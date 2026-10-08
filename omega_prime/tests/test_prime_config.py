"""Tests for the v10 config surface (omega_prime/config.py)."""

from __future__ import annotations

import json

from omega_prime.config import (
    PRIME_FAMILIES,
    family_config,
    load_config,
    prime_enabled,
)


def test_defaults_all_families_off(tmp_path):
    config = load_config(tmp_path)
    for family in PRIME_FAMILIES:
        assert prime_enabled(config, family) is False


def test_missing_file_is_defaults(tmp_path):
    config = load_config(tmp_path / "nowhere")
    assert prime_enabled(config, "rlm") is False


def test_file_enables_family(tmp_path):
    (tmp_path / "omega-prime.json").write_text(
        json.dumps({"prime": {"rlm": {"enabled": True}}})
    )
    config = load_config(tmp_path)
    assert prime_enabled(config, "rlm") is True
    assert prime_enabled(config, "harness") is False


def test_env_override_enables_family(tmp_path, monkeypatch):
    monkeypatch.setenv("OMEGA_PRIME_PRIME_RLM_ENABLED", "1")
    config = load_config(tmp_path)
    assert prime_enabled(config, "rlm") is True


def test_env_override_beats_file(tmp_path, monkeypatch):
    (tmp_path / "omega-prime.json").write_text(
        json.dumps({"prime": {"rlm": {"enabled": True}}})
    )
    monkeypatch.setenv("OMEGA_PRIME_PRIME_RLM_ENABLED", "0")
    config = load_config(tmp_path)
    assert prime_enabled(config, "rlm") is False


def test_unknown_family_is_disabled(tmp_path):
    config = load_config(tmp_path)
    assert prime_enabled(config, "nonexistent") is False


def test_family_config_returns_subtree(tmp_path):
    (tmp_path / "omega-prime.json").write_text(
        json.dumps({"prime": {"autonomous": {"enabled": True, "max_turns": 8}}})
    )
    config = load_config(tmp_path)
    assert family_config(config, "autonomous")["max_turns"] == 8
    # Defaults pre-populate every family as disabled.
    assert family_config(config, "rlm") == {"enabled": False}


def test_non_object_file_rejected(tmp_path):
    (tmp_path / "omega-prime.json").write_text("[1, 2]")
    try:
        load_config(tmp_path)
    except ValueError as exc:
        assert "JSON object" in str(exc)
    else:
        raise AssertionError("expected ValueError")
