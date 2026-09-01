#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(PROJECT_ROOT / "tools")
)

from generate_exercise import normalize_draft

draft = {
    "exercise": {
        "exercise_schema_version": 1,
        "id": "placeholder",
        "topic": "references",
        "title": "Keep a service update connected to caller state",
        "difficulty": "easy",
        "type": "fix_code",
        "scenario": (
            "A service receives a caller-owned count and needs to update "
            "that live value while processing an ordinary business operation."
        ),
        "problem_statement": (
            "The helper currently changes only its own integer copy, so the "
            "caller observes no update after the function returns even though "
            "the function body performs the expected arithmetic."
        ),
        "constraints": [
            "Keep the existing function body unchanged."
        ],
        "learning_objective": (
            "Choose a writable reference parameter when a function must "
            "modify caller-owned state."
        ),
        "learner_goal": (
            "Make the service update remain visible in the owning object after the helper returns."
        ),
        "instructions": (
            "Correct the API behavior without changing the arithmetic "
            "performed inside the function body."
        ),
        "starter_code": (
            "void updateCount(int count) { count += 1; }"
        ),
        "reference_solution": (
            "void updateCount(int& count) { count += 1; }"
        ),
        "expected_concepts": ["reference"],
        "concept_checks": [
            {
                "type": "non_const_reference_parameter",
                "function": "updateCount",
                "parameter": "count",
                "variable": "",
                "argument": "",
                "class": "",
            }
        ],
        "hidden_test_file": "ignored.cpp",
        "support_file": "",
        "analysis_support_file": "",
        "trace_mode": "runtime",
        "hints": [
            "Consider whether the function needs a separate integer object."
        ],
        "explanation": (
            "A writable reference aliases the caller-owned integer, so the "
            "change is observable after the function returns."
        ),
    },
    "artifacts": [
        {
            "kind": "hidden_test",
            "path": "ignored.cpp",
            "content": "int main() { return 0; }",
        }
    ],
}

candidate = normalize_draft(
    draft=draft,
    exercise_id="ai_references_test_001",
    topic="references",
    difficulty="easy",
    model="test-model",
    response_id="resp_test",
    generation_attempt=1,
)

assert candidate["exercise"]["id"] == "ai_references_test_001"
assert (
    candidate["exercise"]["hidden_test_file"]
    == "tests/ai_references_test_001_tests.cpp"
)
assert "support_file" not in candidate["exercise"]
assert "analysis_support_file" not in candidate["exercise"]

check = candidate["exercise"]["concept_checks"][0]
assert set(check.keys()) == {
    "type",
    "function",
    "parameter",
}

print("Step 28 generator normalization test: PASS")
