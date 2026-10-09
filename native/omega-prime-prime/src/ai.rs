// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Spectrum Web Co
//! In-process Prime providers and catalog resolution.
//!
//! `complete` returns Prime's assistant wire message, including terminal
//! `stopReason: error/aborted` responses. Unknown/non-JSON runtime options are
//! rejected. A single process-lifetime runtime has two async workers and at most
//! four blocking workers; the Python caller releases the GIL during every wait.
//! `timeoutMs` covers session queueing and the entire completion, not just HTTP
//! headers. Timeout/KeyboardInterrupt cancels the provider and allows at most
//! one second for terminal settlement. An unsettled cancellation is reported,
//! never presented as a successful completion or silently detached by us.
//!
//! Codex caches a connection's original cancellation token. Reusing that token
//! under a per-session gate preserves both cancellation and connection reuse.
//! The session table is bounded; idle LRU eviction closes the Prime connection.
//! There is deliberately no Python streaming facade or provider substitute.

use std::collections::HashMap;
use std::future::pending;
use std::path::PathBuf;
use std::sync::{Arc, LazyLock, Mutex};
use std::time::{Duration, Instant};

use pa_ai::types::{
    AssistantMessage, CacheRetention, Context, Message, Model, ModelThinkingLevel, ServiceTier,
    SimpleStreamOptions, StreamOptions, ThinkingBudgets, Transport,
};
use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use serde::de::DeserializeOwned;
use serde_json::{Map, Value};
use tokio::runtime::{Builder, Runtime};
use tokio_util::sync::CancellationToken;

use crate::convert::{from_py, to_py};

const SIGNAL_POLL_INTERVAL: Duration = Duration::from_millis(100);
const CANCELLATION_GRACE: Duration = Duration::from_secs(1);
const MAX_CODEX_SESSIONS: usize = 128;

fn runtime() -> PyResult<&'static Runtime> {
    static RUNTIME: LazyLock<Result<Runtime, std::io::Error>> = LazyLock::new(|| {
        Builder::new_multi_thread()
            .worker_threads(2)
            .max_blocking_threads(4)
            .thread_name("omega-prime-ai")
            .enable_all()
            .build()
    });
    RUNTIME
        .as_ref()
        .map_err(|_| PyRuntimeError::new_err("Could not initialize the Prime provider runtime"))
}

struct CodexSession {
    id: String,
    // The guard is held until completion or bounded cancellation cleanup ends.
    state: tokio::sync::Mutex<CodexSessionState>,
}

struct CodexSessionState {
    token: CancellationToken,
    // Fail closed if Prime did not settle: its private task handle cannot be
    // aborted by this binding and must never interfere with a replacement.
    reusable: bool,
}

struct SessionEntry {
    session: Arc<CodexSession>,
    last_used: Instant,
}

fn codex_session(
    model: &Model,
    options: &SimpleStreamOptions,
) -> PyResult<Option<Arc<CodexSession>>> {
    if model.api != "openai-codex-responses" || options.base.transport == Some(Transport::Sse) {
        return Ok(None);
    }
    let Some(id) = options.base.session_id.as_deref() else {
        return Ok(None);
    };
    static SESSIONS: LazyLock<Mutex<HashMap<String, SessionEntry>>> =
        LazyLock::new(|| Mutex::new(HashMap::new()));
    let mut sessions = SESSIONS
        .lock()
        .map_err(|_| PyRuntimeError::new_err("Prime session registry is unavailable"))?;
    if let Some(entry) = sessions.get_mut(id) {
        entry.last_used = Instant::now();
        return Ok(Some(Arc::clone(&entry.session)));
    }
    if sessions.len() == MAX_CODEX_SESSIONS {
        let idle_id = sessions
            .iter()
            .filter(|(_, entry)| {
                Arc::strong_count(&entry.session) == 1
                    && entry
                        .session
                        .state
                        .try_lock()
                        .is_ok_and(|state| state.reusable)
            })
            .min_by_key(|(_, entry)| entry.last_used)
            .map(|(id, _)| id.clone());
        let Some(id) = idle_id else {
            return Err(PyRuntimeError::new_err(
                "All Prime Codex session slots are in use",
            ));
        };
        pa_ai::codex_debug::close_websocket_sessions(Some(&id));
        sessions.remove(&id);
    }
    let session = Arc::new(CodexSession {
        id: id.to_owned(),
        state: tokio::sync::Mutex::new(CodexSessionState {
            token: CancellationToken::new(),
            reusable: true,
        }),
    });
    sessions.insert(
        id.to_owned(),
        SessionEntry {
            session: Arc::clone(&session),
            last_used: Instant::now(),
        },
    );
    Ok(Some(session))
}

fn option<T: DeserializeOwned>(values: &mut Map<String, Value>, name: &str) -> PyResult<Option<T>> {
    match values.remove(name) {
        None | Some(Value::Null) => Ok(None),
        Some(value) => serde_json::from_value(value)
            .map(Some)
            // Never interpolate an option's value (credentials can be malformed).
            .map_err(|_| PyValueError::new_err(format!("Invalid Prime completion option: {name}"))),
    }
}

fn parse_options(
    py: Python<'_>,
    options: Option<&Bound<'_, PyAny>>,
) -> PyResult<SimpleStreamOptions> {
    let Some(options) = options.filter(|value| !value.is_none()) else {
        return Ok(SimpleStreamOptions::default());
    };
    let value: Value = from_py(py, options)
        .map_err(|_| PyValueError::new_err("Prime completion options must be a JSON object"))?;
    let Value::Object(mut values) = value else {
        return Err(PyValueError::new_err(
            "Prime completion options must be a JSON object",
        ));
    };
    // StreamOptions contains runtime hooks and CancellationToken, not serde
    // fields. Map only its public, JSON-representable options explicitly.
    let base = StreamOptions {
        api_key: option::<String>(&mut values, "apiKey")?,
        temperature: option::<f64>(&mut values, "temperature")?,
        max_tokens: option::<u64>(&mut values, "maxTokens")?,
        timeout_ms: option::<u64>(&mut values, "timeoutMs")?,
        session_id: option::<String>(&mut values, "sessionId")?,
        transport: option::<Transport>(&mut values, "transport")?,
        service_tier: option::<ServiceTier>(&mut values, "serviceTier")?,
        cache_retention: option::<CacheRetention>(&mut values, "cacheRetention")?,
        headers: option::<HashMap<String, String>>(&mut values, "headers")?,
        metadata: option::<HashMap<String, Value>>(&mut values, "metadata")?,
        ..StreamOptions::default()
    };
    let reasoning = option::<ModelThinkingLevel>(&mut values, "reasoning")?;
    if let Some(Value::Object(budgets)) = values.get("thinkingBudgets") {
        if budgets
            .keys()
            .any(|key| !matches!(key.as_str(), "minimal" | "low" | "medium" | "high"))
        {
            return Err(PyValueError::new_err(
                "Unsupported Prime thinking budget option",
            ));
        }
    }
    let thinking_budgets = option::<ThinkingBudgets>(&mut values, "thinkingBudgets")?;
    if !values.is_empty() {
        return Err(PyValueError::new_err("Unsupported Prime completion option"));
    }
    Ok(SimpleStreamOptions {
        base,
        reasoning,
        thinking_budgets,
    })
}

enum CompletionFailure {
    Launch,
    Cleanup,
    Timeout { settled: bool },
    Interrupted { settled: bool },
}

async fn deadline_wait(deadline: Option<tokio::time::Instant>) {
    match deadline {
        Some(deadline) => tokio::time::sleep_until(deadline).await,
        None => pending::<()>().await,
    }
}

async fn run_completion(
    model: &Model,
    context: &Context,
    mut options: SimpleStreamOptions,
    session: Option<&CodexSession>,
    deadline: Option<tokio::time::Instant>,
    interrupted: &CancellationToken,
) -> Result<AssistantMessage, CompletionFailure> {
    let mut guard = match session {
        Some(session) => Some(tokio::select! {
            biased;
            () = interrupted.cancelled() => return Err(CompletionFailure::Interrupted { settled: true }),
            () = deadline_wait(deadline) => return Err(CompletionFailure::Timeout { settled: true }),
            guard = session.state.lock() => guard,
        }),
        None => None,
    };
    if interrupted.is_cancelled() {
        return Err(CompletionFailure::Interrupted { settled: true });
    }
    if deadline.is_some_and(|deadline| tokio::time::Instant::now() >= deadline) {
        return Err(CompletionFailure::Timeout { settled: true });
    }
    let signal = match guard.as_mut() {
        Some(state) => {
            if !state.reusable {
                return Err(CompletionFailure::Cleanup);
            }
            // Reset only after the previous cancelled provider settled.
            if state.token.is_cancelled() {
                state.token = CancellationToken::new();
            }
            state.token.clone()
        }
        None => CancellationToken::new(),
    };
    options.base.signal = Some(signal.clone());
    let completion = pa_ai::complete_simple(model, context, Some(options));
    let mut completion = std::pin::pin!(completion);
    let timed_out = tokio::select! {
        biased;
        result = &mut completion => return result.map_err(|_| CompletionFailure::Launch),
        () = interrupted.cancelled() => false,
        () = deadline_wait(deadline) => true,
    };
    signal.cancel();
    if let Some(session) = session {
        pa_ai::codex_debug::close_websocket_sessions(Some(&session.id));
    }
    // Dropping complete_simple alone does not cancel Prime's spawned provider
    // task. Cancel its signal and await terminal settlement before releasing
    // the gate; the grace bound also handles a broken/non-cooperative provider.
    let settled = tokio::time::timeout(CANCELLATION_GRACE, &mut completion)
        .await
        .is_ok();
    if let Some(state) = guard.as_mut() {
        state.reusable = settled;
    }
    if timed_out {
        Err(CompletionFailure::Timeout { settled })
    } else {
        Err(CompletionFailure::Interrupted { settled })
    }
}

fn secrets(model: &Model, options: &SimpleStreamOptions) -> Vec<String> {
    let mut secrets = Vec::new();
    if let Some(key) = &options.base.api_key {
        secrets.push(key.clone());
    }
    if let Some(names) = pa_ai::env_api_keys::get_api_key_env_vars(&model.provider) {
        secrets.extend(
            names
                .into_iter()
                .filter_map(|name| std::env::var(name).ok()),
        );
    }
    if model.provider == "amazon-bedrock" {
        secrets.extend(
            [
                "AWS_ACCESS_KEY_ID",
                "AWS_SECRET_ACCESS_KEY",
                "AWS_SESSION_TOKEN",
                "AWS_BEARER_TOKEN_BEDROCK",
            ]
            .into_iter()
            .filter_map(|name| std::env::var(name).ok()),
        );
    }
    if let Some(headers) = &model.headers {
        for value in headers.values() {
            secrets.push(value.clone());
            if let Some(token) = value
                .strip_prefix("Bearer ")
                .or_else(|| value.strip_prefix("Basic "))
            {
                secrets.push(token.to_owned());
            }
        }
    }
    if let Some(headers) = &options.base.headers {
        for value in headers.values() {
            secrets.push(value.clone());
            if let Some(token) = value
                .strip_prefix("Bearer ")
                .or_else(|| value.strip_prefix("Basic "))
            {
                secrets.push(token.to_owned());
            }
        }
    }
    // Error causes can contain the request URL, including query credentials.
    secrets.push(model.base_url.clone());
    if let Some((_, query)) = model.base_url.split_once('?') {
        for field in query.split('&') {
            if let Some((_, value)) = field.split_once('=') {
                secrets.push(value.to_owned());
                secrets.push(decode_url_secret(value, true));
            }
        }
    }
    if let Some((_, authority)) = model.base_url.split_once("://") {
        if let Some((credentials, _)) = authority.split('/').next().unwrap_or("").rsplit_once('@') {
            secrets.push(credentials.to_owned());
            if let Some((_, password)) = credentials.split_once(':') {
                secrets.push(password.to_owned());
                secrets.push(decode_url_secret(password, false));
            }
        }
    }
    secrets.retain(|secret| !secret.is_empty());
    secrets
        .sort_unstable_by(|left, right| right.len().cmp(&left.len()).then_with(|| left.cmp(right)));
    secrets.dedup();
    secrets
}

fn decode_url_secret(value: &str, query: bool) -> String {
    let mut bytes = value.bytes().peekable();
    let mut decoded = Vec::with_capacity(value.len());
    while let Some(byte) = bytes.next() {
        if byte == b'%' {
            let mut pair = bytes.clone();
            if let (Some(high), Some(low)) = (pair.next(), pair.next()) {
                if let (Some(high), Some(low)) =
                    ((high as char).to_digit(16), (low as char).to_digit(16))
                {
                    decoded.push((high * 16 + low) as u8);
                    bytes = pair;
                    continue;
                }
            }
        }
        decoded.push(if query && byte == b'+' { b' ' } else { byte });
    }
    String::from_utf8_lossy(&decoded).into_owned()
}

fn redact(value: &mut Value, secrets: &[String]) {
    match value {
        Value::String(text) => {
            for secret in secrets {
                if text.contains(secret.as_str()) {
                    *text = text.replace(secret.as_str(), "[redacted]");
                }
            }
        }
        Value::Array(values) => values.iter_mut().for_each(|value| redact(value, secrets)),
        Value::Object(values) => values.values_mut().for_each(|value| redact(value, secrets)),
        _ => {}
    }
}

/// Complete a Prime wire context with an actual in-process Prime provider.
#[pyfunction]
#[pyo3(signature = (model, context, options=None))]
pub fn complete(
    py: Python<'_>,
    model: &Bound<'_, PyAny>,
    context: &Bound<'_, PyAny>,
    options: Option<&Bound<'_, PyAny>>,
) -> PyResult<PyObject> {
    let model: Model = from_py(py, model)
        .map_err(|_| PyValueError::new_err("Invalid Prime model wire descriptor"))?;
    let context: Context = from_py(py, context)
        .map_err(|_| PyValueError::new_err("Invalid Prime context wire object"))?;
    let options = parse_options(py, options)?;
    let secrets = secrets(&model, &options);
    let runtime = runtime()?;
    let deadline = options
        .base
        .timeout_ms
        .map(|milliseconds| {
            tokio::time::Instant::now()
                .checked_add(Duration::from_millis(milliseconds))
                .ok_or_else(|| {
                    PyValueError::new_err("Prime timeoutMs exceeds the supported duration")
                })
        })
        .transpose()?;
    let session = codex_session(&model, &options)?;
    let interrupted = CancellationToken::new();
    let completion = run_completion(
        &model,
        &context,
        options,
        session.as_deref(),
        deadline,
        &interrupted,
    );
    let mut completion = std::pin::pin!(completion);
    let result = loop {
        let result = py.allow_threads(|| {
            runtime.block_on(async {
                tokio::select! {
                    biased;
                    result = &mut completion => Some(result),
                    () = tokio::time::sleep(SIGNAL_POLL_INTERVAL) => None,
                }
            })
        });
        if let Some(result) = result {
            break result;
        }
        if let Err(error) = py.check_signals() {
            interrupted.cancel();
            // Preserve KeyboardInterrupt while still running bounded cleanup.
            let _ = py.allow_threads(|| runtime.block_on(&mut completion));
            return Err(error);
        }
    };
    py.check_signals()?;
    let message = result.map_err(|failure| {
        let message = match failure {
            CompletionFailure::Launch => "Prime provider could not start the completion",
            CompletionFailure::Cleanup => "Prime Codex session is unavailable because its previous provider cancellation did not settle",
            CompletionFailure::Timeout { settled: true } => "Prime completion timed out; provider cancellation settled",
            CompletionFailure::Timeout { settled: false } => "Prime completion timed out; provider did not settle within the cancellation grace period",
            CompletionFailure::Interrupted { settled: true } => "Prime completion was aborted",
            CompletionFailure::Interrupted { settled: false } => "Prime completion was aborted; provider did not settle within the cancellation grace period",
        };
        PyRuntimeError::new_err(message)
    })?;
    if !matches!(
        message.stop_reason,
        pa_ai::types::StopReason::Error | pa_ai::types::StopReason::Aborted
    ) {
        return to_py(py, &Message::Assistant(message));
    }
    // AssistantMessage itself has no role field; Prime's tagged Message wire
    // envelope supplies it without hand-assembling content, usage or signatures.
    let mut wire = serde_json::to_value(Message::Assistant(message))
        .map_err(|_| PyRuntimeError::new_err("Could not encode the Prime assistant message"))?;
    // Keep terminal protocol tags unchanged even for an unusually short
    // credential equal to a stop reason. Redact only diagnostic payloads.
    for name in ["errorMessage", "diagnostics", "stopReasonRaw", "content"] {
        if let Some(value) = wire.get_mut(name) {
            redact(value, &secrets);
        }
    }
    to_py(py, &wire)
}

/// Resolve Prime's disk-cache / bundled / compiled catalog without network I/O.
#[pyfunction]
#[pyo3(signature = (models_dir=None))]
pub fn resolve_models(py: Python<'_>, models_dir: Option<String>) -> PyResult<PyObject> {
    let models = py.allow_threads(|| {
        pa_models::ModelCatalog::new(models_dir.map(PathBuf::from)).resolve(None)
    });
    to_py(py, &models)
}

pub fn register(parent: &Bound<'_, PyModule>) -> PyResult<()> {
    let module = PyModule::new(parent.py(), "ai")?;
    module.add_function(wrap_pyfunction!(complete, &module)?)?;
    module.add_function(wrap_pyfunction!(resolve_models, &module)?)?;
    parent.add_submodule(&module)?;
    Ok(())
}
