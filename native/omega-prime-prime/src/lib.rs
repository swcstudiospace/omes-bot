// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Spectrum Web Co
//! PyO3 bindings for the pinned Prime crates.
//!
//! The crate sits outside the Prime workspace because that workspace forbids
//! `unsafe` and PyO3 needs it. `prime-agent/` is not modified. `ai.complete`
//! runs real Prime providers; `crates.probe` only exercises helpers from each
//! workspace member. Nothing here starts the terminal UI or a daemon worker.

mod ai;
mod autonomous;
mod commands;
mod convert;
mod goals;
mod heartbeat;
mod protocol;
mod refinement;
mod surface;

use pyo3::prelude::*;

const CRATES: [&str; 9] = [
    "pa-telemetry",
    "pa-types",
    "pa-ai",
    "pa-models",
    "pa-agent",
    "pa-core",
    "pa-daemon",
    "pa-tui",
    "pa-cli",
];

/// Workspace member names, in Cargo.toml order.
#[pyfunction]
fn linked_crates() -> Vec<String> {
    CRATES.iter().map(|name| (*name).to_string()).collect()
}

/// Reference one public item from each Prime crate so the linker keeps all nine.
#[pyfunction]
fn touch_crates() -> usize {
    let mut n = pa_telemetry::version().len();
    n += std::mem::size_of_val(&pa_types::JsNumber(0.0));
    n += std::mem::size_of::<pa_ai::StreamFailureKind>();
    n += pa_models::CATALOG_REFRESH_INTERVAL_MS as usize;
    n += pa_agent::now_ms().unsigned_abs() as usize;
    n += usize::from(pa_core::autonomous::is_unlimited_autonomous_limit(0));
    let _ = pa_core::kernel::protocol::parse_event("");
    n += pa_daemon::descriptor::SUPERVISOR_CONFIG_FILE_NAME.len();
    n += std::mem::size_of::<pa_tui::agents_view_search::SessionSearchText>();
    n += std::mem::size_of::<pa_cli::RunOptions>();
    n
}

#[pyfunction]
fn validate_goal_objective(text: &str) -> PyResult<String> {
    goals::validate_goal_objective(text)
}

#[pyfunction]
fn goal_token_delta(input: i64, output: i64) -> u64 {
    goals::goal_token_delta(input, output)
}

/// Same dict as `protocol.parse_event`.
#[pyfunction]
fn parse_kernel_event(py: Python<'_>, line: &str) -> PyResult<PyObject> {
    protocol::parse_event(py, line)
}

#[pymodule]
fn omega_prime_prime(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.setattr(
        "__doc__",
        "PyO3 bindings for the pinned Prime crates.\n\n\
         goals, autonomous, protocol, heartbeat, refinement, and commands call\n\
         pa-core. crates.probe calls pa-telemetry, pa-types, pa-ai, pa-models,\n\
         pa-agent, pa-core, pa-daemon, pa-tui, and pa-cli. The TUI and the daemon\n\
         worker are not started.",
    )?;
    ai::register(m)?;
    goals::register(m)?;
    autonomous::register(m)?;
    protocol::register(m)?;
    heartbeat::register(m)?;
    refinement::register(m)?;
    commands::register(m)?;
    surface::register(m)?;
    m.add_function(wrap_pyfunction!(linked_crates, m)?)?;
    m.add_function(wrap_pyfunction!(touch_crates, m)?)?;
    m.add_function(wrap_pyfunction!(validate_goal_objective, m)?)?;
    m.add_function(wrap_pyfunction!(goal_token_delta, m)?)?;
    m.add_function(wrap_pyfunction!(parse_kernel_event, m)?)?;
    Ok(())
}
