"""Suite-wide setup. PyRIT creates its data dir at import; keep it in tmp.

`pyrit.common.path` mkdirs `user_data_dir("dbdata")` and touches logs.txt on
first import, which breaks read-only sandboxes when it resolves under HOME.
`XDG_DATA_HOME` redirects appdirs on Linux (CI, containers). This must run
before any `pyrit` import, so it lives in conftest and not in a test module.
"""

from __future__ import annotations

import os
import tempfile


def _isolate_pyrit() -> None:
    root = os.environ.setdefault(
        "XDG_DATA_HOME", os.path.join(tempfile.gettempdir(), "omega-prime-pyrit")
    )
    os.makedirs(root, exist_ok=True)


_isolate_pyrit()
