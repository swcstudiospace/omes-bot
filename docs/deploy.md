# Deploying the tool host

The Grok Bot tool host (`python -m omega_prime.mcp_server --transport sse`) ships with a deployment kit: a hardened
image definition, a renderer for four deployment targets, a checker, and an image CI workflow. Every target runs the
host as a non-root user on a read-only root filesystem with one writable state volume and `/tmp`, reads its bearer
token from a file the platform mounts, and exposes `/healthz` and `/readyz` for health probes. No artifact ever contains
a secret.

```bash
python -m omega_prime.grokbot.deploy render --target k8s --out deploy/k8s
python -m omega_prime.grokbot.deploy check deploy/k8s
```

`render` options: `--target {docker,compose,systemd,k8s}`, `--out DIR`, `--name` (default `omega-prime-mcp`, a DNS
label), `--image` (default `ghcr.io/swcstudiospace/omega-prime-mcp:0.1.0`), `--port` (default 8000), `--public-url`
(adds `--public-url` to the server arguments), `--uid` (default 10001, at least 1000) and `--force` (replace a file this
tool did not generate). Output is deterministic: the same options always produce the same bytes. `check` exits 0 when
clean or warnings only, 1 on any error finding, and 2 on bad usage; `--json` prints machine-readable findings.

## The token file

The host refuses to start on a non-loopback address without a token, and it refuses a token file that group or others
can read. Create a one-line file and hand it to the platform; never put the token in a command line, environment
variable, compose file, unit file or manifest.

```bash
umask 077
openssl rand -hex 24 > token
```

Clients send it as `Authorization: Bearer <token>`.

## Docker

```bash
python -m omega_prime.grokbot.deploy render --target docker --out .   # already committed at the repo root
docker build -t omega-prime-mcp .
sudo chown 10001:10001 token
docker run -d --name omega-prime-mcp \
  --read-only --tmpfs /tmp --cap-drop ALL --security-opt no-new-privileges:true \
  -v omega-prime-state:/var/lib/omega-prime \
  -v "$PWD/token:/run/secrets/omega_prime_token:ro" \
  -p 127.0.0.1:8000:8000 omega-prime-mcp
```

The committed `Dockerfile` and `.dockerignore` are byte-identical to `render --target docker` with default arguments (a
test enforces it). Change the generator, then regenerate; a Dependabot bump of the base image must be mirrored in
`BASE_IMAGE` in `omega_prime/grokbot/deploy.py`. The build installs `requirements-lock.txt` into `/opt/venv`, copies the
`omega_prime/` package (minus tests and caches) to `/app/omega_prime`, and runs with `--root /app`. The image runs as
numeric user `10001:10001`, has a stdlib-only `HEALTHCHECK` against `/healthz`, and uses `STOPSIGNAL SIGTERM`.

## Compose

```bash
python -m omega_prime.grokbot.deploy render --target compose --out deploy/compose
cd deploy/compose
install -d -m 0700 secrets && openssl rand -hex 24 > secrets/omega_prime_token
sudo chown 10001:10001 secrets/omega_prime_token && chmod 600 secrets/omega_prime_token
docker compose up -d
```

The service uses `read_only: true`, `tmpfs: [/tmp]`, `cap_drop: [ALL]`, `no-new-privileges`, a named state volume and a
file-based secret mounted at `/run/secrets/omega_prime_token`. Compose bind-mounts the file with its host owner, so the
file must be owned by the container user (uid 10001) and mode 0600. The port is published on `127.0.0.1` only; put a TLS
reverse proxy in front and pass `--public-url`.

## systemd

```bash
python -m omega_prime.grokbot.deploy render --target systemd --out /tmp/unit
sudo install -d /opt/omega-prime /etc/omega-prime
sudo cp -r omega_prime /opt/omega-prime/omega_prime
sudo python3.12 -m venv /opt/omega-prime/venv
sudo /opt/omega-prime/venv/bin/pip install -r requirements-lock.txt
sudo install -m 0600 token /etc/omega-prime/token
sudo install -m 0644 /tmp/unit/omega-prime-mcp.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now omega-prime-mcp
```

The unit uses `DynamicUser=yes`, `StateDirectory=omega-prime` (state under `/var/lib/omega-prime`) and
`LoadCredential=omega_prime_token:/etc/omega-prime/token`, so the service reads the token from its private credentials
directory (`%d`) and never from a world-visible path. It binds `127.0.0.1`; front it with a reverse proxy. Run
`systemd-analyze verify` on the installed unit; before the install layout above exists it only reports that the
`ExecStart` binary is missing.

## Kubernetes

```bash
python -m omega_prime.grokbot.deploy render --target k8s --out deploy/k8s
kubectl create secret generic omega-prime-token --from-file=omega_prime_token=./token
kubectl apply -f deploy/k8s/omega-prime-mcp.yaml
```

One multi-document file: a `Deployment`, a ClusterIP `Service`, a `NetworkPolicy` (ingress only from pods labelled
`omega-prime-mcp-client: "true"` in the same namespace) and a `PodDisruptionBudget`. The pod runs as `runAsUser` and
`fsGroup` 10001 with `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`, all capabilities dropped,
`seccompProfile: RuntimeDefault` and `automountServiceAccountToken: false`. `emptyDir` volumes back `/tmp`, the state
directory and the token copy.

- A Secret volume with `fsGroup` is group-readable, which the host rejects. An init container (same image, same
  hardening) therefore copies the token into an in-memory `emptyDir` as a 0600 file owned by uid 10001.
- One replica: SSE and Streamable HTTP sessions live in the process. Scale out only behind session affinity.
- Probes: `startupProbe` and `livenessProbe` on `/healthz`, `readinessProbe` on `/readyz`.
- State is an `emptyDir`; mount a PersistentVolumeClaim at `/var/lib/omega-prime` to keep memory and the audit log.
- Egress is not restricted; add an egress policy for your cluster if the connectors you enable need it.

## State volume and the read-only root filesystem

The image's root filesystem is read-only in every target. Everything the host writes goes to `/tmp` or the state volume
mounted at `/var/lib/omega-prime` (`HOME` and the `--home` directory):

- `OMEGA_PRIME_STATE_DIR=/var/lib/omega-prime/state` moves the memory store and the session database out of the source
  tree. Without it the host writes `omega_prime/memory/` and `omega_prime/sessions.db` under `--root`.
- `OMEGA_PRIME_AUDIT_LOG=/var/lib/omega-prime/audit/audit.jsonl` is the hash-chained audit trail.

Every write location of the default tool set:

| Location | Written by | Where it lands in the image |
| --- | --- | --- |
| `$OMEGA_PRIME_STATE_DIR/memory/` (`MEMORY.md`, `USER.md`) | `memory` tool | state volume |
| `$OMEGA_PRIME_STATE_DIR/sessions.db` | `session_search` store | state volume |
| `<root>/omega_prime/memory/`, `<root>/omega_prime/sessions.db` | the same, when the variable is unset | read-only; set the variable |
| audit log path (`--audit-log`) | host audit trail | state volume |
| `<home>/.omega-prime-exec/*.py` | `execute_code` scratch scripts | state volume |
| `<root>/omega_prime/skills/` | `skill_manage` (runtime skill creation) | read-only; mount a writable skills volume at `/app/omega_prime/skills` to allow it |
| `<root>/omega_prime/**` | `write_file`, `edit_file` and the other coding tools | read-only; these tools return an error |
| `<root>/.receipts/quality/`, receipt files under `<root>` | `qua_receipt_approve`, `qua_waiver_record` | read-only; the tools fail |
| caller-chosen screenshot paths | device, Appium and Playwright screenshot tools | choose a path under `/tmp` or the state volume |
| `/tmp` (render scratch, browser sandbox profile) | lead render, browser egress probe | `/tmp` tmpfs |
| `<root>/cron/jobs.json`, `<root>/prime-kernel/`, goals, harness and autonomous state | Prime families, config-gated and off by default | read-only; mount a writable volume before enabling a family |

## Findings

`check` reports findings with stable ids. Errors make the CLI exit 1; warnings do not.

| Id | Severity | Meaning |
| --- | --- | --- |
| `run-as-root` | error | the workload runs as root or declares no non-root user |
| `privileged` | error | the workload runs privileged |
| `host-network` | error | the workload shares the host network namespace |
| `host-pid` | error | the workload shares the host PID namespace |
| `missing-healthcheck` | error | no Dockerfile `HEALTHCHECK` or compose `healthcheck` |
| `missing-probe` | error | a Kubernetes container lacks a liveness or readiness probe |
| `latest-tag` | error | an image reference is untagged or uses `latest` |
| `inline-secret` | error | a credential is written into the artifact (token-looking value, `*_TOKEN`/`*_KEY`/`PASSWORD` set to a literal, `--token VALUE`, a Secret object with data) |
| `privilege-escalation` | error | `allowPrivilegeEscalation: true` |
| `missing-no-new-privileges` | error | `no-new-privileges` (compose), `NoNewPrivileges=yes` (systemd) or `allowPrivilegeEscalation: false` (Kubernetes) is missing |
| `unparseable` | error | the file could not be read, so it could not be verified |
| `writable-rootfs` | warning | the root filesystem is not read-only (`read_only`, `readOnlyRootFilesystem`, `ProtectSystem`) |
| `missing-resource-limits` | warning | no memory limit is set |
| `missing-network-policy` | warning | a Kubernetes workload is present without any NetworkPolicy in the scanned files |
| `unrecognized-file` | warning | a file named explicitly is not a Dockerfile, compose, Kubernetes or unit file |
| `promote-without-staging-evidence` | warning | a `promotion*` marker is present without a staging receipt (`*staging*`) or image digest (`*.digest`) file |
| `missing-promotion-approval-record` | warning | a `promotion*` marker is present without an approval (`*approv*`) or audit (`*audit*`) record file |
`check` reads YAML with a built-in block-YAML reader (no PyYAML needed). Anchors, aliases, tags, merge keys and
multi-line flow collections are not supported and are reported as `unparseable`.

## Staging first, then gated promotion

Promote the same digest through staging before production. There are no `--staging` or `--prod` flags: `check`
infers a production promotion from a `promotion*` marker file placed alongside the artifact set, and both
promotion findings below are warnings, so they never change the exit code (exit 0 is preserved).

1. `render` the artifact set once, then run `render`+`check`+`verify` against a staging host first. Keep the
   staging receipt (any `*staging*` file) or the image digest file (any `*.digest` file) alongside the artifact
   set; without either, `check` warns `promote-without-staging-evidence`.
2. Record the approval in the audit log and keep the approval or audit record (any `*approv*` or `*audit*`
   file) alongside the artifact set; without it, `check` warns `missing-promotion-approval-record`.
3. Promote the same digest: apply the identical artifact set to production with the `promotion*` marker
   present. Never re-render with different options between staging and production.

## Stop and drain

On SIGTERM the host stops accepting new calls, drains in-flight tool calls for up to `--shutdown-grace` seconds
(20 by default) and exits 0. `/readyz` returns 503 while draining. Platform stop timeouts must be longer: 30 s for
`docker stop`, compose (`stop_grace_period`) and systemd (`TimeoutStopSec`). With nothing in flight the host exits
within a fraction of a second of SIGTERM, so Kubernetes runs a 5 s `preStop` sleep first, which gives the load balancer
time to see `/readyz` go 503 and stop routing; `terminationGracePeriodSeconds: 45` covers that sleep, the 20 s drain and
a margin.

## Image CI

`.github/workflows/grokbot-image.yml` builds the committed `Dockerfile`, starts it with the production hardening flags
(`--read-only`, tmpfs state, `--cap-drop ALL`, `no-new-privileges`, a generated throwaway token file), waits for the
`healthy` status, runs `python -m omega_prime.grokbot.verify` inside the container, requires `docker stop -t 30` to exit
0, then writes an SPDX SBOM and scans the image with Trivy (critical, fixed vulnerabilities fail the job). It never
pushes an image and uses no secrets beyond the default token. The workflow also runs weekly to catch new
vulnerabilities in the pinned base image and lock file.

## What was verified

Verified when this kit was written: the four targets render deterministically and `check` reports nothing on them; the
image builds from `requirements-lock.txt`, starts with the exact flags above, reports `healthy`, serves `/healthz` and
`/readyz`, rejects an unauthenticated `/sse`, runs as uid 10001 and exits 0 on `docker stop`; `docker build --check`
reports no warnings; `docker compose config` accepts the compose file; `systemd-analyze verify` reports only the
missing `ExecStart` binary on a machine without the install layout; `actionlint` accepts the workflow. The Kubernetes
manifest was parsed and checked but not applied to a live cluster, and the systemd unit was not started.
