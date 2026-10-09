// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Spectrum Web Co
//! JSON bridge between Python objects and the Prime wire types.
//!
//! Prime's public structs already implement serde. Round-tripping through
//! `json.dumps` / `json.loads` keeps the binding crate free of a second
//! Python-serde dependency and preserves each type's own rename rules.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use serde::de::DeserializeOwned;
use serde::Serialize;

pub fn py_err(err: impl ToString) -> PyErr {
    PyValueError::new_err(err.to_string())
}

pub fn from_py<T: DeserializeOwned>(py: Python<'_>, obj: &Bound<'_, PyAny>) -> PyResult<T> {
    let text: String = py
        .import("json")?
        .getattr("dumps")?
        .call1((obj,))?
        .extract()?;
    serde_json::from_str(&text).map_err(py_err)
}

pub fn to_py<T: Serialize>(py: Python<'_>, value: &T) -> PyResult<PyObject> {
    let text = serde_json::to_string(value).map_err(py_err)?;
    Ok(py
        .import("json")?
        .getattr("loads")?
        .call1((text,))?
        .unbind())
}
