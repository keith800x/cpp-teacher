#!/usr/bin/env python3

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

index = (
    PROJECT_ROOT /
    "visualizer" /
    "index.html"
).read_text(encoding="utf-8")

styles = (
    PROJECT_ROOT /
    "visualizer" /
    "styles.css"
).read_text(encoding="utf-8")

script = (
    PROJECT_ROOT /
    "visualizer" /
    "visualization_export.js"
).read_text(encoding="utf-8")

for required in [
    'id="downloadVisualizationDataButton"',
    'id="downloadVisualizationSnapshotButton"',
    'id="downloadVisualizationAllButton"',
    'visualization_export.js?v=30.8.2',
]:
    assert required in index, required

for required in [
    ".visualization-export-actions",
    ".visualization-toolbar-right",
]:
    assert required in styles, required

for required in [
    "async function fetchTimeline()",
    "async function captureElementSvg(",
    "async function createStoredZip(",
    "async function downloadTimelineData()",
    "async function downloadCurrentSnapshotSvg()",
    "async function downloadAllSnapshots()",
    "/api/authoring/candidates/",
    "/reference-visualization",
    "/solution/visualization",
    "/attempts/latest/visualization",
    "timeline.json",
    "snapshots/snapshot-",
    "image/svg+xml",
    "application/zip",
]:
    assert required in script, required

assert "/output/" not in script
assert "const originalStep =" in script
assert "createStoredZip" in script

# Step 30.6.6 must never reintroduce the browser canvas path that
# caused "Tainted canvases may not be exported".
for forbidden in [
    "toBlob(",
    'createElement("canvas")',
    'getContext("2d")',
    "drawImage(",
    "captureElementPng",
    "image/png",
]:
    assert forbidden not in script, forbidden

for required in [
    "image/svg+xml",
    ".svg",
    "captureElementSvg",
]:
    assert required in script, required

node = shutil.which("node")
if node:
    result = subprocess.run(
        [
            node,
            "--check",
            str(
                PROJECT_ROOT /
                "visualizer" /
                "visualization_export.js"
            ),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

print(
    "Step 30.6.4 visualization-export regression test: PASS"
)
