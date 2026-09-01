#!/usr/bin/env python3
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
index = (ROOT / "visualizer/index.html").read_text(encoding="utf-8")
pointer = (ROOT / "visualizer/pointer_visualizer.js").read_text(encoding="utf-8")
raii = (ROOT / "visualizer/raii_visualizer.js").read_text(encoding="utf-8")
styles = (ROOT / "visualizer/styles.css").read_text(encoding="utf-8")
server = (ROOT / "dev_server.py").read_text(encoding="utf-8")

for required in [
    'pointer_visualizer.js?v=30.7.1',
    'raii_visualizer.js?v=30.7.6',
]:
    assert required in index, required

for required in [
    'function isPointersExercise()',
    'text("exerciseTopicBadge")',
    'isPointersExercise() &&',
]:
    assert required in pointer, required

for required in [
    'function isRaiiExercise()',
    'label.textContent = "manages"',
    'Conceptual managed-resource relationship',
    'automatic object — no managed heap resource is visualized',
    'hidePointerArrowLayer()',
    '`${field.points_to} (released)`',
]:
    assert required in raii, required

for required in [
    '.raii-managed-row',
    '.raii-managed-value',
    '.raii-object-note',
]:
    assert required in styles, required

for required in [
    'def exercise_topic_for_visualization(',
    'def raii_internal_lifecycle_scope(',
    'def visualization_timeline_for_client(',
    '"processVideoFrame"',
    'raii_internal_lifecycle_scope(',
]:
    assert required in server, required

# Step 30.7.5 generalizes the previous processVideoFrame-only filter to also
# remove constructor/destructor lifecycle wrappers. Verify the generalized
# implementation rather than one old exact source spelling.
assert 'cause_subject == "processVideoFrame"' in server
assert 'scope != "processVideoFrame"' in server

# Candidate, published solution, and latest attempt endpoints all sanitize.
assert server.count('visualization_timeline_for_client(') >= 4

node = shutil.which("node")
if node:
    for script in [
        ROOT / "visualizer/pointer_visualizer.js",
        ROOT / "visualizer/raii_visualizer.js",
    ]:
        result = subprocess.run(
            [node, "--check", str(script)],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

print("Step 30.7.5 RAII visualization-truthfulness regression: PASS")
