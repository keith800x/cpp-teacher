#!/usr/bin/env python3

from __future__ import annotations

import copy
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from generate_exercise import (
    is_pointer_trace_only_repair,
    preserve_pointer_trace_repair_core,
)

report = {
    "checks": [
        {
            "id": "artifacts.pointer_trace_shape",
            "category": "artifacts",
            "status": "fail",
            "message": "bad trace target",
        },
        {
            "id": "difficulty.quality",
            "category": "difficulty",
            "status": "fail",
            "message": "pointer evidence not measurable",
        },
    ]
}

assert is_pointer_trace_only_repair("pointers", report)

original = {
    "candidate_schema_version": 1,
    "generation_metadata": {
        "generation_attempt": 1,
        "prompt_version": 11,
    },
    "exercise": {
        "id": "ai_pointer_stable_repair",
        "topic": "pointers",
        "difficulty": "easy",
        "scenario": "ORIGINAL SCENARIO",
        "problem_statement": "ORIGINAL PROBLEM",
        "constraints": ["ORIGINAL CONSTRAINT"],
        "learning_objective": "ORIGINAL OBJECTIVE",
        "instructions": "ORIGINAL INSTRUCTIONS",
        "starter_code": "ORIGINAL STARTER",
        "reference_solution": "ORIGINAL REFERENCE",
        "expected_concepts": ["ORIGINAL CONCEPT"],
        "concept_checks": [],
        "hints": ["ORIGINAL HINT"],
        "explanation": "ORIGINAL EXPLANATION",
        "learner_goal": "ORIGINAL GOAL",
        "hidden_test_file": "tests/ai_pointer_stable_repair_tests.cpp",
        "trace_mode": "runtime",
        "type": "fix_code",
        "title": "ORIGINAL TITLE",
    },
    "files": {
        "tests/ai_pointer_stable_repair_tests.cpp": "BROKEN HIDDEN TEST",
        "support/keep.hpp": "KEEP SUPPORT",
    },
}

repaired = copy.deepcopy(original)

repaired["generation_metadata"] = {
    "generation_attempt": 2,
    "prompt_version": 11,
}

repaired["exercise"]["title"] = "DRIFTED TITLE"
repaired["exercise"]["scenario"] = "DRIFTED SCENARIO"
repaired["exercise"]["problem_statement"] = "DRIFTED PROBLEM"
repaired["exercise"]["starter_code"] = "DRIFTED STARTER"
repaired["exercise"]["reference_solution"] = "DRIFTED REFERENCE"
repaired["exercise"]["difficulty"] = "medium"
repaired["exercise"]["concept_checks"] = [
    {
        "type": "const_reference_parameter",
        "function": "f",
        "parameter": "x",
    }
]

repaired["files"][
    "tests/ai_pointer_stable_repair_tests.cpp"
] = "FIXED HIDDEN TEST"

repaired["files"]["support/keep.hpp"] = "DRIFTED SUPPORT"

merged = preserve_pointer_trace_repair_core(
    previous_candidate=original,
    repaired_candidate=repaired,
    report=report,
)

assert merged["generation_metadata"]["generation_attempt"] == 2
assert merged["exercise"]["title"] == "ORIGINAL TITLE"
assert merged["exercise"]["scenario"] == "ORIGINAL SCENARIO"
assert merged["exercise"]["problem_statement"] == "ORIGINAL PROBLEM"
assert merged["exercise"]["starter_code"] == "ORIGINAL STARTER"
assert merged["exercise"]["reference_solution"] == "ORIGINAL REFERENCE"
assert merged["exercise"]["difficulty"] == "easy"
assert merged["exercise"]["concept_checks"] == []
assert (
    merged["files"]["tests/ai_pointer_stable_repair_tests.cpp"]
    == "FIXED HIDDEN TEST"
)
assert merged["files"]["support/keep.hpp"] == "KEEP SUPPORT"

non_trace_report = {
    "checks": [
        {
            "id": "pedagogy.starter_differs",
            "category": "pedagogy",
            "status": "fail",
            "message": "starter equals reference",
        }
    ]
}

assert not is_pointer_trace_only_repair(
    "pointers",
    non_trace_report,
)

unfrozen = preserve_pointer_trace_repair_core(
    previous_candidate=original,
    repaired_candidate=repaired,
    report=non_trace_report,
)

assert unfrozen["exercise"]["scenario"] == "DRIFTED SCENARIO"

print("Step 30.4 stable pointer trace-repair regression test: PASS")
