"""Discord import failures produce a controlled factory error."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

OMES = Path(__file__).resolve().parents[1]
ROOT = OMES.parent


def test_discord_module_imports_without_the_library() -> None:
    code = "\n".join(
        [
            "import sys",
            "sys.modules['discord'] = None",
            "import omes.tools.discord as d",
            "try:",
            "    d._default_client()",
            "except d.DiscordError:",
            "    pass",
            "else:",
            "    raise SystemExit('factory did not fail soft')",
        ]
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
