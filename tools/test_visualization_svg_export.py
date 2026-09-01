#!/usr/bin/env python3

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

index = (
    PROJECT_ROOT /
    "visualizer" /
    "index.html"
).read_text(
    encoding="utf-8"
)

script = (
    PROJECT_ROOT /
    "visualizer" /
    "visualization_export.js"
).read_text(
    encoding="utf-8"
)

for required in [
    "Snapshot SVG",
    "visualization_export.js?v=30.8.2",
]:
    assert required in index, required

for required in [
    "async function captureElementSvg(",
    "image/svg+xml;charset=utf-8",
    "downloadCurrentSnapshotSvg",
    "snapshots/snapshot-",
    ".svg",
    "timeline.json",
    "createStoredZip",
]:
    assert required in script, required

for forbidden in [
    "toBlob(",
    'createElement("canvas")',
    'getContext("2d")',
    "drawImage(",
    "captureElementPng",
    "image/png",
]:
    assert forbidden not in script, forbidden

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
    "Step 30.8.2 reliable SVG visualization-export regression: PASS"
)
