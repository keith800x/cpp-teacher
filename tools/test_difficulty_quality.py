#!/usr/bin/env python3

from __future__ import annotations

import copy
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
    difficulty_quality_result,
)


def load_exercise(name: str) -> dict:
    with (
        PROJECT_ROOT /
        "exercises" /
        name
    ).open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def artifact_map(exercise: dict) -> dict[str, str]:
    result = {}

    for field in [
        "hidden_test_file",
        "support_file",
        "analysis_support_file",
    ]:
        raw = exercise.get(
            field
        )

        if not isinstance(
            raw,
            str
        ):
            continue

        path = (
            PROJECT_ROOT /
            raw
        )

        if path.exists():
            result[raw] = path.read_text(
                encoding="utf-8"
            )

    return result


published_cases = [
    (
        "references_alias_001.json",
        "easy",
    ),
    (
        "raii_scope_001.json",
        "medium",
    ),
    (
        "move_runtime_trace_001.json",
        "hard",
    ),
]

for filename, expected_difficulty in (
    published_cases
):
    exercise = load_exercise(
        filename
    )

    assert (
        exercise["difficulty"] ==
        expected_difficulty
    )

    valid, detail, evidence = (
        difficulty_quality_result(
            exercise,
            artifact_map(
                exercise
            )
        )
    )

    assert valid, (
        filename,
        detail,
        evidence,
    )

    print(
        "PASS published:",
        filename,
        "->",
        expected_difficulty
    )


# Festival-style hard References exercise:
# only one writable helper + one read-only helper.
festival = copy.deepcopy(
    load_exercise(
        "references_alias_001.json"
    )
)

festival["difficulty"] = "hard"
festival["concept_checks"] = [
    {
        "type":
            "non_const_reference_parameter",
        "function":
            "delaySet",
        "parameter":
            "schedule",
    },
    {
        "type":
            "const_reference_parameter",
        "function":
            "announcementFor",
        "parameter":
            "schedule",
    },
]

valid, detail, evidence = (
    difficulty_quality_result(
        festival,
        {}
    )
)

assert not valid, (
    detail,
    evidence,
)

print(
    "PASS calibration: festival-style "
    "2-decision References is rejected as hard"
)


# Museum/Emergency-style medium:
# multiple decisions, but writable state is concentrated
# in one primary mutation function.
medium_reference = copy.deepcopy(
    load_exercise(
        "references_alias_001.json"
    )
)

medium_reference[
    "difficulty"
] = "medium"

medium_reference[
    "concept_checks"
] = [
    {
        "type":
            "non_const_reference_parameter",
        "function":
            "recordRequest",
        "parameter":
            "liveValue",
    },
    {
        "type":
            "const_reference_parameter",
        "function":
            "recordRequest",
        "parameter":
            "name",
    },
    {
        "type":
            "const_reference_parameter",
        "function":
            "recordRequest",
        "parameter":
            "operatorName",
    },
    {
        "type":
            "const_reference_parameter",
        "function":
            "formatLabel",
        "parameter":
            "name",
    },
    {
        "type":
            "const_reference_parameter",
        "function":
            "formatLabel",
        "parameter":
            "operatorName",
    },
]

valid, detail, evidence = (
    difficulty_quality_result(
        medium_reference,
        {}
    )
)

assert valid, (
    detail,
    evidence,
)

print(
    "PASS calibration: multi-parameter "
    "single-write-path References is medium"
)


# A hard References shape requires multiple writable paths.
hard_reference = copy.deepcopy(
    medium_reference
)

hard_reference[
    "difficulty"
] = "hard"

hard_reference[
    "concept_checks"
].append(
    {
        "type":
            "non_const_reference_parameter",
        "function":
            "commitAdjustment",
        "parameter":
            "liveValue",
    }
)

valid, detail, evidence = (
    difficulty_quality_result(
        hard_reference,
        {}
    )
)

assert valid, (
    detail,
    evidence,
)

print(
    "PASS calibration: multi-function "
    "multi-write-path References qualifies as hard"
)


print(
    "Step 29.2.5 difficulty-quality tests: PASS"
)
