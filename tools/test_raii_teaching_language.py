#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
index = (ROOT / "visualizer/index.html").read_text(encoding="utf-8")
script = (ROOT / "visualizer/raii_visualizer.js").read_text(encoding="utf-8")

assert 'raii_visualizer.js?v=30.7.6' in index

for required in [
    '"Function lifetime begins"',
    '"Automatic object created"',
    '"Resource acquired"',
    '"Managed-resource relationship"',
    '"Destructor begins"',
    '"Managed resource released"',
    '"Object lifetime ends"',
    '"RESOURCE_ACQUIRED"',
    '"MANAGES_RESOURCE"',
    '"RESOURCE_RELEASED"',
    '"DESTRUCTOR_BEGINS"',
    '"OBJECT_DESTROYED"',
    'deterministic cleanup',
    'lexical lifetime has ended',
    'not teaching a literal learner-visible raw-pointer field',
]:
    assert required in script, required

for forbidden in [
    '"Heap allocation"',
    '"Pointer binding"',
    '"Resource lifetime ends"',
    'temporarily dangling during destructor execution',
    'non-const reference',
]:
    assert forbidden not in script, forbidden

# The RAII layer should rewrite the event card as well as the teaching panel,
# so internal BIND_POINTER encoding is not presented as the learner concept.
for required in [
    'setElementText("eventType", "MANAGES_RESOURCE")',
    'setElementText("eventSubject", manager)',
    '`manages ${detail}`',
]:
    assert required in script, required

node = shutil.which("node")
if node:
    result = subprocess.run(
        [
            node,
            "--check",
            str(ROOT / "visualizer/raii_visualizer.js"),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

print("Step 30.7.2 RAII teaching-language regression: PASS")
