"""Tests for Grok Bot Manifest Generator."""

from pathlib import Path

from omega_prime.grokbot.manifest import (
    find_repo_root,
    generate_manifest,
    get_assembled_prompt,
    parse_template_sections,
)


def test_find_repo_root():
    root = find_repo_root()
    assert (root / "pyproject.toml").is_file()
    assert (root / "omega_prime").is_dir()


def test_parse_template_sections(tmp_path: Path):
    sample_md = tmp_path / "test.md"
    sample_md.write_text(
        "# Header\n"
        "Some top description\n\n"
        "## Enabled Skills\n"
        "- skill-alpha\n"
        "- skill-beta\n\n"
        "## Routines\n"
        "- routine-one\n",
        encoding="utf-8",
    )
    data = parse_template_sections(sample_md)
    assert data["skills"] == ["skill-alpha", "skill-beta"]
    assert data["routines"] == ["routine-one"]


def test_generate_manifest_defaults():
    root = find_repo_root()
    manifest = generate_manifest(
        root, transport="sse", host_url="https://grok.internal:8000/sse"
    )
    assert manifest["manifest_version"] == "1.0.0"
    assert manifest["bot"]["name"] == "Omega Prime"
    assert len(manifest["bot"]["skills"]) >= 20
    assert manifest["mcp_server"]["transport"] == "sse"
    assert manifest["mcp_server"]["url"] == "https://grok.internal:8000/sse"
    assert manifest["mcp_server"]["auth"]["type"] == "none"
    assert manifest["mcp_server"]["rostered_tool_count"] > 100
    assert len(manifest["mcp_server"]["tools"]) > 100
    assert manifest["capabilities"]["programming_desk"] is True


def test_generate_manifest_with_token():
    root = find_repo_root()
    manifest = generate_manifest(root, auth_token="secret-grok-token")
    assert manifest["mcp_server"]["auth"]["type"] == "bearer"
    assert manifest["mcp_server"]["auth"]["token_env"] == "MCP_AUTH_TOKEN"


def test_get_assembled_prompt():
    prompt = get_assembled_prompt()
    assert "<core_directives" in prompt or len(prompt) > 500
