#!/usr/bin/env python3

from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

candidate = json.loads(
    (
        ROOT /
        "candidates/generated" /
        "ai_move_semantics_20260828_101133_286f4d.json"
    ).read_text(
        encoding="utf-8"
    )
)

exercise = candidate["exercise"]
files = candidate["files"]
hidden = files[
    exercise["hidden_test_file"]
]
support = files[
    exercise["support_file"]
]

# Learner-facing exercise remains unchanged.
assert ": load_(other.load_)" in exercise["starter_code"]
assert ": load_(std::move(other.load_))" in exercise["reference_solution"]

# Native parser vocabulary remains stable: model move state through supported
# CREATE_VALUE / WRITE_VALUE events.
for required in [
    "TRACE|CREATE_VALUE|loadingKit.load_|",
    "TRACE|CREATE_VALUE|stationKit.load_|",
    "|moved_from=loadingKit.load_",
    "TRACE|WRITE_VALUE|loadingKit.load_|",
    "|moved_to=stationKit.load_",
    "|copied_from=loadingKit.load_",
    "|retained_after=stationKit.load_",
    "type=FieldKit&&",
]:
    assert required in hidden, required

for forbidden in [
    "TRACE|INITIALIZE_VALUE",
    "TRACE|MOVE_VALUE",
    "TRACE|COPY_VALUE",
    "TRACE|TRANSFER_VALUE",
    "TRACE|CLEAR_VALUE",
]:
    assert forbidden not in support, forbidden

# -------------------------------------------------------------------------
# Execute only client-sanitizer functions from dev_server.py.
# -------------------------------------------------------------------------

server_path = ROOT / "dev_server.py"
server_source = server_path.read_text(
    encoding="utf-8"
)

tree = ast.parse(
    server_source,
    filename=str(server_path),
)

wanted = {
    "visualization_detail_value",
    "move_semantics_cause_for_client",
    "move_semantics_object_for_client",
    "move_semantics_timeline_for_client",
    "visualization_timeline_for_client",
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

namespace = {
    "exercise_topic_for_visualization":
        lambda exercise_id: "move_semantics",
}

exec(
    compile(
        module,
        str(server_path),
        "exec",
    ),
    namespace,
)

raw = {
    "exercise_id": "move-probe",
    "schema_version": 4,
    "timeline": [
        {
            "step": 1,
            "active_scopes": [
                "supply-handoff",
            ],
            "cause": {
                "type": "CREATE_OBJECT",
                "subject": "loadingKit",
                "detail": "type=FieldKit",
            },
            "stack": [
                {
                    "name": "loadingKit",
                    "type": "FieldKit",
                    "scope": "supply-handoff",
                    "alive": True,
                    "fields": {
                        "data_": {
                            "kind": "pointer",
                            "points_to": None,
                        },
                    },
                },
            ],
            "stack_values": [],
            "aliases": [],
            "heap": [],
        },
        {
            "step": 2,
            "active_scopes": [
                "supply-handoff",
            ],
            "cause": {
                "type": "CREATE_VALUE",
                "subject": "loadingKit.load_",
                "detail": "type=int|value=24|role=move_source",
            },
            "stack": [
                {
                    "name": "loadingKit",
                    "type": "FieldKit",
                    "scope": "supply-handoff",
                    "alive": True,
                    "fields": {
                        "data_": {
                            "kind": "pointer",
                            "points_to": None,
                        },
                    },
                },
            ],
            "stack_values": [
                {
                    "name": "loadingKit.load_",
                    "type": "int",
                    "value": "24",
                    "scope": "supply-handoff",
                    "alive": True,
                },
            ],
            "aliases": [],
            "heap": [],
        },
        {
            "step": 3,
            "active_scopes": [
                "supply-handoff",
                "FieldKit",
            ],
            "cause": {
                "type": "BIND_ALIAS",
                "subject": "other",
                "detail": "target=loadingKit|type=FieldKit&&|const=false",
            },
            "stack": [
                {
                    "name": "loadingKit",
                    "type": "FieldKit",
                    "scope": "supply-handoff",
                    "alive": True,
                    "fields": {
                        "data_": {
                            "kind": "pointer",
                            "points_to": None,
                        },
                    },
                },
            ],
            "stack_values": [
                {
                    "name": "loadingKit.load_",
                    "type": "int",
                    "value": "24",
                    "scope": "supply-handoff",
                    "alive": True,
                },
            ],
            "aliases": [
                {
                    "name": "other",
                    "target": "loadingKit",
                    "type": "FieldKit&&",
                    "scope": "FieldKit",
                    "alive": True,
                    "const": False,
                },
            ],
            "heap": [],
        },
        {
            "step": 4,
            "active_scopes": [
                "supply-handoff",
                "FieldKit",
            ],
            "cause": {
                "type": "CREATE_VALUE",
                "subject": "stationKit.load_",
                "detail": "type=int|value=24|moved_from=loadingKit.load_",
            },
            "stack": [
                {
                    "name": "loadingKit",
                    "type": "FieldKit",
                    "scope": "supply-handoff",
                    "alive": True,
                    "fields": {
                        "data_": {
                            "kind": "pointer",
                            "points_to": None,
                        },
                    },
                },
                {
                    "name": "stationKit",
                    "type": "FieldKit",
                    "scope": "FieldKit",
                    "alive": True,
                    "fields": {
                        "data_": {
                            "kind": "pointer",
                            "points_to": None,
                        },
                    },
                },
            ],
            "stack_values": [
                {
                    "name": "loadingKit.load_",
                    "type": "int",
                    "value": "24",
                    "scope": "supply-handoff",
                    "alive": True,
                },
                {
                    "name": "stationKit.load_",
                    "type": "int",
                    "value": "24",
                    "scope": "FieldKit",
                    "alive": True,
                },
            ],
            "aliases": [
                {
                    "name": "other",
                    "target": "loadingKit",
                    "type": "FieldKit&&",
                    "scope": "FieldKit",
                    "alive": True,
                    "const": False,
                },
            ],
            "heap": [],
        },
        {
            "step": 5,
            "active_scopes": [
                "supply-handoff",
                "FieldKit",
            ],
            "cause": {
                "type": "WRITE_VALUE",
                "subject": "loadingKit.load_",
                "detail": "value=0|moved_to=stationKit.load_",
            },
            "stack": [
                {
                    "name": "loadingKit",
                    "type": "FieldKit",
                    "scope": "supply-handoff",
                    "alive": True,
                    "fields": {
                        "data_": {
                            "kind": "pointer",
                            "points_to": None,
                        },
                    },
                },
                {
                    "name": "stationKit",
                    "type": "FieldKit",
                    "scope": "FieldKit",
                    "alive": True,
                    "fields": {
                        "data_": {
                            "kind": "pointer",
                            "points_to": None,
                        },
                    },
                },
            ],
            "stack_values": [
                {
                    "name": "loadingKit.load_",
                    "type": "int",
                    "value": "0",
                    "scope": "supply-handoff",
                    "alive": True,
                },
                {
                    "name": "stationKit.load_",
                    "type": "int",
                    "value": "24",
                    "scope": "FieldKit",
                    "alive": True,
                },
            ],
            "aliases": [
                {
                    "name": "other",
                    "target": "loadingKit",
                    "type": "FieldKit&&",
                    "scope": "FieldKit",
                    "alive": True,
                    "const": False,
                },
            ],
            "heap": [],
        },
        {
            "step": 6,
            "active_scopes": [
                "supply-handoff",
            ],
            "cause": {
                "type": "EXIT_SCOPE",
                "subject": "FieldKit",
                "detail": "medical station received kit",
            },
            "stack": [],
            "stack_values": [],
            "aliases": [
                {
                    "name": "other",
                    "target": "loadingKit",
                    "type": "FieldKit&&",
                    "scope": "FieldKit",
                    "alive": False,
                    "const": False,
                },
            ],
            "heap": [],
        },
    ],
}

cleaned = namespace[
    "visualization_timeline_for_client"
](
    "move-probe",
    raw,
)

assert cleaned["move_semantics_model"] == "member_state_transfer"

frames = cleaned["timeline"]

assert frames[0]["stack"][0]["fields"] == {}
assert frames[1]["cause"]["type"] == "INITIALIZE_VALUE"
assert frames[3]["cause"]["type"] == "TRANSFER_VALUE"
assert frames[4]["cause"]["type"] == "CLEAR_VALUE"
assert frames[4]["stack_values"][0]["value"] == "0"
assert frames[4]["stack_values"][1]["value"] == "24"
assert frames[5]["aliases"] == []

# -------------------------------------------------------------------------
# Browser delivery.
# -------------------------------------------------------------------------

move_js = (
    ROOT /
    "visualizer/move_visualizer.js"
).read_text(
    encoding="utf-8"
)

index = (
    ROOT /
    "visualizer/index.html"
).read_text(
    encoding="utf-8"
)

for required in [
    "function isMoveExercise()",
    "Tracked member state",
    "rvalue-reference parameter",
    "std::move itself is only a cast",
    "Member state transferred",
    "Moved-from source becomes empty",
    "Source still has packages",
    ".alias-card.out-of-scope",
]:
    assert required in move_js, required

assert (
    "move_visualizer.js?v=30.8.2"
    in index
)

node = shutil.which("node")

if node:
    result = subprocess.run(
        [
            node,
            "--check",
            str(
                ROOT /
                "visualizer/move_visualizer.js"
            ),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, (
        result.stderr
    )

# -------------------------------------------------------------------------
# Behavioral candidate smoke test.
# -------------------------------------------------------------------------

compiler = (
    shutil.which("g++") or
    shutil.which("clang++")
)

if compiler:
    def compile_run(
        name: str,
        learner_code: str,
    ):
        with tempfile.TemporaryDirectory(
            prefix=f"cpp_teacher_{name}_"
        ) as temp_dir:
            temp = Path(temp_dir)
            source = temp / f"{name}.cpp"
            executable = temp / name

            source.write_text(
                support +
                "\n" +
                learner_code +
                "\n" +
                hidden,
                encoding="utf-8",
            )

            built = subprocess.run(
                [
                    compiler,
                    "-std=c++20",
                    str(source),
                    "-o",
                    str(executable),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            assert (
                built.returncode == 0
            ), built.stderr

            return subprocess.run(
                [
                    str(executable)
                ],
                text=True,
                capture_output=True,
                check=False,
            )

    reference = compile_run(
        "move_easy_reference",
        exercise[
            "reference_solution"
        ],
    )

    starter = compile_run(
        "move_easy_starter",
        exercise[
            "starter_code"
        ],
    )

    assert reference.returncode == 0, (
        reference.stderr
    )

    assert starter.returncode != 0, (
        "Broken Move Easy starter unexpectedly passed."
    )

    # Reference trace uses supported state vocabulary and records the transfer.
    assert (
        "TRACE|CREATE_VALUE|stationKit.load_|"
        in reference.stderr
    )

    assert (
        "|moved_from=loadingKit.load_"
        in reference.stderr
    )

    assert (
        "TRACE|WRITE_VALUE|loadingKit.load_|"
        in reference.stderr
    )

    assert (
        "|moved_to=stationKit.load_"
        in reference.stderr
    )

    # Broken starter visibly takes the copy-like teaching path.
    assert (
        "|copied_from=loadingKit.load_"
        in starter.stderr
    )

    assert (
        "|retained_after=stationKit.load_"
        in starter.stderr
    )

print(
    "Step 30.8.2 Move Semantics teaching-timeline regression: PASS"
)
