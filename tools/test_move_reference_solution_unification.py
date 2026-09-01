#!/usr/bin/env python3

from __future__ import annotations

import ast
import json
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

server_path = ROOT / "dev_server.py"
server = server_path.read_text(
    encoding="utf-8"
)

# The legacy route must no longer call latest_solution_timeline directly.
route_marker = (
    'len(parts) == 3 and\n'
    '                parts[1] == "solution" and\n'
    '                parts[2] == "visualization"'
)

route_start = server.index(
    route_marker
)

route_end = server.index(
    'if (\n'
    '                len(parts) == 4 and\n'
    '                parts[1] == "attempts"',
    route_start,
)

route = server[
    route_start:
    route_end
]

assert (
    "reference_timeline_for_solution_view("
    in route
)

assert (
    "latest_solution_timeline("
    not in route
)

# The resolver must explicitly avoid stale legacy fallback for a generated
# candidate whose validated archive is absent/stale.
resolver_start = server.index(
    "def reference_timeline_for_solution_view("
)

resolver_end = server.index(
    "\n\ndef ",
    resolver_start + 10,
)

resolver_source = server[
    resolver_start:
    resolver_end
]

for required in [
    "authoring_candidate_id_is_safe(",
    "authoring_candidate_paths(",
    "read_candidate_reference_timeline(",
    "return latest_solution_timeline(",
    "Do NOT fall back to an old solution timeline",
]:
    assert required in resolver_source, required

# Execute only the resolver against controlled fake sources.
tree = ast.parse(
    server,
    filename=str(server_path),
)

resolver_node = next(
    node
    for node in tree.body
    if (
        isinstance(node, ast.FunctionDef)
        and node.name ==
            "reference_timeline_for_solution_view"
    )
)

module = ast.Module(
    body=[
        resolver_node,
    ],
    type_ignores=[],
)

ast.fix_missing_locations(
    module
)

with tempfile.TemporaryDirectory(
    prefix="cpp_teacher_reference_unify_"
) as temp_dir:
    temp = Path(temp_dir)

    generated_id = (
        "ai_move_semantics_probe"
    )

    normal_id = (
        "move_runtime_trace_001"
    )

    generated_candidate = (
        temp /
        f"{generated_id}.json"
    )

    generated_candidate.write_text(
        "{}\n",
        encoding="utf-8",
    )

    validated14 = {
        "timeline": [
            {
                "step": i
            }
            for i in range(
                1,
                15,
            )
        ],
    }

    stale11 = {
        "timeline": [
            {
                "step": i
            }
            for i in range(
                1,
                12,
            )
        ],
    }

    calls = []

    namespace = {
        "authoring_candidate_id_is_safe":
            lambda exercise_id:
                exercise_id.startswith("ai_"),
        "authoring_candidate_paths":
            lambda exercise_id: (
                generated_candidate,
                temp /
                f"{exercise_id}.validation.json",
            ),
        "read_candidate_reference_timeline":
            lambda exercise_id: (
                calls.append(
                    ("candidate", exercise_id)
                )
                or validated14
            ),
        "latest_solution_timeline":
            lambda exercise_id: (
                calls.append(
                    ("legacy", exercise_id)
                )
                or stale11
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

    resolve = namespace[
        "reference_timeline_for_solution_view"
    ]

    generated = resolve(
        generated_id
    )

    assert len(
        generated["timeline"]
    ) == 14

    assert calls == [
        (
            "candidate",
            generated_id,
        ),
    ]

    calls.clear()

    normal = resolve(
        normal_id
    )

    assert len(
        normal["timeline"]
    ) == 11

    assert calls == [
        (
            "legacy",
            normal_id,
        ),
    ]

    # Critical safety case: a generated candidate with no current validated
    # archive must return None. It must NOT silently resurrect stale11.
    calls.clear()

    namespace[
        "read_candidate_reference_timeline"
    ] = lambda exercise_id: (
        calls.append(
            ("candidate", exercise_id)
        )
        or None
    )

    # Re-exec so the function resolves the replaced global.
    generated_stale = resolve(
        generated_id
    )

    assert generated_stale is None

    assert calls == [
        (
            "candidate",
            generated_id,
        ),
    ]

print(
    "Step 30.8.3 unified Reference Solution timeline regression: PASS"
)
