#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

path = (
    PROJECT_ROOT /
    "config" /
    "project_version.json"
)

if not path.exists():
    print(
        "C++ Teacher version tracking is not initialized."
    )
    raise SystemExit(1)

data = json.loads(
    path.read_text(
        encoding="utf-8"
    )
)

print(
    "Version:",
    data.get(
        "version",
        "unknown"
    )
)

print(
    "Last patch:",
    data.get(
        "last_patch",
        "unknown"
    )
)

print(
    "Installed:",
    data.get(
        "installed_at",
        "unknown"
    )
)
