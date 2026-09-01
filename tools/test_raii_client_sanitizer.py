#!/usr/bin/env python3

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

server_path = (
    ROOT /
    "dev_server.py"
)

source = server_path.read_text(
    encoding="utf-8"
)

tree = ast.parse(
    source,
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

ast.fix_missing_locations(
    module
)

namespace = {
    "exercise_topic_for_visualization":
        lambda exercise_id: "raii_scope",
    "raii_learner_operation_for_visualization":
        lambda exercise_id: "publishMorningBulletin",
}

exec(
    compile(
        module,
        str(server_path),
        "exec",
    ),
    namespace,
)

timeline = {
    "exercise_id": "probe",
    "schema_version": 4,
    "timeline": [
        {
            "step": 1,
            "active_scopes": [
                "processVideoFrame",
            ],
            "cause": {
                "type": "ENTER_SCOPE",
                "subject": "processVideoFrame",
            },
            "stack": [],
            "heap": [],
        },
        {
            "step": 2,
            "active_scopes": [
                "processVideoFrame",
                "publishMorningBulletin",
            ],
            "cause": {
                "type": "CREATE_OBJECT",
                "subject": "morningBulletin",
            },
            "stack": [
                {
                    "name": "morningBulletin",
                    "type": "BulletinPacket",
                    "fields": {
                        "data_": {
                            "kind": "pointer",
                            "points_to": None,
                        },
                    },
                },
            ],
            "heap": [],
        },
        {
            "step": 3,
            "active_scopes": [
                "processVideoFrame",
                "publishMorningBulletin",
            ],
            "cause": {
                "type": "BIND_POINTER",
                "subject": "gaugeSession.channel_",
                "detail": "resource#1",
            },
            "stack": [
                {
                    "name": "gaugeSession",
                    "type": "TideGaugeSession",
                    "fields": {
                        "channel_": {
                            "kind": "pointer",
                            "points_to": "resource#1",
                        },
                    },
                },
                {
                    "name": "morningBulletin",
                    "type": "BulletinPacket",
                    "fields": {
                        "data_": {
                            "kind": "pointer",
                            "points_to": None,
                        },
                    },
                },
            ],
            "heap": [
                {
                    "id": "resource#1",
                    "alive": True,
                },
            ],
        },
    ],
}

cleaned = namespace[
    "visualization_timeline_for_client"
](
    "probe",
    timeline,
)

frames = cleaned[
    "timeline"
]

assert len(frames) == 2
assert [
    frame["step"]
    for frame in frames
] == [1, 2]

assert frames[0][
    "stack"
][0][
    "fields"
] == {}

gauge_fields = frames[1][
    "stack"
][0][
    "fields"
]

assert gauge_fields == {
    "channel_": {
        "kind": "pointer",
        "points_to": "resource#1",
    },
}

assert frames[1][
    "stack"
][1][
    "fields"
] == {}

assert all(
    "processVideoFrame"
    not in frame.get(
        "active_scopes",
        []
    )
    for frame in frames
)

print(
    "Step 30.7.4 RAII client sanitizer behavior: PASS"
)
