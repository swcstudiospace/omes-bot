---
phase: 63-grokbot-enterprise-improvements
plan: "07"
subsystem: grokbot-deploy
tags: [docker, compose, systemd, kubernetes, hardening, ci]
requires:
  - phase: 62
    provides: The host, its probes, graceful drain and token-file handling
provides:
  - Deterministic renderer for Docker, Compose, systemd and Kubernetes artifacts, and a hardening checker
  - Committed `Dockerfile` equal to the renderer output
  - `OMEGA_PRIME_STATE_DIR` so the root filesystem can be read-only
  - Image CI workflow (build, boot hardened, verify, SIGTERM, SBOM, scan)
affects: [63-06, v11-closeout]
tech-stack:
  added: []
  patterns: [render-and-drift-test, read-only root with a state volume, token via mounted file]
key-files:
  created:
    - omega_prime/grokbot/deploy.py
    - omega_prime/tests/test_grokbot_deploy.py
    - omega_prime/tests/test_grokbot_state_dir.py
    - Dockerfile
    - .dockerignore
    - .github/workflows/grokbot-image.yml
    - docs/deploy.md
  modified:
    - omega_prime/mcp_server.py
    - .github/dependabot.yml
    - docs/SUMMARY.md
key-decisions:
  - "No secret is ever inlined: the host reads its token from a mounted file; the Kubernetes manifest copies it with an init container into a 0600 file in a memory emptyDir, because `fsGroup` makes Secret volumes group-readable and the host (correctly) rejects group-readable token files."
  - "`OMEGA_PRIME_STATE_DIR` redirects memory and the sessions DB (the store wrote MEMORY.md and USER.md into the Python package directory); skills stay under the root, so runtime skill creation needs a writable skills volume."
  - "Kubernetes sleeps 5 s in a `preStop` hook and uses `terminationGracePeriodSeconds: 45`: with nothing in flight the host exits within about 0.1 s of SIGTERM, so without the hook a load balancer would get no window to see `/readyz` go 503."
  - "The image tag defaults to the package version (`0.1.0`), not `latest`."
duration: 1 wave
completed: 2026-10-09
---

# Summary: 63-07 Deployment kit

Commit `ece986b`. Requirement: GRI-07.

## Verified on the real artifacts (not only parsed)

`actionlint` accepts every workflow; `docker build --check .` reports no warnings; the image built from the
committed `Dockerfile` (1.99 GB; the dependency tree includes pyrit and transformers) runs as uid 10001 with
`--read-only --cap-drop ALL --security-opt no-new-privileges`, a tmpfs state volume and the token mounted from
a 0600 file; `/healthz` and `/readyz` are 200, `/sse` is 401 without a token and for `?token=`, a real MCP client
lists 108 tools and a `memory` write lands in the state volume (not in the source package), the audit log inside
the container verifies, the token appears 0 times in the container log, and `docker stop` exits 0 in 1.3 s.

## Not exercised

The Kubernetes manifest was not applied to a live cluster and the systemd unit was not started
(`systemd-analyze verify` only reports the missing binary). The image workflow runs on GitHub, not locally.
