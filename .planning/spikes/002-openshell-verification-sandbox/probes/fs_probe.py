"""Filesystem-policy probe run INSIDE the sandbox. Prints one JSON object.

Exit 0 when every expectation holds, 4 otherwise. The key control is
/opt/omega-dac-writable: the image makes it mode 0777, so only Landlock can
deny the write there.
"""

import json
import os

WRITES = [
    # (path, expected_allowed, why)
    ("/sandbox/omega-probe.txt", True, "workdir, read_write"),
    ("/tmp/omega-probe.txt", True, "read_write"),
    ("/opt/omega-dac-writable/omega-probe.txt", False, "0777 dir not in policy: Landlock-only denial"),
    ("/home/app/omega-probe.txt", False, "user-owned home not in policy: Landlock-only denial"),
    ("/etc/omega-probe.txt", False, "read_only (also root-owned)"),
    ("/usr/local/lib/omega-probe.txt", False, "read_only (also root-owned)"),
    ("/var/tmp/omega-probe.txt", False, "not in policy (1777 sticky dir, DAC allows)"),
]

READS = [
    ("/etc/hostname", True, "read_only"),
    ("/usr/local/bin/python3", True, "read_only"),
    ("/home/app/.bashrc", False, "not in policy"),
    ("/opt/omega-dac-writable", False, "not in policy (listdir)"),
]


def try_write(path):
    try:
        with open(path, "w") as fh:
            fh.write("omega spike 002\n")
        os.remove(path)
        return {"allowed": True}
    except OSError as exc:
        return {"allowed": False, "errno": exc.errno, "error": f"{type(exc).__name__}: {exc.strerror}"}


def try_read(path):
    try:
        if os.path.isdir(path):
            os.listdir(path)
        else:
            with open(path, "rb") as fh:
                fh.read(16)
        return {"allowed": True}
    except OSError as exc:
        return {"allowed": False, "errno": exc.errno, "error": f"{type(exc).__name__}: {exc.strerror}"}


out = {"uid": os.getuid(), "gid": os.getgid(), "writes": {}, "reads": {}}
ok = True
for path, expected, why in WRITES:
    res = try_write(path)
    res.update(expected_allowed=expected, why=why, matches=res["allowed"] == expected)
    ok &= res["matches"]
    out["writes"][path] = res
for path, expected, why in READS:
    res = try_read(path)
    res.update(expected_allowed=expected, why=why, matches=res["allowed"] == expected)
    ok &= res["matches"]
    out["reads"][path] = res
out["all_expectations_hold"] = ok
print(json.dumps(out))
raise SystemExit(0 if ok else 4)
