#!/usr/bin/env python3

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

script = (
    PROJECT_ROOT /
    "visualizer" /
    "pointer_visualizer.js"
).read_text(
    encoding="utf-8"
)

index = (
    PROJECT_ROOT /
    "visualizer" /
    "index.html"
).read_text(
    encoding="utf-8"
)

for required in [
    "function previousPointerTarget(",
    "Pointer reseated",
    "previously pointed to ${previousTarget} and now points to ${target}",
    "Both stack objects remain alive",
    "Pointer cleared",
    "clearing only removes this non-owning pointer relationship",
]:
    assert required in script, required

assert (
    "teachPointerFrame(\n"
    "                documentData,\n"
    "                index,"
    in script
)

assert re.search(
    r'pointer_visualizer\.js\?v=30\.7\.1',
    index
)

node = shutil.which("node")

if node:
    result = subprocess.run(
        [
            node,
            "--check",
            str(
                PROJECT_ROOT /
                "visualizer" /
                "pointer_visualizer.js"
            ),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

print(
    "Step 30.6.3 pointer reseating visualization regression: PASS"
)
