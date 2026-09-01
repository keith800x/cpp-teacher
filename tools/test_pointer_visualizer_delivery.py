#!/usr/bin/env python3

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

server = (
    PROJECT_ROOT / "dev_server.py"
).read_text(encoding="utf-8")

script = (
    PROJECT_ROOT /
    "visualizer" /
    "pointer_visualizer.js"
).read_text(encoding="utf-8")

index = (
    PROJECT_ROOT /
    "visualizer" /
    "index.html"
).read_text(encoding="utf-8")

for required in [
    "def latest_solution_timeline(",
    "/reference-visualization",
    'parts[1] == "solution"',
    'parts[2] == "visualization"',
    "no-store, no-cache",
    '"/visualizer/"',
]:
    assert required in server, required

assert "/output/" not in script

for required in [
    "/api/authoring/candidates/",
    "/reference-visualization",
    "/api/exercises/",
    "/solution/visualization",
    "/attempts/latest/visualization",
]:
    assert required in script, required

assert (
    "pointer_visualizer.js?v=30.7.1"
    in index
)

print(
    "Step 30.6.1 pointer visualizer delivery regression: PASS"
)
