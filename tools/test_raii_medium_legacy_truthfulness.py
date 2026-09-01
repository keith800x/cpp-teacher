#!/usr/bin/env python3

from __future__ import annotations

import ast
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

candidate = json.loads(
    (
        ROOT /
        "candidates/generated" /
        "ai_raii_scope_20260814_125032_987d79.json"
    ).read_text(
        encoding="utf-8"
    )
)

exercise = candidate["exercise"]
hidden = candidate["files"][
    exercise["hidden_test_file"]
]

# Candidate no longer grades one exact audit vector through shipmentAuditMatches.
assert "shipmentAuditMatches(expected)" not in hidden
assert "TRACE|ENTER_SCOPE|completeShipment|" in hidden
assert "TRACE|EXIT_SCOPE|completeShipment|" in hidden
assert "reverse construction order" in hidden

server_path = ROOT / "dev_server.py"
server_source = server_path.read_text(
    encoding="utf-8"
)

for required in [
    "def raii_internal_lifecycle_scope(",
    "def raii_cause_for_client(",
    "not part.startswith(",
    '"pointer="',
    'field.get(',
    '"points_to"',
    "raii_internal_lifecycle_scope(",
]:
    assert required in server_source, required

# Execute only the sanitizer helpers, not the whole dev server.
tree = ast.parse(
    server_source,
    filename=str(server_path),
)

wanted = {
    "raii_internal_lifecycle_scope",
    "raii_cause_for_client",
    "raii_object_for_client",
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

ast.fix_missing_locations(module)

namespace = {
    "exercise_topic_for_visualization":
        lambda exercise_id: "raii_scope",
    "raii_learner_operation_for_visualization":
        lambda exercise_id: "completeShipment",
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
    "exercise_id": "medium-probe",
    "schema_version": 4,
    "timeline": [
        {
            "step": 1,
            "active_scopes": [
                "completeShipment",
            ],
            "cause": {
                "type": "ENTER_SCOPE",
                "subject": "completeShipment",
                "detail": "",
            },
            "stack": [],
            "heap": [],
        },
        {
            "step": 2,
            "active_scopes": [
                "completeShipment",
                "ShipmentAsset::ShipmentAsset",
            ],
            "cause": {
                "type": "ENTER_SCOPE",
                "subject": "ShipmentAsset::ShipmentAsset",
                "detail": "gelPack",
            },
            "stack": [],
            "heap": [],
        },
        {
            "step": 3,
            "active_scopes": [
                "completeShipment",
                "ShipmentAsset::ShipmentAsset",
            ],
            "cause": {
                "type": "CREATE_OBJECT",
                "subject": "gelPack",
                "detail": "type=ColdPack|pointer=payload_",
            },
            "stack": [
                {
                    "name": "gelPack",
                    "type": "ColdPack",
                    "scope": "ShipmentAsset::ShipmentAsset",
                    "alive": True,
                    "fields": {
                        "payload_": {
                            "kind": "pointer",
                            "points_to": None,
                        },
                    },
                },
            ],
            "heap": [],
        },
        {
            "step": 4,
            "active_scopes": [
                "completeShipment",
                "ShipmentAsset::ShipmentAsset",
            ],
            "cause": {
                "type": "ALLOCATE_RESOURCE",
                "subject": "resource#2",
                "detail": "value=256 bytes",
            },
            "stack": [
                {
                    "name": "gelPack",
                    "type": "ColdPack",
                    "scope": "ShipmentAsset::ShipmentAsset",
                    "alive": True,
                    "fields": {
                        "payload_": {
                            "kind": "pointer",
                            "points_to": None,
                        },
                    },
                },
            ],
            "heap": [
                {
                    "id": "resource#2",
                    "alive": True,
                },
            ],
        },
        {
            "step": 5,
            "active_scopes": [
                "completeShipment",
                "ShipmentAsset::ShipmentAsset",
            ],
            "cause": {
                "type": "BIND_POINTER",
                "subject": "gelPack.payload_",
                "detail": "resource#2",
            },
            "stack": [
                {
                    "name": "gelPack",
                    "type": "ColdPack",
                    "scope": "ShipmentAsset::ShipmentAsset",
                    "alive": True,
                    "fields": {
                        "payload_": {
                            "kind": "pointer",
                            "points_to": "resource#2",
                        },
                    },
                },
            ],
            "heap": [
                {
                    "id": "resource#2",
                    "alive": True,
                },
            ],
        },
        {
            "step": 6,
            "active_scopes": [
                "completeShipment",
            ],
            "cause": {
                "type": "EXIT_SCOPE",
                "subject": "ShipmentAsset::ShipmentAsset",
                "detail": "gelPack",
            },
            "stack": [
                {
                    "name": "gelPack",
                    "type": "ColdPack",
                    "scope": "ShipmentAsset::ShipmentAsset",
                    "alive": True,
                    "fields": {
                        "payload_": {
                            "kind": "pointer",
                            "points_to": "resource#2",
                        },
                    },
                },
            ],
            "heap": [
                {
                    "id": "resource#2",
                    "alive": True,
                },
            ],
        },
        {
            "step": 7,
            "active_scopes": [
                "completeShipment",
                "chillCargo",
            ],
            "cause": {
                "type": "ENTER_SCOPE",
                "subject": "chillCargo",
                "detail": "",
            },
            "stack": [
                {
                    "name": "gelPack",
                    "type": "ColdPack",
                    "scope": "ShipmentAsset::ShipmentAsset",
                    "alive": True,
                    "fields": {
                        "payload_": {
                            "kind": "pointer",
                            "points_to": "resource#2",
                        },
                    },
                },
            ],
            "heap": [
                {
                    "id": "resource#2",
                    "alive": True,
                },
            ],
        },
        {
            "step": 8,
            "active_scopes": [],
            "cause": {
                "type": "EXIT_SCOPE",
                "subject": "completeShipment",
                "detail": "",
            },
            "stack": [
                {
                    "name": "gelPack",
                    "type": "ColdPack",
                    "scope": "ShipmentAsset::ShipmentAsset",
                    "alive": False,
                    "fields": {},
                },
            ],
            "heap": [
                {
                    "id": "resource#2",
                    "alive": False,
                },
            ],
        },
    ],
}

cleaned = namespace[
    "visualization_timeline_for_client"
](
    "medium-probe",
    raw,
)

frames = cleaned["timeline"]

assert cleaned["raii_learner_operation"] == "completeShipment"

# Constructor ENTER/EXIT frames disappear; learner operation stays.
assert [
    frame["cause"]["subject"]
    for frame in frames
] == [
    "completeShipment",
    "gelPack",
    "resource#2",
    "gelPack.payload_",
    "chillCargo",
    "completeShipment",
]

create = frames[1]

assert create["cause"]["detail"] == "type=ColdPack"
assert create["active_scopes"] == [
    "completeShipment",
]

gel = create["stack"][0]

# The object is shown in its learner function, not in the base constructor.
assert gel["scope"] == "completeShipment"

# Constructor-internal unbound pointer state is removed.
assert gel["fields"] == {}

bound = frames[3]["stack"][0]

# Bound resource relationship remains available for "manages" teaching.
assert bound["fields"] == {
    "payload_": {
        "kind": "pointer",
        "points_to": "resource#2",
    },
}

assert all(
    "ShipmentAsset::ShipmentAsset"
    not in frame.get(
        "active_scopes",
        []
    )
    for frame in frames
)

raii_js = (
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

for required in [
    "function learnerOperationName(",
    "documentData?.raii_learner_operation",
    "`enclosing function: ${object.scope}`",
]:
    assert required in raii_js, required

assert (
    "raii_visualizer.js?v=30.7.6"
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
                "visualizer/raii_visualizer.js"
            ),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr

print(
    "Step 30.7.5 RAII Medium legacy-truthfulness regression: PASS"
)
