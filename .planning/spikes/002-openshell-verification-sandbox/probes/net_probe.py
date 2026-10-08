"""Outbound-network probe run INSIDE the sandbox. Prints one JSON object.

Exit 0 when every outbound attempt failed (deny holds), 3 when any succeeded.
Records only the names of proxy env vars, never their values.
"""

import json
import os
import shutil
import socket
import subprocess
import urllib.request

TIMEOUT = 6
results = {}


def attempt(name, fn):
    try:
        detail = fn()
        results[name] = {"connected": True, "detail": str(detail)[:300]}
    except Exception as exc:  # noqa: BLE001 - every failure is evidence
        results[name] = {"connected": False, "error": f"{type(exc).__name__}: {exc}"[:300]}


def urllib_env_proxy():
    with urllib.request.urlopen("https://example.com/", timeout=TIMEOUT) as resp:
        return resp.status


def urllib_no_proxy():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open("https://example.com/", timeout=TIMEOUT) as resp:
        return resp.status


def http_plain():
    with urllib.request.urlopen("http://example.com/", timeout=TIMEOUT) as resp:
        return resp.status


def raw_tcp_ip():
    with socket.create_connection(("1.1.1.1", 443), timeout=TIMEOUT):
        return "tcp connect 1.1.1.1:443"


def raw_tcp_pypi():
    with socket.create_connection(("pypi.org", 443), timeout=TIMEOUT):
        return "tcp connect pypi.org:443"


def curl():
    exe = shutil.which("curl")
    if not exe:
        raise FileNotFoundError("curl not in image")
    proc = subprocess.run(
        [exe, "-sS", "-o", "/dev/null", "-w", "%{http_code}", "-m", str(TIMEOUT), "https://example.com/"],
        capture_output=True,
        text=True,
        timeout=TIMEOUT + 4,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"curl rc={proc.returncode} stderr={proc.stderr.strip()}")
    return f"http_code={proc.stdout.strip()}"


attempt("urllib_https_env_proxy", urllib_env_proxy)
attempt("urllib_https_direct_no_proxy", urllib_no_proxy)
attempt("urllib_http_plain", http_plain)
attempt("tcp_1.1.1.1_443", raw_tcp_ip)
attempt("tcp_pypi.org_443", raw_tcp_pypi)
attempt("curl_https", curl)

try:
    dns = sorted({ai[4][0] for ai in socket.getaddrinfo("example.com", 443)})
    dns_result = {"resolved": True, "addresses": dns[:4]}
except Exception as exc:  # noqa: BLE001
    dns_result = {"resolved": False, "error": f"{type(exc).__name__}: {exc}"[:300]}

proxy_vars = sorted(k for k in os.environ if k.lower() in {"http_proxy", "https_proxy", "all_proxy", "no_proxy"})
all_denied = not any(r["connected"] for r in results.values())
print(json.dumps({"all_denied": all_denied, "attempts": results, "dns": dns_result, "proxy_env_var_names": proxy_vars}))
raise SystemExit(0 if all_denied else 3)
