// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Spectrum Web Co
//! Bindings for the continual-harness history in `pa_core::refinement`.
//!
//! Append and load hit the history file under the directory the caller passes.
//! They do not start a harness.

use std::path::Path;

use pa_core::refinement::{HarnessScope, RefinementResult};
use pyo3::prelude::*;

use crate::convert::{from_py, py_err, to_py};

fn scope_name(scope: HarnessScope) -> &'static str {
    match scope {
        HarnessScope::Local => "local",
        HarnessScope::Global => "global",
    }
}

/// `<dir>/refinement_history.jsonl`.
#[pyfunction]
pub fn history_path(directory: &str) -> String {
    pa_core::refinement::get_refinement_history_path(Path::new(directory))
        .to_string_lossy()
        .into_owned()
}

/// `"local"`, `"global"`, or `None` when the result does not name one scope.
#[pyfunction]
pub fn infer_scope(py: Python<'_>, result: Bound<'_, PyAny>) -> PyResult<Option<String>> {
    let result = from_py::<RefinementResult>(py, &result)?;
    Ok(pa_core::refinement::infer_refinement_result_scope(&result)
        .map(|scope| scope_name(scope).to_string()))
}

/// Append one result to the global history JSONL. Returns the file path.
#[pyfunction]
pub fn append(py: Python<'_>, directory: &str, result: Bound<'_, PyAny>) -> PyResult<String> {
    let result = from_py::<RefinementResult>(py, &result)?;
    let path = pa_core::refinement::append_global_refinement(Path::new(directory), &result)
        .map_err(py_err)?;
    Ok(path.to_string_lossy().into_owned())
}

/// Load the history. Malformed lines are skipped, matching Prime.
#[pyfunction]
pub fn load_history(py: Python<'_>, directory: &str) -> PyResult<PyObject> {
    let rows = pa_core::refinement::load_global_refinement_history(Path::new(directory));
    to_py(py, &rows)
}

pub fn register(parent: &Bound<'_, PyModule>) -> PyResult<()> {
    let module = PyModule::new(parent.py(), "refinement")?;
    module.add_function(wrap_pyfunction!(history_path, &module)?)?;
    module.add_function(wrap_pyfunction!(infer_scope, &module)?)?;
    module.add_function(wrap_pyfunction!(append, &module)?)?;
    module.add_function(wrap_pyfunction!(load_history, &module)?)?;
    module.add(
        "HISTORY_FILE_NAME",
        pa_core::refinement::REFINEMENT_HISTORY_FILE_NAME,
    )?;
    parent.add_submodule(&module)?;
    Ok(())
}
