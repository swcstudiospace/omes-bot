// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Spectrum Web Co
//! Bindings for `pa_core::autonomous` run-state accounting.
//!
//! `AutonomousRuntimeState` is not a serde type (it carries the gate snapshot),
//! so Python holds the Rust value in [`AutonomousRun`] and receives the
//! camelCase [`AgentAutonomousStatus`] from `status()`.

use pa_core::autonomous::{
    add_autonomous_continuation, add_autonomous_usage, autonomous_continuation_text,
    autonomous_limit_reason, autonomous_status, create_autonomous_runtime_state,
    create_autonomous_subagent_keep_alive_text, describe_autonomous_limit, set_autonomous_enabled,
    set_autonomous_limits, AgentAutonomousConfig, AgentAutonomousGateFailure,
    AutonomousLimitReason, AutonomousRuntimeState,
};
use pyo3::prelude::*;

use crate::convert::{from_py, py_err, to_py};

fn config_from_py(
    py: Python<'_>,
    value: Option<Bound<'_, PyAny>>,
) -> PyResult<Option<AgentAutonomousConfig>> {
    match value {
        Some(obj) if !obj.is_none() => Ok(Some(from_py(py, &obj)?)),
        _ => Ok(None),
    }
}

fn reason_name(reason: AutonomousLimitReason) -> &'static str {
    match reason {
        AutonomousLimitReason::MaxContinuations => "max_continuations",
        AutonomousLimitReason::MaxTurns => "max_turns",
        AutonomousLimitReason::MaxTokens => "max_tokens",
        AutonomousLimitReason::TimeoutMs => "timeout_ms",
    }
}

fn reason_from_name(name: &str) -> PyResult<AutonomousLimitReason> {
    match name {
        "max_continuations" => Ok(AutonomousLimitReason::MaxContinuations),
        "max_turns" => Ok(AutonomousLimitReason::MaxTurns),
        "max_tokens" => Ok(AutonomousLimitReason::MaxTokens),
        "timeout_ms" => Ok(AutonomousLimitReason::TimeoutMs),
        other => Err(py_err(format!("unknown autonomous limit '{other}'"))),
    }
}

/// Usage object. Accepts Prime's camelCase wire keys and the prompt/completion aliases.
/// Cache-read tokens are stored and ignored by the autonomous delta, matching `pa-core`.
fn usage_from_py(py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<pa_types::ai::Usage> {
    let value = from_py::<serde_json::Value>(py, obj)?;
    let map = value
        .as_object()
        .ok_or_else(|| py_err("usage must be an object"))?;
    let number = |keys: &[&str]| -> PyResult<u64> {
        for key in keys {
            if let Some(found) = map.get(*key) {
                if found.is_null() {
                    return Ok(0);
                }
                return found
                    .as_u64()
                    .ok_or_else(|| py_err(format!("{key} must be a non-negative integer")));
            }
        }
        Ok(0)
    };
    Ok(pa_types::ai::Usage {
        input: number(&["input", "prompt_tokens", "promptTokens"])?,
        output: number(&["output", "completion_tokens", "completionTokens"])?,
        cache_read: number(&["cacheRead", "cache_read"])?,
        cache_write: number(&["cacheWrite", "cache_write"])?,
        total_tokens: number(&["totalTokens", "total_tokens"])?,
        ..pa_types::ai::Usage::default()
    })
}

/// One autonomous run. Config objects use Prime's camelCase (`maxTurns`, `timeoutMs`).
#[pyclass(name = "AutonomousRun", module = "omega_prime_prime.autonomous")]
pub struct AutonomousRun {
    state: AutonomousRuntimeState,
}

#[pymethods]
impl AutonomousRun {
    /// `config` enables the run when `enabled` is true. `defaults` fills limits the config omits.
    #[new]
    #[pyo3(signature = (config=None, defaults=None))]
    fn new(
        py: Python<'_>,
        config: Option<Bound<'_, PyAny>>,
        defaults: Option<Bound<'_, PyAny>>,
    ) -> PyResult<Self> {
        let config = config_from_py(py, config)?;
        let defaults = config_from_py(py, defaults)?;
        Ok(Self {
            state: create_autonomous_runtime_state(config.as_ref(), defaults.as_ref()),
        })
    }

    #[getter]
    fn enabled(&self) -> bool {
        self.state.enabled
    }

    #[getter]
    fn turns_used(&self) -> u64 {
        self.state.turns_used
    }

    #[getter]
    fn tokens_used(&self) -> u64 {
        self.state.tokens_used
    }

    #[getter]
    fn continuations_used(&self) -> u64 {
        self.state.continuations_used
    }

    /// CamelCase `AgentAutonomousStatus` snapshot.
    fn status(&self, py: Python<'_>) -> PyResult<PyObject> {
        to_py(py, &autonomous_status(&self.state))
    }

    /// Enabling resets counters. Disabling clears `startedAt`.
    fn set_enabled(&mut self, enabled: bool) {
        set_autonomous_enabled(&mut self.state, enabled);
    }

    /// Apply only the fields present on `config`.
    fn set_limits(&mut self, py: Python<'_>, config: Bound<'_, PyAny>) -> PyResult<()> {
        let config = from_py::<AgentAutonomousConfig>(py, &config)?;
        set_autonomous_limits(&mut self.state, &config);
        Ok(())
    }

    /// Count one settled turn. Input + output + cache-write; cache-read is not counted.
    /// A disabled run ignores the call. `usage=None` still counts a turn when enabled.
    #[pyo3(signature = (usage=None))]
    fn add_usage(&mut self, py: Python<'_>, usage: Option<Bound<'_, PyAny>>) -> PyResult<()> {
        let parsed = match usage {
            Some(obj) if !obj.is_none() => Some(usage_from_py(py, &obj)?),
            _ => None,
        };
        add_autonomous_usage(&mut self.state, parsed.as_ref());
        Ok(())
    }

    fn add_continuation(&mut self) {
        add_autonomous_continuation(&mut self.state);
    }

    /// `max_continuations`, `max_turns`, `max_tokens`, `timeout_ms`, or `None`.
    fn limit_reason(&self, now_ms: u64) -> Option<&'static str> {
        autonomous_limit_reason(&self.state, now_ms).map(reason_name)
    }

    fn describe_limit(&self, reason: &str, now_ms: u64) -> PyResult<String> {
        let reason = reason_from_name(reason)?;
        Ok(describe_autonomous_limit(
            &autonomous_status(&self.state),
            reason,
            now_ms,
        ))
    }

    fn continuation_text(&self) -> String {
        autonomous_continuation_text(&self.state)
    }

    fn keep_alive_text(&self) -> String {
        create_autonomous_subagent_keep_alive_text(&self.state)
    }
}

/// The user message an in-run continuation hook hands back to the agent loop.
#[pyfunction]
pub fn continuation_loop_row(py: Python<'_>, text: &str, timestamp: u64) -> PyResult<PyObject> {
    to_py(
        py,
        &pa_core::autonomous::autonomous_continuation_loop_row(text, timestamp),
    )
}

/// Disabled status snapshot (`emptyAutonomousStatus`).
#[pyfunction]
pub fn disabled_status(py: Python<'_>) -> PyResult<PyObject> {
    to_py(py, &pa_core::autonomous::disabled_autonomous_status())
}

/// True at or above the JSON-safe "no cap" sentinel.
#[pyfunction]
pub fn is_unlimited(value: u64) -> bool {
    pa_core::autonomous::is_unlimited_autonomous_limit(value)
}

/// Gate-failure continuation body. `failure` is camelCase (`exitText`).
#[pyfunction]
pub fn gate_failure_continuation(
    py: Python<'_>,
    failure: Bound<'_, PyAny>,
    max_retries: u64,
    timestamp: u64,
) -> PyResult<String> {
    let failure = from_py::<AgentAutonomousGateFailure>(py, &failure)?;
    Ok(
        pa_core::autonomous::build_autonomous_gate_failure_continuation(
            &failure,
            max_retries,
            timestamp,
        ),
    )
}

pub fn register(parent: &Bound<'_, PyModule>) -> PyResult<()> {
    let module = PyModule::new(parent.py(), "autonomous")?;
    module.add_class::<AutonomousRun>()?;
    module.add_function(wrap_pyfunction!(continuation_loop_row, &module)?)?;
    module.add_function(wrap_pyfunction!(disabled_status, &module)?)?;
    module.add_function(wrap_pyfunction!(is_unlimited, &module)?)?;
    module.add_function(wrap_pyfunction!(gate_failure_continuation, &module)?)?;
    module.add(
        "DEFAULT_MAX_CONTINUATIONS",
        pa_core::autonomous::DEFAULT_MAX_CONTINUATIONS,
    )?;
    module.add("DEFAULT_MAX_TURNS", pa_core::autonomous::DEFAULT_MAX_TURNS)?;
    module.add(
        "DEFAULT_MAX_TOKENS",
        pa_core::autonomous::DEFAULT_MAX_TOKENS,
    )?;
    module.add(
        "DEFAULT_TIMEOUT_MS",
        pa_core::autonomous::DEFAULT_TIMEOUT_MS,
    )?;
    module.add(
        "UNLIMITED_AUTONOMOUS_LIMIT",
        pa_core::autonomous::UNLIMITED_AUTONOMOUS_LIMIT,
    )?;
    module.add(
        "DEFAULT_AUTONOMOUS_CONTINUATION_PROMPT",
        pa_core::autonomous::DEFAULT_AUTONOMOUS_CONTINUATION_PROMPT,
    )?;
    parent.add_submodule(&module)?;
    Ok(())
}
