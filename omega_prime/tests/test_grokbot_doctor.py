"""Tests for Grok Bot Preflight Health Doctor."""

from omega_prime.grokbot.doctor import GrokBotDoctor, run_doctor_checks


def test_doctor_run_all_checks():
    doctor = GrokBotDoctor()
    checks = doctor.run_all_checks(check_port=59123)
    check_ids = [c.id for c in checks]

    assert "python_version" in check_ids
    assert "virtual_env" in check_ids
    assert "submodule_prime_agent" in check_ids
    assert "prompt_assembled" in check_ids
    assert "mcp_dependencies" in check_ids
    assert "manifest_generation" in check_ids
    assert "port_availability" in check_ids
    assert "audit_writeable" in check_ids

    # Port 59123 should be free
    port_check = next(c for c in checks if c.id == "port_availability")
    assert port_check.status == "PASS"


def test_run_doctor_checks_summary():
    summary = run_doctor_checks(port=59124)
    assert "passed" in summary
    assert "checks" in summary
    assert len(summary["checks"]) >= 8
