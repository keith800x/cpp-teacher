#!/usr/bin/env python3

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

script = (
    ROOT / "visualizer" / "pointer_visualizer.js"
).read_text(encoding="utf-8")

index = (
    ROOT / "visualizer" / "index.html"
).read_text(encoding="utf-8")

for required in [
    "function heapResourceIds(",
    "function pointerTargetKind(",
    '"Write through pointer"',
    '"Pointee lifetime ends"',
    "Both heap resources are still alive at this point",
    "The raw pointer is non-owning",
    "No tracked pointer still points to it",
    "still stores this target and is now dangling",
    "allocation and cleanup remain separate lifetime responsibilities",
]:
    assert required in script, required

assert re.search(
    r'pointer_visualizer\.js\?v=30\.7\.1',
    index
)

node = shutil.which("node")
if node:
    result = subprocess.run(
        [node, "--check", str(ROOT / "visualizer/pointer_visualizer.js")],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

print(
    "Step 30.7.1 pointer heap-teaching regression test: PASS"
)
