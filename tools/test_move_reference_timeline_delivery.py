#!/usr/bin/env python3

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

server_path = ROOT / "dev_server.py"
server = server_path.read_text(
    encoding="utf-8"
)

for required in [
    "CANDIDATE_REFERENCE_TIMELINE_DIRECTORY",
    "def archive_candidate_reference_timeline(",
    "def read_candidate_reference_timeline(",
    "def validation_visualization_snapshot_count(",
    "clear_candidate_reference_timeline(",
    '"runtime.reference_visualization"',
    "archive_candidate_reference_timeline(",
    "Validation/reference timeline delivery mismatch:",
]:
    assert required in server, required

stable_read = (
    "timeline = read_candidate_reference_timeline("
)

stable_index = server.index(
    stable_read
)

endpoint_window = server[
    max(
        0,
        stable_index - 2200,
    ):
    stable_index + 1600
]

assert (
    "/reference-visualization"
    in endpoint_window
)

assert (
    "read_generated_timeline("
    not in endpoint_window
)

# Extract helper functions only.
tree = ast.parse(
    server,
    filename=str(server_path),
)

wanted = {
    "candidate_reference_timeline_path",
    "clear_candidate_reference_timeline",
    "archive_candidate_reference_timeline",
    "timeline_snapshot_count",
    "validation_visualization_snapshot_count",
    "read_candidate_reference_timeline",
}

selected = [
    node
    for node in tree.body
    if (
        isinstance(node, ast.FunctionDef) and
        node.name in wanted
    )
]

assert {
    node.name
    for node in selected
} == wanted

module = ast.Module(
    body=selected,
    type_ignores=[],
)

ast.fix_missing_locations(
    module
)

with tempfile.TemporaryDirectory(
    prefix="cpp_teacher_move_reference_delivery_"
) as temp_dir:
    temp = Path(temp_dir)

    archive_dir = (
        temp /
        "reference"
    )

    candidate_dir = (
        temp /
        "candidates"
    )

    candidate_dir.mkdir(
        parents=True
    )

    candidate_id = (
        "ai_move_delivery_probe"
    )

    candidate_path = (
        candidate_dir /
        f"{candidate_id}.json"
    )

    validation_path = (
        candidate_dir /
        f"{candidate_id}.validation.json"
    )

    candidate_path.write_text(
        "{}\n",
        encoding="utf-8",
    )

    validation_path.write_text(
        "{}\n",
        encoding="utf-8",
    )

    namespace = {
        "Path": Path,
        "json": json,
        "re": __import__("re"),
        "CANDIDATE_REFERENCE_TIMELINE_DIRECTORY":
            archive_dir,
        "authoring_candidate_paths":
            lambda candidate_id: (
                candidate_path,
                validation_path,
            ),
    }

    exec(
        compile(
            module,
            str(server_path),
            "exec",
        ),
        namespace,
    )

    raw14 = {
        "exercise_id": candidate_id,
        "schema_version": 4,
        "timeline": [
            {
                "step": index,
                "cause": {
                    "type":
                        "CREATE_VALUE",
                    "subject":
                        f"value{index}",
                    "detail": "",
                },
            }
            for index in range(
                1,
                15,
            )
        ],
    }

    report = {
        "valid": True,
        "checks": [
            {
                "id":
                    "runtime.reference_visualization",
                "message":
                    "Visualization contains 14 snapshots.",
            },
        ],
    }

    assert namespace[
        "timeline_snapshot_count"
    ](
        raw14
    ) == 14

    assert namespace[
        "validation_visualization_snapshot_count"
    ](
        report,
        "runtime.reference_visualization",
    ) == 14

    time.sleep(
        0.02
    )

    archive_path = namespace[
        "archive_candidate_reference_timeline"
    ](
        candidate_id,
        raw14,
    )

    delivered = namespace[
        "read_candidate_reference_timeline"
    ](
        candidate_id
    )

    assert namespace[
        "timeline_snapshot_count"
    ](
        delivered
    ) == 14

    # A later mutable shared-output overwrite cannot change this archive.
    shared_output = (
        temp /
        f"{candidate_id}_memory_timeline.json"
    )

    shared_output.write_text(
        json.dumps(
            {
                "timeline": [
                    {
                        "step": index
                    }
                    for index in range(
                        1,
                        12,
                    )
                ],
            }
        ),
        encoding="utf-8",
    )

    delivered_again = namespace[
        "read_candidate_reference_timeline"
    ](
        candidate_id
    )

    assert namespace[
        "timeline_snapshot_count"
    ](
        delivered_again
    ) == 14

    # A candidate edit invalidates the old reference until revalidation.
    newer = (
        archive_path.stat().st_mtime
        + 2.0
    )

    os.utime(
        candidate_path,
        (
            newer,
            newer,
        ),
    )

    assert namespace[
        "read_candidate_reference_timeline"
    ](
        candidate_id
    ) is None

move_js = (
    ROOT /
    "visualizer/move_visualizer.js"
).read_text(
    encoding="utf-8"
)

export_js = (
    ROOT /
    "visualizer/visualization_export.js"
).read_text(
    encoding="utf-8"
)

index = (
    ROOT /
    "visualizer/index.html"
).read_text(
    encoding="utf-8"
)

assert (
    '${exerciseId}:${mode}:${displayedTotal}'
    in move_js
)

for required in [
    "function timelineStepCount(",
    "deliveredTotal !== total",
    "Visualization timeline changed while this view",
    "Reopen Reference Solution before exporting.",
]:
    assert required in export_js, required

assert (
    "move_visualizer.js?v=30.8.2"
    in index
)

assert (
    "visualization_export.js?v=30.8.2"
    in index
)

node = shutil.which(
    "node"
)

if node:
    for path in [
        ROOT /
        "visualizer/move_visualizer.js",
        ROOT /
        "visualizer/visualization_export.js",
    ]:
        result = subprocess.run(
            [
                node,
                "--check",
                str(path),
            ],
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, (
            result.stderr
        )

print(
    "Step 30.8.2 Move reference-timeline delivery regression: PASS"
)
