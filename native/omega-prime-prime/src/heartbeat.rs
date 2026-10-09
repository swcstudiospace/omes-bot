// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Spectrum Web Co
//! Bindings for `pa_core::cron` schedule parsing and heartbeat deferral.

use pa_core::cron::{
    AgentCronJob, AgentCronSchedule, DeliveryMode, HeartbeatSessionActivity, ParsedHeartbeatCommand,
};
use pyo3::prelude::*;
use serde_json::json;

use crate::convert::{from_py, py_err, to_py};

fn flag(obj: &Bound<'_, PyAny>, key: &str) -> PyResult<bool> {
    obj.call_method1("get", (key, false))?.extract()
}

fn count(obj: &Bound<'_, PyAny>, key: &str) -> PyResult<usize> {
    obj.call_method1("get", (key, 0_usize))?.extract()
}

fn activity_from_py(obj: &Bound<'_, PyAny>) -> PyResult<HeartbeatSessionActivity> {
    Ok(HeartbeatSessionActivity {
        is_streaming: flag(obj, "is_streaming")?,
        is_compacting: flag(obj, "is_compacting")?,
        is_retrying: flag(obj, "is_retrying")?,
        is_bash_running: flag(obj, "is_bash_running")?,
        has_pending_session_work: flag(obj, "has_pending_session_work")?,
        unfinished_action_count: count(obj, "unfinished_action_count")?,
    })
}

fn delivery_name(mode: DeliveryMode) -> &'static str {
    match mode {
        DeliveryMode::Steer => "steer",
        DeliveryMode::FollowUp => "follow_up",
    }
}

fn command_value(command: ParsedHeartbeatCommand) -> serde_json::Value {
    match command {
        ParsedHeartbeatCommand::Status => json!({"command": "status"}),
        ParsedHeartbeatCommand::Pause => json!({"command": "pause"}),
        ParsedHeartbeatCommand::Resume => json!({"command": "resume"}),
        ParsedHeartbeatCommand::Clear => json!({"command": "clear"}),
        ParsedHeartbeatCommand::Set {
            schedule,
            instruction,
            delivery_mode,
        } => json!({
            "command": "set",
            "schedule": schedule,
            "instruction": instruction,
            "deliveryMode": delivery_mode.map(delivery_name),
        }),
    }
}

/// Parse `in` / `every` / `at` / cron. `nextRunAt` is epoch milliseconds.
#[pyfunction]
pub fn parse_schedule(py: Python<'_>, expression: &str, now_ms: u64) -> PyResult<PyObject> {
    let (schedule, next_run_at) =
        pa_core::cron::parse_agent_cron_schedule(expression, now_ms).map_err(py_err)?;
    to_py(py, &json!({"schedule": schedule, "nextRunAt": next_run_at}))
}

/// Blank input becomes `every 5m`. A bare `10m` becomes `every 10m`.
#[pyfunction]
#[pyo3(signature = (expression=None))]
pub fn normalize_schedule(expression: Option<String>) -> String {
    pa_core::cron::normalize_heartbeat_schedule(expression.as_deref())
}

/// `None`, `"steer"`, or `"follow_up"`. Anything else is a `ValueError`.
#[pyfunction]
#[pyo3(signature = (mode=None))]
pub fn normalize_delivery_mode(mode: Option<String>) -> PyResult<Option<String>> {
    Ok(
        pa_core::cron::normalize_heartbeat_delivery_mode(mode.as_deref())
            .map_err(py_err)?
            .map(|mode| delivery_name(mode).to_string()),
    )
}

/// Prime's streaming behavior slug: `"steer"` or `"followUp"`.
#[pyfunction]
#[pyo3(signature = (mode=None))]
pub fn streaming_behavior(mode: Option<String>) -> PyResult<&'static str> {
    let mode = pa_core::cron::normalize_heartbeat_delivery_mode(mode.as_deref()).map_err(py_err)?;
    Ok(pa_core::cron::resolve_heartbeat_streaming_behavior(mode))
}

/// Parse a `/heartbeat` command body (`status`, `pause`, `resume`, `clear`, or a set).
#[pyfunction]
pub fn parse_command(py: Python<'_>, text: &str) -> PyResult<PyObject> {
    let command = pa_core::cron::parse_heartbeat_command(text).map_err(py_err)?;
    to_py(py, &command_value(command))
}

#[pyfunction]
pub fn is_heartbeat(py: Python<'_>, job: Bound<'_, PyAny>) -> PyResult<bool> {
    let job = from_py::<AgentCronJob>(py, &job)?;
    Ok(pa_core::cron::is_heartbeat_cron_job(&job))
}

/// Defer a heartbeat while the session is busy. `activity` uses snake_case flags.
#[pyfunction]
pub fn should_defer(
    py: Python<'_>,
    job: Bound<'_, PyAny>,
    activity: Bound<'_, PyAny>,
) -> PyResult<bool> {
    let job = from_py::<AgentCronJob>(py, &job)?;
    let activity = activity_from_py(&activity)?;
    Ok(pa_core::cron::should_defer_heartbeat_cron_job(
        &job, &activity,
    ))
}

/// `nextRunAt` on the job is an ISO-8601 string, compared with `now_ms`.
#[pyfunction]
pub fn is_due(py: Python<'_>, job: Bound<'_, PyAny>, now_ms: u64) -> PyResult<bool> {
    let job = from_py::<AgentCronJob>(py, &job)?;
    Ok(pa_core::cron::is_due_job(&job, now_ms))
}

/// Next run after `after_ms`. One-shot schedules return `None`.
#[pyfunction]
pub fn next_run(
    py: Python<'_>,
    schedule: Bound<'_, PyAny>,
    after_ms: u64,
) -> PyResult<Option<u64>> {
    let schedule = from_py::<AgentCronSchedule>(py, &schedule)?;
    pa_core::cron::next_run_at_for_schedule(&schedule, after_ms).map_err(py_err)
}

/// One-line summary from `format_agent_cron_job`.
#[pyfunction]
pub fn format_job(py: Python<'_>, job: Bound<'_, PyAny>) -> PyResult<String> {
    let job = from_py::<AgentCronJob>(py, &job)?;
    Ok(pa_core::cron::format_agent_cron_job(&job))
}

pub fn register(parent: &Bound<'_, PyModule>) -> PyResult<()> {
    let module = PyModule::new(parent.py(), "heartbeat")?;
    module.add_function(wrap_pyfunction!(parse_schedule, &module)?)?;
    module.add_function(wrap_pyfunction!(normalize_schedule, &module)?)?;
    module.add_function(wrap_pyfunction!(normalize_delivery_mode, &module)?)?;
    module.add_function(wrap_pyfunction!(streaming_behavior, &module)?)?;
    module.add_function(wrap_pyfunction!(parse_command, &module)?)?;
    module.add_function(wrap_pyfunction!(is_heartbeat, &module)?)?;
    module.add_function(wrap_pyfunction!(should_defer, &module)?)?;
    module.add_function(wrap_pyfunction!(is_due, &module)?)?;
    module.add_function(wrap_pyfunction!(next_run, &module)?)?;
    module.add_function(wrap_pyfunction!(format_job, &module)?)?;
    module.add(
        "DEFAULT_HEARTBEAT_SCHEDULE",
        pa_core::cron::DEFAULT_HEARTBEAT_SCHEDULE,
    )?;
    parent.add_submodule(&module)?;
    Ok(())
}
