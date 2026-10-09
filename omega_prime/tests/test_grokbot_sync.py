"""Tests for Grok Bot Dynamic Capability & Prompt Synchronizer."""

import json
import shutil
from pathlib import Path

import pytest

from omega_prime.config import PRIME_FAMILIES
from omega_prime.grokbot.manifest import find_repo_root, generate_grokbot_manifest
from omega_prime.grokbot.sync import check_prompt_sync, get_active_family_flags, main


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


# --- phase 62-03: semantic drift ------------------------------------------


def _make_tree(base: Path) -> Path:
    src = find_repo_root() / "omega_prime"
    dst = base / "repo" / "omega_prime"
    ignore = shutil.ignore_patterns("__pycache__")
    for rel in ("contracts", "skills", "prompts-assembled", "grokbot/templates"):
        shutil.copytree(src / rel, dst / rel, ignore=ignore)
    (dst / "routines").mkdir()
    for routine in (src / "routines").glob("*.md"):
        shutil.copy2(routine, dst / "routines" / routine.name)
    return base / "repo"


@pytest.fixture
def tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for family in PRIME_FAMILIES:
        monkeypatch.delenv(f"OMEGA_PRIME_PRIME_{family.upper()}_ENABLED", raising=False)
    return _make_tree(tmp_path)


def _export(tree: Path, home: Path, name: str = "manifest.json", **kwargs) -> Path:
    path = home / name
    manifest = generate_grokbot_manifest(tree, home=home, **kwargs)
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


def test_same_settings_export_has_no_drift(tree: Path, tmp_path: Path):
    saved = _export(tree, tmp_path)
    report = check_prompt_sync(saved, root=tree, home=tmp_path)
    assert report.in_sync is True
    assert report.diff is None
    assert report.changed_sections == []
    assert report.added_tools == []
    assert report.removed_tools == []
    assert report.expected_digest == report.actual_digest
    assert len(report.expected_digest) == 64


def test_transport_url_and_auth_are_not_drift(tree: Path, tmp_path: Path):
    stdio = _export(tree, tmp_path, "stdio.json", transport="stdio")
    remote = _export(
        tree,
        tmp_path,
        "remote.json",
        host_url="http://0.0.0.0:9999/sse",
        public_url="https://grok.example.com",
        auth_token="tok-0123456789abcdef-secret",
    )
    for saved in (stdio, remote):
        report = check_prompt_sync(saved, root=tree, home=tmp_path)
        assert report.in_sync is True
        assert report.changed_sections == []
    args = ["--check", str(stdio), "--root", str(tree), "--home", str(tmp_path)]
    assert main(args) == 0


def test_tool_changes_are_reported(tree: Path, tmp_path: Path):
    saved = _export(tree, tmp_path)
    data = json.loads(saved.read_text(encoding="utf-8"))
    dropped = data["mcp_server"]["tools"].pop()
    data["mcp_server"]["tools"].append("ghost_tool")
    saved.write_text(json.dumps(data), encoding="utf-8")

    report = check_prompt_sync(saved, root=tree, home=tmp_path)
    assert report.in_sync is False
    assert report.added_tools == [dropped]
    assert report.removed_tools == ["ghost_tool"]
    assert report.changed_sections == ["mcp_server.tools"]
    assert report.diff is not None
    assert "ghost_tool" in report.diff
    assert report.expected_digest != report.actual_digest
    args = ["--check", str(saved), "--root", str(tree), "--home", str(tmp_path)]
    assert main(args) == 1


def test_changed_sections_are_named(tree: Path, tmp_path: Path):
    saved = _export(tree, tmp_path)
    data = json.loads(saved.read_text(encoding="utf-8"))
    data["bot"]["instructions"] += "\nstale"
    data["bot"]["routines"] = []
    data["mcp_server"]["approval_required"] = []
    data["capabilities"]["omp_harness"] = False
    saved.write_text(json.dumps(data), encoding="utf-8")

    report = check_prompt_sync(saved, root=tree, home=tmp_path)
    assert report.changed_sections == [
        "bot.instructions",
        "bot.routines",
        "mcp_server.approval_required",
        "capabilities",
    ]


def test_prime_flag_flip_is_drift_in_capabilities_and_tools(
    tree: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    saved = _export(tree, tmp_path)
    monkeypatch.setenv("OMEGA_PRIME_PRIME_GOALS_ENABLED", "1")

    report = check_prompt_sync(saved, root=tree, home=tmp_path)
    assert report.in_sync is False
    assert "capabilities" in report.changed_sections
    assert "mcp_server.tools" in report.changed_sections
    assert "mcp_server.approval_required" in report.changed_sections
    assert "bot.instructions" not in report.changed_sections
    assert "goal_set" in report.added_tools
    assert report.active_flags["goals"] is True


def test_prime_flag_flip_through_env_changes_capabilities(tree: Path, tmp_path: Path):
    saved = _export(tree, tmp_path)
    env = {"OMEGA_PRIME_PRIME_GOALS_ENABLED": "1"}
    report = check_prompt_sync(saved, root=tree, home=tmp_path, env=env)
    assert "capabilities" in report.changed_sections
    assert report.active_flags["goals"] is True
    assert get_active_family_flags(tree, env)["goals"] is True
    assert get_active_family_flags(tree, {})["goals"] is False


def test_missing_file_raises_and_main_exits_2(
    tree: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    missing = tmp_path / "nope.json"
    with pytest.raises(FileNotFoundError):
        check_prompt_sync(missing, root=tree, home=tmp_path)
    args = ["--check", str(missing), "--root", str(tree), "--home", str(tmp_path)]
    assert main(args) == 2
    assert "omega-prime-grokbot-sync:" in capsys.readouterr().err


def test_invalid_manifest_file_exits_2(tree: Path, tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("[1, 2]", encoding="utf-8")
    args = ["--check", str(bad), "--root", str(tree), "--home", str(tmp_path)]
    assert main(args) == 2
    bad.write_text("{not json", encoding="utf-8")
    assert main(args) == 2


def test_usage_error_exits_2():
    assert main(["--no-such-flag"]) == 2


def test_json_output_shape(
    tree: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    saved = _export(tree, tmp_path)
    data = json.loads(saved.read_text(encoding="utf-8"))
    removed = data["mcp_server"]["tools"].pop(0)
    saved.write_text(json.dumps(data), encoding="utf-8")

    args = ["--check", str(saved), "--json", "--root", str(tree)]
    args += ["--home", str(tmp_path)]
    assert main(args) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["in_sync"] is False
    assert payload["added_tools"] == [removed]
    assert payload["removed_tools"] == []
    assert payload["changed_sections"] == ["mcp_server.tools"]
    assert payload["has_diff"] is True
    assert payload["num_tools"] > 100
    assert set(payload["active_flags"]) == set(PRIME_FAMILIES)
    assert len(payload["expected_digest"]) == 64
    assert payload["expected_digest"] != payload["actual_digest"]


def test_in_sync_json_exit_zero(
    tree: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    saved = _export(tree, tmp_path)
    args = ["--check", str(saved), "--json", "--root", str(tree)]
    args += ["--home", str(tmp_path)]
    assert main(args) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["in_sync"] is True
    assert payload["changed_sections"] == []


def test_export_prompt_writes_file_and_keeps_exit_code(tree: Path, tmp_path: Path):
    out = tmp_path / "prompt.txt"
    base = ["--root", str(tree), "--home", str(tmp_path)]
    assert main(["--export-prompt", str(out), *base]) == 0
    expected = (tree / "omega_prime/prompts-assembled/OMEGA_PRIME.xml").read_text(
        encoding="utf-8"
    )
    assert out.read_text(encoding="utf-8") == expected

    clean = _export(tree, tmp_path)
    assert main(["--export-prompt", str(out), "--check", str(clean), *base]) == 0

    data = json.loads(clean.read_text(encoding="utf-8"))
    data["bot"]["skills"] = ["custom-skill-only"]
    clean.write_text(json.dumps(data), encoding="utf-8")
    out.unlink()
    assert main(["--export-prompt", str(out), "--check", str(clean), *base]) == 1
    assert out.read_text(encoding="utf-8") == expected


def test_cwd_does_not_matter(
    tree: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    saved = _export(tree, tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert check_prompt_sync(saved, root=tree, home=tmp_path).in_sync is True
    assert check_prompt_sync().in_sync is True
    assert get_active_family_flags()["rlm"] in (True, False)
