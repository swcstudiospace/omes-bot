// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Spectrum Web Co
//! One callable surface per pinned Prime crate.
//!
//! Each function below calls code that lives in that crate. `pa-tui` is the
//! session search, and `pa-daemon` is the worker-frame codec plus the durable
//! create command. Neither function starts a terminal UI or a worker process.

use pyo3::prelude::*;
use serde_json::{json, Map, Value};

use crate::convert::{from_py, py_err, to_py};

fn object(value: Value) -> PyResult<Map<String, Value>> {
    value
        .as_object()
        .cloned()
        .ok_or_else(|| py_err("expected a JSON object"))
}

#[pyfunction]
fn telemetry_version() -> String {
    pa_telemetry::version().to_string()
}

#[pyfunction]
fn telemetry_parse_bool(value: Option<String>) -> Option<bool> {
    pa_telemetry::parse_bool_override(value.as_deref())
}

#[pyfunction]
fn types_js_number(value: f64) -> PyResult<String> {
    serde_json::to_string(&pa_types::JsNumber(value)).map_err(py_err)
}

#[pyfunction]
fn types_worker_id(socket_path: Option<String>) -> Option<String> {
    pa_types::incident::worker_id_from_socket_path(socket_path.as_deref()).map(str::to_string)
}

#[pyfunction]
fn ai_error_has_overflow(message: &str) -> bool {
    pa_ai::utils::overflow::error_message_has_overflow(message)
}

#[pyfunction]
fn ai_repair_json(py: Python<'_>, text: &str) -> PyResult<PyObject> {
    let value = pa_ai::parse_json_with_repair(text).map_err(py_err)?;
    to_py(py, &value)
}

#[pyfunction]
fn models_compat(py: Python<'_>, api: &str, compat: Option<Bound<'_, PyAny>>) -> PyResult<bool> {
    let parsed = match compat {
        Some(obj) if !obj.is_none() => Some(object(from_py(py, &obj)?)?),
        _ => None,
    };
    Ok(pa_models::compat::is_model_compat(api, parsed.as_ref()))
}

#[pyfunction]
fn models_private_id(model_id: &str) -> bool {
    pa_models::prime_inference::is_private_prime_inference_model_id(model_id)
}

#[pyfunction]
fn agent_now_ms() -> i64 {
    pa_agent::now_ms()
}

#[pyfunction]
fn agent_validate_arguments(
    py: Python<'_>,
    tool_name: &str,
    schema: Bound<'_, PyAny>,
    arguments: Bound<'_, PyAny>,
) -> PyResult<PyObject> {
    let schema_value: Value = from_py(py, &schema)?;
    let argument_value: Value = from_py(py, &arguments)?;
    match pa_agent::validation::validate_tool_arguments(tool_name, &schema_value, &argument_value) {
        Ok(value) => to_py(py, &value),
        Err(message) => Err(py_err(message)),
    }
}

#[pyfunction]
fn core_protocol_version() -> u64 {
    pa_core::kernel::protocol::REPL_PROTOCOL_VERSION
}

#[pyfunction]
fn cli_modes() -> Vec<String> {
    [
        pa_cli::AppMode::Interactive,
        pa_cli::AppMode::Print,
        pa_cli::AppMode::Json,
        pa_cli::AppMode::Rpc,
        pa_cli::AppMode::Acp,
        pa_cli::AppMode::Daemon,
    ]
    .into_iter()
    .map(|mode| mode.as_str().to_string())
    .collect()
}

#[pyfunction]
fn cli_missing_subsystem(name: &str) -> PyResult<String> {
    let missing = match name {
        "session" => pa_cli::MissingSubsystem::SessionEngine,
        "models" => pa_cli::MissingSubsystem::ModelRegistry,
        "packages" => pa_cli::MissingSubsystem::PackageManager,
        other => {
            return Err(py_err(format!(
                "unknown subsystem '{other}' (expected session, models, or packages)"
            )))
        }
    };
    Ok(missing.error_message())
}

#[pyfunction]
fn daemon_encode_frame(py: Python<'_>, header: Bound<'_, PyAny>) -> PyResult<PyObject> {
    let value: Value = from_py(py, &header)?;
    let encoded = pa_daemon::framing::encode_private_frame(
        &value,
        &[],
        pa_types::daemon::framing::DEFAULT_PRIVATE_FRAME_LIMITS,
    )
    .map_err(py_err)?;
    if encoded.len() < pa_types::daemon::framing::FRAME_PREFIX_BYTES {
        return Err(py_err("private frame shorter than the 8-byte prefix"));
    }
    let header_len = u32::from_be_bytes([encoded[0], encoded[1], encoded[2], encoded[3]]);
    let payload_len = u32::from_be_bytes([encoded[4], encoded[5], encoded[6], encoded[7]]);
    to_py(
        py,
        &json!({
            "total": encoded.len(),
            "prefix": pa_types::daemon::framing::FRAME_PREFIX_BYTES,
            "header_len": header_len,
            "payload_len": payload_len,
        }),
    )
}

#[pyfunction]
fn daemon_durable_create(py: Python<'_>, payload: Bound<'_, PyAny>) -> PyResult<PyObject> {
    let value: Value = from_py(py, &payload)?;
    let command = pa_daemon::descriptor::durable_create_command(&value);
    to_py(py, &command)
}

#[pyfunction]
fn tui_score_search(name: &str, id: &str, cwd: &str, query: &str) -> Option<f64> {
    let targets = pa_tui::agents_view_search::SessionSearchText {
        name: name.to_string(),
        id: id.to_string(),
        cwd: cwd.to_string(),
    };
    let parsed = pa_tui::agents_view_search::parse_search_query(query);
    pa_tui::agents_view_search::score_search(&targets, &parsed)
}

#[pyfunction]
fn probe(py: Python<'_>) -> PyResult<PyObject> {
    let event = pa_telemetry::catalog()
        .first()
        .map(|rule| rule.name.to_string())
        .unwrap_or_default();
    let schema = json!({
        "type": "object",
        "properties": {"n": {"type": "integer"}},
        "required": ["n"],
    });
    let coerced =
        pa_agent::validation::validate_tool_arguments("probe", &schema, &json!({"n": "4"}))
            .map_err(py_err)?;
    let header = json!({"type": "ping"});
    let encoded = pa_daemon::framing::encode_private_frame(
        &header,
        &[],
        pa_types::daemon::framing::DEFAULT_PRIVATE_FRAME_LIMITS,
    )
    .map_err(py_err)?;
    let header_len = u32::from_be_bytes([encoded[0], encoded[1], encoded[2], encoded[3]]);
    let payload = json!({
        "type": "create",
        "sessionPath": "/tmp/s",
        "noSession": false,
        "extra": 1,
    });
    let created = pa_daemon::descriptor::durable_create_command(&payload);
    let repaired = pa_ai::parse_json_with_repair(r#"{"a":1}"#).map_err(py_err)?;
    let value = json!({
        "pa-telemetry": {
            "version": pa_telemetry::version(),
            "schema_version": pa_telemetry::SCHEMA_VERSION,
            "parse_bool": pa_telemetry::parse_bool_override(Some("yes")),
            "event": event,
        },
        "pa-types": {
            "js_number": serde_json::to_string(&pa_types::JsNumber(1.0)).map_err(py_err)?,
            "worker_id": pa_types::incident::worker_id_from_socket_path(Some(
                "/tmp/prime-agent-worker-abcd-0123456789ab.sock",
            )),
        },
        "pa-ai": {
            "overflow": pa_ai::utils::overflow::error_message_has_overflow("prompt is too long"),
            "plain": pa_ai::utils::overflow::error_message_has_overflow("hello"),
            "repaired": repaired,
        },
        "pa-models": {
            "refresh_ms": pa_models::CATALOG_REFRESH_INTERVAL_MS,
            "private_id": pa_models::prime_inference::is_private_prime_inference_model_id("internal/x"),
            "public_id": pa_models::prime_inference::is_private_prime_inference_model_id("gpt-4"),
            "compat_absent": pa_models::compat::is_model_compat("openai-completions", None),
            "compat_unknown_api": pa_models::compat::is_model_compat(
                "not-an-api",
                Some(&Map::from_iter([("x".to_string(), Value::Bool(true))])),
            ),
            "offline": pa_models::offline::is_catalog_offline(),
        },
        "pa-agent": {
            "now_ms": pa_agent::now_ms(),
            "coerced": coerced,
        },
        "pa-core": {
            "protocol": pa_core::kernel::protocol::REPL_PROTOCOL_VERSION,
            "unlimited_zero": pa_core::autonomous::is_unlimited_autonomous_limit(0),
        },
        "pa-daemon": {
            "supervisor_config": pa_daemon::descriptor::SUPERVISOR_CONFIG_FILE_NAME,
            "frame_total": encoded.len(),
            "frame_prefix": pa_types::daemon::framing::FRAME_PREFIX_BYTES,
            "header_len": header_len,
            "payload_len": 0,
            "create": created,
        },
        "pa-tui": {
            "score": tui_score_search("ship the release", "sess", "/work", "release"),
            "invalid_regex": tui_score_search("ship the release", "sess", "/work", "re:("),
        },
        "pa-cli": {
            "modes": cli_modes(),
            "missing_session_engine": pa_cli::MissingSubsystem::SessionEngine.error_message(),
        },
    });
    to_py(py, &value)
}

pub fn register(parent: &Bound<'_, PyModule>) -> PyResult<()> {
    let module = PyModule::new(parent.py(), "crates")?;
    module.add_function(wrap_pyfunction!(telemetry_version, &module)?)?;
    module.add_function(wrap_pyfunction!(telemetry_parse_bool, &module)?)?;
    module.add_function(wrap_pyfunction!(types_js_number, &module)?)?;
    module.add_function(wrap_pyfunction!(types_worker_id, &module)?)?;
    module.add_function(wrap_pyfunction!(ai_error_has_overflow, &module)?)?;
    module.add_function(wrap_pyfunction!(ai_repair_json, &module)?)?;
    module.add_function(wrap_pyfunction!(models_compat, &module)?)?;
    module.add_function(wrap_pyfunction!(models_private_id, &module)?)?;
    module.add_function(wrap_pyfunction!(agent_now_ms, &module)?)?;
    module.add_function(wrap_pyfunction!(agent_validate_arguments, &module)?)?;
    module.add_function(wrap_pyfunction!(core_protocol_version, &module)?)?;
    module.add_function(wrap_pyfunction!(cli_modes, &module)?)?;
    module.add_function(wrap_pyfunction!(cli_missing_subsystem, &module)?)?;
    module.add_function(wrap_pyfunction!(daemon_encode_frame, &module)?)?;
    module.add_function(wrap_pyfunction!(daemon_durable_create, &module)?)?;
    module.add_function(wrap_pyfunction!(tui_score_search, &module)?)?;
    module.add_function(wrap_pyfunction!(probe, &module)?)?;
    module.add(
        "CATALOG_REFRESH_INTERVAL_MS",
        pa_models::CATALOG_REFRESH_INTERVAL_MS,
    )?;
    parent.add_submodule(&module)?;
    Ok(())
}
