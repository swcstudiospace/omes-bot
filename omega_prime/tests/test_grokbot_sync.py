"""Tests for Grok Bot Dynamic Capability & Prompt Synchronizer."""

import json
from pathlib import Path

from omega_prime.grokbot.manifest import generate_grokbot_manifest
from omega_prime.grokbot.sync import check_prompt_sync, get_active_family_flags


def test_get_active_family_flags():
    flags = get_active_family_flags()
    assert "rlm" in flags
    assert "kernel" in flags
    assert isinstance(flags["rlm"], bool)


def test_check_prompt_sync_baseline():
    report = check_prompt_sync()
    assert report.in_sync is True
    assert report.num_tools > 100
    assert report.num_skills > 20
    assert report.prompt_length > 1000
    assert report.diff is None


def test_check_prompt_sync_drift_detected(tmp_path: Path):
    manifest_file = tmp_path / "modified_manifest.json"
    manifest_data = generate_grokbot_manifest()
    # Artificially alter manifest
    manifest_data["bot"]["skills"] = ["custom-skill-only"]
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")

    report = check_prompt_sync(manifest_path=manifest_file)
    assert report.in_sync is False
    assert report.diff is not None
    assert "custom-skill-only" in report.diff
