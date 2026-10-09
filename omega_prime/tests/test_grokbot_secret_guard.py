# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (C) 2026 Spectrum Web Co
"""Tests for the Grok Bot secret-redaction gate."""

import hashlib
import json
import os
import secrets
import string
from pathlib import Path

import pytest

from omega_prime.grokbot.secret_guard import (
    SecretLeakError,
    assert_no_secrets,
    enforce_token_file_mode,
)


def _generic_token() -> str:
    from omega_prime.grokbot.secret_guard import _shannon_entropy

    alphabet = string.ascii_letters + string.digits
    for _ in range(1000):
        candidate = "".join(secrets.choice(alphabet) for _ in range(36))
        if not (
            any(char.islower() for char in candidate)
            and any(char.isupper() for char in candidate)
            and any(char.isdigit() for char in candidate)
        ):
            continue
        if _shannon_entropy(candidate) >= 4.5:
            return candidate
    raise AssertionError("could not draw generic token with entropy >= 4.5")


def _pem_block() -> str:
    header = "-----BEGIN " + "RSA PRIVATE " + "KEY-----"
    footer = "-----END " + "RSA PRIVATE " + "KEY-----"
    body = "MIIB" + secrets.token_urlsafe(24)
    return f"{header}\n{body}\n{footer}"


_SK_TOKEN = "sk-" + secrets.token_hex(14)
_OMK_TOKEN = "omk_" + secrets.token_hex(9)
_BEARER_TOKEN = "Bearer " + secrets.token_urlsafe(21)
_GENERIC_TOKEN = _generic_token()
_PRIVATE_KEY_BLOCK = _pem_block()


def _clean_manifest_text() -> str:
    manifest = {
        "manifest_version": "1.0.0",
        "bot": {
            "name": "Omega Prime",
            "skills": ["programming_desk_run_terminal_approval_flow"],
        },
        "mcp_server": {
            "transport": "sse",
            "url": "https://grok.internal:8000/sse",
            "auth": {"type": "none", "token_env": "MCP_AUTH_TOKEN"},
            "rostered_tool_count": 128,
            "tools": ["read_file", "run_terminal", "supervisor_status"],
        },
        "digest": hashlib.sha256(b"manifest-fixture").hexdigest(),
        "run_id": "123e4567-e89b-12d3-a456-426614174000",
    }
    return json.dumps(manifest, sort_keys=True)


def test_clean_manifest_passes():
    assert_no_secrets(_clean_manifest_text(), "manifest")


def test_clean_0600_file_passes(tmp_path: Path):
    target = tmp_path / "manifest.json"
    target.write_text(_clean_manifest_text(), encoding="utf-8")
    target.chmod(0o600)
    assert_no_secrets(target, "manifest")


@pytest.mark.parametrize(
    "secret",
    [
        _SK_TOKEN,
        _OMK_TOKEN,
        _BEARER_TOKEN,
        "Authorization: " + "Bearer " + secrets.token_hex(10),
        "api_" + "key=" + secrets.token_hex(8),
        _PRIVATE_KEY_BLOCK,
        f"session resumed with {_GENERIC_TOKEN} aboard",
    ],
)
def test_token_bearing_text_raises_without_echo(secret: str):
    with pytest.raises(SecretLeakError) as excinfo:
        assert_no_secrets(f"diag bundle body: {secret}", "diag")
    message = str(excinfo.value)
    assert "token-pattern" in message
    assert "diag" in message
    for fragment in secret.split():
        if len(fragment) >= 8:
            assert fragment not in message


def test_token_bearing_file_raises_without_echo(tmp_path: Path):
    target = tmp_path / "bundle.txt"
    target.write_text(f"clean header\n{_SK_TOKEN}\n", encoding="utf-8")
    target.chmod(0o600)
    with pytest.raises(SecretLeakError) as excinfo:
        assert_no_secrets(target, "diag")
    message = str(excinfo.value)
    assert "token-pattern" in message
    assert _SK_TOKEN not in message


def test_wrong_mode_file_raises(tmp_path: Path):
    target = tmp_path / "token.env"
    target.write_text("nothing secret here\n", encoding="utf-8")
    target.chmod(0o644)
    with pytest.raises(SecretLeakError) as excinfo:
        assert_no_secrets(target, "token-file")
    assert "0600-violation" in str(excinfo.value)
    with pytest.raises(SecretLeakError) as excinfo:
        enforce_token_file_mode(target)
    assert "0600-violation" in str(excinfo.value)


def test_wrong_mode_message_hides_contents(tmp_path: Path):
    target = tmp_path / "token.env"
    target.write_text(_SK_TOKEN + "\n", encoding="utf-8")
    target.chmod(0o640)
    with pytest.raises(SecretLeakError) as excinfo:
        enforce_token_file_mode(target)
    message = str(excinfo.value)
    assert "0600-violation" in message
    assert _SK_TOKEN not in message


def test_directory_is_not_a_token_file(tmp_path: Path):
    with pytest.raises(SecretLeakError, match="0600-violation"):
        enforce_token_file_mode(tmp_path)


def test_enforce_0600_returns_path(tmp_path: Path):
    target = tmp_path / "token.env"
    target.write_text("opaque-secret\n", encoding="utf-8")
    target.chmod(0o600)
    assert enforce_token_file_mode(target) == target


def test_str_path_is_scanned_as_text_not_opened(tmp_path: Path):
    target = tmp_path / "manifest.json"
    target.write_text(_clean_manifest_text(), encoding="utf-8")
    target.chmod(0o644)
    # A `str` payload is literal text: the 0644 file on disk is never mode-checked.
    assert_no_secrets(os.fspath(target), "manifest")
