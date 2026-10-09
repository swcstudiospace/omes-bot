// SPDX-License-Identifier: AGPL-3.0-only
// Copyright (C) 2026 Spectrum Web Co
//! Bindings for the REPL protocol (`pa_core::kernel::protocol`, version 3).
//!
//! `Event` has no serde impl, so `parse_event` rebuilds the frame from the
//! parsed enum. `encode_request` constructs a [`Request`] and returns that
//! value's own `to_json()` object, which is the stdin frame.

use pa_core::kernel::protocol::{Event, Request};
use pyo3::prelude::*;
use serde_json::{json, Map, Value};

use crate::convert::{from_py, py_err, to_py};

fn req_str(obj: &Map<String, Value>, keys: &[&str]) -> PyResult<String> {
    for key in keys {
        if let Some(value) = obj.get(*key) {
            return value
                .as_str()
                .map(str::to_string)
                .ok_or_else(|| py_err(format!("{key} must be a string")));
        }
    }
    Err(py_err(format!("kernel request needs {}", keys[0])))
}

fn req_u64(obj: &Map<String, Value>, keys: &[&str]) -> PyResult<u64> {
    for key in keys {
        if let Some(value) = obj.get(*key) {
            return value
                .as_u64()
                .ok_or_else(|| py_err(format!("{key} must be a non-negative integer")));
        }
    }
    Err(py_err(format!("kernel request needs {}", keys[0])))
}

fn req_bool(obj: &Map<String, Value>, keys: &[&str]) -> PyResult<bool> {
    for key in keys {
        if let Some(value) = obj.get(*key) {
            return value
                .as_bool()
                .ok_or_else(|| py_err(format!("{key} must be a boolean")));
        }
    }
    Err(py_err(format!("kernel request needs {}", keys[0])))
}

fn request_from_value(value: &Value) -> PyResult<Request> {
    let obj = value
        .as_object()
        .ok_or_else(|| py_err("kernel request must be an object"))?;
    let kind = obj
        .get("type")
        .and_then(Value::as_str)
        .ok_or_else(|| py_err("kernel request needs a type"))?;
    match kind {
        "execute" => Ok(Request::Execute {
            code: req_str(obj, &["code"])?,
        }),
        "interrupt" => Ok(Request::Interrupt),
        "host_reply" => Ok(Request::HostReply {
            data: obj.get("data").cloned().unwrap_or(Value::Null),
        }),
        "snapshot" => Ok(Request::Snapshot {
            path: req_str(obj, &["path"])?,
            manifest_path: req_str(obj, &["manifest_path", "manifestPath"])?,
            max_bytes: req_u64(obj, &["max_bytes", "maxBytes"])?,
            max_variable_bytes: req_u64(obj, &["max_variable_bytes", "maxVariableBytes"])?,
            prune_oversized: req_bool(obj, &["prune_oversized", "pruneOversized"])?,
        }),
        "restore" => Ok(Request::Restore {
            path: req_str(obj, &["path"])?,
            max_bytes: req_u64(obj, &["max_bytes", "maxBytes"])?,
            max_variable_bytes: req_u64(obj, &["max_variable_bytes", "maxVariableBytes"])?,
        }),
        "list_names" => Ok(Request::ListNames),
        "mcp_status" => {
            let servers = obj
                .get("servers")
                .cloned()
                .ok_or_else(|| py_err("kernel request needs servers"))?;
            let servers = serde_json::from_value::<Vec<String>>(servers)
                .map_err(|_| py_err("servers must be a list of strings"))?;
            Ok(Request::McpStatus {
                servers,
                timeout_ms: req_u64(obj, &["timeout_ms", "timeoutMs"])?,
            })
        }
        "shutdown" => Ok(Request::Shutdown),
        other => Err(py_err(format!("unknown kernel request type '{other}'"))),
    }
}

fn event_to_value(event: Event) -> Value {
    match event {
        Event::Ready { protocol } => json!({"event": "ready", "protocol": protocol}),
        Event::Stdout { id, text } => json!({"event": "stdout", "id": id, "text": text}),
        Event::Stderr { id, text } => json!({"event": "stderr", "id": id, "text": text}),
        Event::Result { id, text } => json!({"event": "result", "id": id, "text": text}),
        Event::Display { id, data } => json!({"event": "display", "id": id, "data": data}),
        Event::HostRequest { id, data } => {
            json!({"event": "host_request", "id": id, "data": data})
        }
        Event::Error {
            id,
            ename,
            evalue,
            traceback,
        } => json!({
            "event": "error",
            "id": id,
            "ename": ename,
            "evalue": evalue,
            "traceback": traceback,
        }),
        Event::Done { id, fields } => json!({"event": "done", "id": id, "fields": fields}),
    }
}

/// Parse one protocol line into a dict. Unknown or id-less frames raise `ValueError`.
#[pyfunction]
pub fn parse_event(py: Python<'_>, line: &str) -> PyResult<PyObject> {
    let event = pa_core::kernel::protocol::parse_event(line).map_err(py_err)?;
    to_py(py, &event_to_value(event))
}

/// Validate a request dict and return the JSON object `Request::to_json` writes to stdin.
#[pyfunction]
pub fn encode_request(py: Python<'_>, body: Bound<'_, PyAny>) -> PyResult<PyObject> {
    let value = from_py::<Value>(py, &body)?;
    let request = request_from_value(&value)?;
    to_py(py, &request.to_json())
}

pub fn register(parent: &Bound<'_, PyModule>) -> PyResult<()> {
    let module = PyModule::new(parent.py(), "protocol")?;
    module.add_function(wrap_pyfunction!(parse_event, &module)?)?;
    module.add_function(wrap_pyfunction!(encode_request, &module)?)?;
    module.add(
        "REPL_PROTOCOL_VERSION",
        pa_core::kernel::protocol::REPL_PROTOCOL_VERSION,
    )?;
    parent.add_submodule(&module)?;
    Ok(())
}
