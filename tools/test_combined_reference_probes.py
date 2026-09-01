#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(
        PROJECT_ROOT /
        "tools"
    )
)

from exercise_validator import (
    hard_reference_probe_pairs,
    synthesize_reference_probe_set,
    timeline_has_reference_binding,
)


starter = r"""
struct State
{
    int value;
};

void first(State state)
{
    ++state.value;
}

void second(State state)
{
    ++state.value;
}

int readOne(State state)
{
    return state.value;
}

int readTwo(State state)
{
    return state.value;
}
"""

reference = r"""
struct State
{
    int value;
};

void first(State& state)
{
    ++state.value;
}

void second(State& state)
{
    ++state.value;
}

int readOne(const State& state)
{
    return state.value;
}

int readTwo(const State& state)
{
    return state.value;
}
"""

checks = [
    {
        "type":
            "non_const_reference_parameter",
        "function":
            "first",
        "parameter":
            "state",
    },
    {
        "type":
            "non_const_reference_parameter",
        "function":
            "second",
        "parameter":
            "state",
    },
    {
        "type":
            "const_reference_parameter",
        "function":
            "readOne",
        "parameter":
            "state",
    },
    {
        "type":
            "const_reference_parameter",
        "function":
            "readTwo",
        "parameter":
            "state",
    },
]

pairs = hard_reference_probe_pairs(
    checks
)

assert len(
    pairs
) == 6, len(
    pairs
)

probe_source, details, summary = (
    synthesize_reference_probe_set(
        starter,
        reference,
        [
            checks[0],
            checks[2],
        ]
    )
)

assert probe_source is not None
assert (
    "void first(State& state)" in
    probe_source
)
assert (
    "int readOne(const State& state)" in
    probe_source
)
assert (
    "void second(State state)" in
    probe_source
)
assert (
    "int readTwo(State state)" in
    probe_source
)
assert len(
    details
) == 2
assert (
    "first.state" in
    summary
)
assert (
    "readOne.state" in
    summary
)

timeline = {
    "timeline": [
        {
            "step": 1,
            "cause": {
                "type": "ENTER_SCOPE",
                "subject": "caller",
                "detail": "",
            },
            "active_scopes": [
                "caller"
            ],
            "stack": [],
            "stack_values": [],
            "aliases": [],
            "heap": [],
        },
        {
            "step": 2,
            "cause": {
                "type": "CREATE_VALUE",
                "subject": "liveState",
                "detail": "type=State|value=1",
            },
            "active_scopes": [
                "caller"
            ],
            "stack": [],
            "stack_values": [
                {
                    "name": "liveState",
                    "type": "State",
                    "scope": "caller",
                    "value": "1",
                    "alive": True,
                }
            ],
            "aliases": [],
            "heap": [],
        },
        {
            "step": 3,
            "cause": {
                "type": "ENTER_SCOPE",
                "subject": "first",
                "detail": "",
            },
            "active_scopes": [
                "caller",
                "first",
            ],
            "stack": [],
            "stack_values": [
                {
                    "name": "liveState",
                    "type": "State",
                    "scope": "caller",
                    "value": "1",
                    "alive": True,
                }
            ],
            "aliases": [],
            "heap": [],
        },
        {
            "step": 4,
            "cause": {
                "type": "BIND_ALIAS",
                "subject": "state",
                "detail": (
                    "target=liveState|"
                    "type=State&|"
                    "const=false"
                ),
            },
            "active_scopes": [
                "caller",
                "first",
            ],
            "stack": [],
            "stack_values": [
                {
                    "name": "liveState",
                    "type": "State",
                    "scope": "caller",
                    "value": "1",
                    "alive": True,
                }
            ],
            "aliases": [
                {
                    "name": "state",
                    "type": "State&",
                    "scope": "first",
                    "target": "liveState",
                    "const": False,
                    "alive": True,
                }
            ],
            "heap": [],
        },
        {
            "step": 5,
            "cause": {
                "type": "WRITE_VALUE",
                "subject": "liveState",
                "detail": "via=first|value=2",
            },
            "active_scopes": [
                "caller",
                "first",
            ],
            "stack": [],
            "stack_values": [
                {
                    "name": "liveState",
                    "type": "State",
                    "scope": "caller",
                    "value": "2",
                    "alive": True,
                }
            ],
            "aliases": [
                {
                    "name": "state",
                    "type": "State&",
                    "scope": "first",
                    "target": "liveState",
                    "const": False,
                    "alive": True,
                }
            ],
            "heap": [],
        },
        {
            "step": 6,
            "cause": {
                "type": "EXIT_SCOPE",
                "subject": "first",
                "detail": "",
            },
            "active_scopes": [
                "caller"
            ],
            "stack": [],
            "stack_values": [
                {
                    "name": "liveState",
                    "type": "State",
                    "scope": "caller",
                    "value": "2",
                    "alive": True,
                }
            ],
            "aliases": [],
            "heap": [],
        },
        {
            "step": 7,
            "cause": {
                "type": "ENTER_SCOPE",
                "subject": "readOne",
                "detail": "",
            },
            "active_scopes": [
                "caller",
                "readOne",
            ],
            "stack": [],
            "stack_values": [
                {
                    "name": "liveState",
                    "type": "State",
                    "scope": "caller",
                    "value": "2",
                    "alive": True,
                }
            ],
            "aliases": [],
            "heap": [],
        },
        {
            "step": 8,
            "cause": {
                "type": "BIND_ALIAS",
                "subject": "state",
                "detail": (
                    "target=liveState|"
                    "type=const State&|"
                    "const=true"
                ),
            },
            "active_scopes": [
                "caller",
                "readOne",
            ],
            "stack": [],
            "stack_values": [
                {
                    "name": "liveState",
                    "type": "State",
                    "scope": "caller",
                    "value": "2",
                    "alive": True,
                }
            ],
            "aliases": [
                {
                    "name": "state",
                    "type": "const State&",
                    "scope": "readOne",
                    "target": "liveState",
                    "const": True,
                    "alive": True,
                }
            ],
            "heap": [],
        },
    ]
}

first_ok, first_detail = (
    timeline_has_reference_binding(
        timeline,
        function_name="first",
        parameter_name="state",
        expected_const=False,
    )
)

read_ok, read_detail = (
    timeline_has_reference_binding(
        timeline,
        function_name="readOne",
        parameter_name="state",
        expected_const=True,
    )
)

assert first_ok, first_detail
assert read_ok, read_detail

# Also verify the uploaded/repaired Festival candidate has
# the expected six pair combinations when available.
candidate_path = Path(
    "/mnt/data/"
    "ai_references_20260814_102501_2d9918.json"
)

if candidate_path.exists():
    candidate = json.loads(
        candidate_path.read_text(
            encoding="utf-8"
        )
    )

    concept_checks = candidate[
        "exercise"
    ][
        "concept_checks"
    ]

    assert len(
        hard_reference_probe_pairs(
            concept_checks
        )
    ) == 6

print(
    "Step 29.2.6 combined-reference-probe tests: PASS"
)
