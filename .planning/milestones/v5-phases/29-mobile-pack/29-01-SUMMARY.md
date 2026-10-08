# Summary 29-01: Mobile tools, skills, and device transports

## What shipped

`omega_prime/tools/mobile.py`: 13 registry tools porting desk `mobile.py` (Play
edit/track/update/commit flows, TestFlight + phased release/pause, size
delta extended to IPA, lint/entitlement/risk regexes verbatim) plus device
list/review/act. The desk's "approval text must say full rollout" rule
becomes an explicit `confirm_full: bool` (deviation noted). Approval on
the 4 release writes + device act.

`omega_prime/tools/devices.py`: adb (devices/screencap parsing), simctl (device
list/screenshot parsing), Appium (lazy client; screenshot + tap/type/back).
`pyproject.toml` gains `Appium-Python-Client>=4.0`.

`omega_prime/skills/android/SKILL.md`, `omega_prime/skills/ios/SKILL.md`: desk skills with
`bots:` repointed. Roster, policy, composition extended.

## Verification

- `.venv/bin/python -m pytest omega_prime/tests/test_mobile.py -q` → exit 0, 7 passed.
- `.venv/bin/python -m pytest omega_prime/tests -q` → exit 0, 200 passed (193 + 7).
- `.venv/bin/python -m omega_prime.evals.runner omega_prime/evals/cases` → exit 0, 6 passed.
- `bash omega_prime/scripts/assemble-prompts.sh --check` → exit 0.
