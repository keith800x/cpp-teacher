#!/usr/bin/env python3

from __future__ import annotations

import ast
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

server_path = (
    ROOT /
    "dev_server.py"
)

server = server_path.read_text(
    encoding="utf-8"
)

raii = (
    ROOT /
    "visualizer/raii_visualizer.js"
).read_text(
    encoding="utf-8"
)

index = (
    ROOT /
    "visualizer/index.html"
).read_text(
    encoding="utf-8"
)

# Ensure the Python source contains exactly the intended RAII client helper.
tree = ast.parse(
    server,
    filename=str(server_path),
)

functions = {
    node.name: node
    for node in tree.body
    if isinstance(
        node,
        (
            ast.FunctionDef,
            ast.AsyncFunctionDef,
        ),
    )
}

assert "raii_object_for_client" in functions
assert "visualization_timeline_for_client" in functions

# Do not assert a particular source-code line wrapping. Inspect the
# raii_object_for_client() AST and then rely on the dedicated sanitizer
# behavior regression for semantics.
raii_object_node = functions[
    "raii_object_for_client"
]

raii_object_source = ast.get_source_segment(
    server,
    raii_object_node,
)

assert isinstance(
    raii_object_source,
    str,
)

for required in [
    '"kind"',
    '"pointer"',
    '"points_to"',
]:
    assert required in raii_object_source, required

# The helper must contain an `is None` comparison, but its formatting is free.
assert any(
    isinstance(node, ast.Compare)
    and any(
        isinstance(op, ast.Is)
        for op in node.ops
    )
    and any(
        isinstance(comparator, ast.Constant)
        and comparator.value is None
        for comparator in node.comparators
    )
    for node in ast.walk(
        raii_object_node
    )
)

assert "raii_object_for_client(" in server

# Browser should remove stale rows entirely, not merely hide the source row.
for required in [
    "if (entries.length === 0)",
    "fields.replaceChildren();",
    "automatic object — no managed heap resource is visualized",
]:
    assert required in raii, required

assert (
    "raii_visualizer.js?v=30.7.6"
    in index
)

node = shutil.which(
    "node"
)

if node:
    result = subprocess.run(
        [
            node,
            "--check",
            str(
                ROOT /
                "visualizer/raii_visualizer.js"
            ),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert (
        result.returncode == 0
    ), result.stderr

print(
    "Step 30.7.5 RAII object-field truthfulness regression: PASS"
)
