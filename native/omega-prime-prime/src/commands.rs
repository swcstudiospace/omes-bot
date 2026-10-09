// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Spectrum Web Co
//! Bindings for Prime's `/goal` and `/autonomous` argument parsers.
//!
//! These are the functions `SessionEngine` calls before it mutates goal or
//! autonomous state. The strings and the error text come from `pa-core`.

use pa_core::autonomous::AgentAutonomousStatus;
use pa_core::slash_command_args::{AutonomousCommand, GoalCommand};
use pyo3::prelude::*;
use serde_json::{json, Value};

use crate::convert::{from_py, py_err, to_py};

fn goal_command(command: GoalCommand) -> Value {
    match command {
        GoalCommand::Status => json!({"command": "status"}),
        GoalCommand::Clear => json!({"command": "clear"}),
        GoalCommand::Pause => json!({"command": "pause"}),
        GoalCommand::Resume => json!({"command": "resume"}),
        GoalCommand::Start {
            objective,
            token_budget,
        } => json!({
            "command": "start",
            "objective": objective,
            "tokenBudget": token_budget,
        }),
    }
}

fn autonomous_command(py: Python<'_>, command: AutonomousCommand) -> PyResult<PyObject> {
    let value = match command {
        AutonomousCommand::Status => json!({"command": "status"}),
        AutonomousCommand::Off => json!({"command": "off"}),
        AutonomousCommand::On { config } => {
            let mut body = json!({"command": "on"});
            body["config"] = serde_json::to_value(&config).map_err(py_err)?;
            body
        }
    };
    to_py(py, &value)
}

/// Parse the text after `/goal`.
#[pyfunction]
pub fn parse_goal(py: Python<'_>, args: &str) -> PyResult<PyObject> {
    let command = pa_core::slash_command_args::parse_goal_command(args).map_err(py_err)?;
    to_py(py, &goal_command(command))
}

/// Parse the text after `/autonomous`. `on` includes the camelCase config.
#[pyfunction]
pub fn parse_autonomous(py: Python<'_>, args: &str) -> PyResult<PyObject> {
    let command = pa_core::slash_command_args::parse_autonomous_command(args).map_err(py_err)?;
    autonomous_command(py, command)
}

/// The `[autonomous-status: ...]` block from `format_autonomous_status`.
#[pyfunction]
pub fn format_autonomous_status(py: Python<'_>, status: Bound<'_, PyAny>) -> PyResult<String> {
    let status = from_py::<AgentAutonomousStatus>(py, &status)?;
    Ok(pa_core::slash_command_args::format_autonomous_status(
        &status,
    ))
}

pub fn register(parent: &Bound<'_, PyModule>) -> PyResult<()> {
    let module = PyModule::new(parent.py(), "commands")?;
    module.add_function(wrap_pyfunction!(parse_goal, &module)?)?;
    module.add_function(wrap_pyfunction!(parse_autonomous, &module)?)?;
    module.add_function(wrap_pyfunction!(format_autonomous_status, &module)?)?;
    module.add(
        "AUTONOMOUS_BUDGET_USAGE",
        pa_core::slash_command_args::AUTONOMOUS_BUDGET_USAGE,
    )?;
    parent.add_submodule(&module)?;
    Ok(())
}
