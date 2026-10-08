"""Pin-drift guard for the Prime Agent parity oracle.

The v10 merge keeps ``prime-agent/`` as an ignored, read-only upstream
checkout whose Rust workspace is the CI-built parity oracle
(``.github/workflows/rust-parity.yml``). Two surfaces record the pin:
``VENDOR.md`` (prose, the v1 precedent) and
``omega_prime/contracts/prime-agent.pin.json`` (machine-readable, consumed
by CI). This test fails when they drift apart — the roster drift-guard
precedent: two surfaces, one source of truth enforced by test.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN_PATH = ROOT / "omega_prime" / "contracts" / "prime-agent.pin.json"
VENDOR_PATH = ROOT / "VENDOR.md"

_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def _load_pin() -> dict:
    return json.loads(PIN_PATH.read_text(encoding="utf-8"))


def test_pin_file_has_required_keys_and_shapes() -> None:
    pin = _load_pin()
    assert pin["remote"] == "https://github.com/PrimeIntellect-ai/prime-agent.git"
    assert _COMMIT_RE.match(pin["commit"]), pin["commit"]
    assert re.match(r"^\d+\.\d+\.\d+$", pin["toolchain"]), pin["toolchain"]
    assert isinstance(pin["known_failing_tests"], list)


def test_pin_commit_matches_vendor_md() -> None:
    pin = _load_pin()
    vendor = VENDOR_PATH.read_text(encoding="utf-8")
    assert pin["commit"] in vendor, "VENDOR.md and prime-agent.pin.json drifted"
    assert "PrimeIntellect-ai/prime-agent" in vendor


def test_known_failing_tests_stay_scoped_to_the_documented_surface() -> None:
    """The exclusion set must only name the acp_mode_e2e tests recorded in
    the Phase 53 baseline (pa-cli ACP-stdio settle timing; pa-cli is out of
    v10 port scope). Any new exclusion needs baseline evidence and a reason,
    per the prime-agent AGENTS.md disabled-test rule."""
    pin = _load_pin()
    for name in pin["known_failing_tests"]:
        assert name.startswith("acp_"), name
