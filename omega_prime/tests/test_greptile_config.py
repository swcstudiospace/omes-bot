"""Phase 45: the Greptile repo config stays inside the documented schema."""

from __future__ import annotations

import json
from pathlib import Path

OMEGA_PRIME = Path(__file__).resolve().parents[1]
ROOT = OMEGA_PRIME.parent

TOP_LEVEL_KEYS = frozenset(
    {
        "strictness",
        "commentTypes",
        "fileChangeLimit",
        "labels",
        "disabledLabels",
        "includeAuthors",
        "excludeAuthors",
        "includeBranches",
        "excludeBranches",
        "includeKeywords",
        "ignoreKeywords",
        "ignorePatterns",
        "triggerOnUpdates",
        "statusCheck",
        "statusCommentsEnabled",
        "skipReview",
        "shouldUpdateDescription",
        "updateSummaryOnly",
        "fixWithAI",
        "hideFooter",
        "autoApprove",
        "summarySection",
        "context",
        "instructions",
        "rules",
        "disabledRules",
    }
)

SEVERITIES = frozenset({"low", "medium", "high"})


def _config() -> dict:
    path = ROOT / ".greptile" / "config.json"
    parsed = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def test_config_keys_are_documented() -> None:
    config = _config()
    assert set(config) <= TOP_LEVEL_KEYS
    assert config.get("strictness") in (1, 2, 3)
    assert isinstance(config.get("commentTypes"), list)
    assert config.get("statusCheck") is True


def test_rules_have_shape_and_scope() -> None:
    config = _config()
    rules = config.get("rules", [])
    assert len(rules) >= 3
    seen_ids = set()
    for rule in rules:
        assert isinstance(rule.get("rule"), str) and rule["rule"]
        assert rule.get("severity", "medium") in SEVERITIES
        if "id" in rule:
            assert rule["id"] not in seen_ids
            seen_ids.add(rule["id"])
        for scope in rule.get("scope", []):
            assert ".." not in scope
            assert (ROOT / scope.split("*")[0]).exists()
