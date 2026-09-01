#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from exercise_validator import (
    ValidationReport,
    pointer_trace_shape_issues,
    trace_stream_contract_issues,
    validate_structure,
)
from generate_exercise import (
    normalize_draft,
    normalize_hidden_runtime_artifact,
)

source = (
    PROJECT_ROOT / "tools" / "generate_exercise.py"
).read_text(encoding="utf-8")

m = re.search(
    r"^PROMPT_VERSION\s*=\s*(\d+)\s*$",
    source,
    re.MULTILINE,
)
assert m and int(m.group(1)) >= 14
assert "Never emit TRACE" in source
assert '"artifacts.trace_stream_contract"' in source

exercise = {
    "exercise_schema_version": 1,
    "id": "trace_stream_fixture",
    "topic": "pointers",
    "title": "Keep the Garden Display Focused",
    "difficulty": "easy",
    "type": "fix_code",
    "scenario": (
        "A community garden display observes one live plant owned elsewhere "
        "while the kiosk remains open for a volunteer reviewing that plant."
    ),
    "problem_statement": (
        "GardenDisplay::highlight receives a Plant but the display does not "
        "retain that selected plant."
    ),
    "constraints": [
        "Keep the API unchanged.",
        "The Plant remains alive.",
        "Do not allocate dynamically.",
    ],
    "learning_objective": (
        "Observe one live object through a raw non-owning pointer."
    ),
    "instructions": (
        "Make the display retain the selected plant."
    ),
    "starter_code": (
        "class Plant{}; "
        "class GardenDisplay { Plant* p_=nullptr; };"
    ),
    "reference_solution": (
        "class Plant{}; "
        "class GardenDisplay { Plant* p_=nullptr; };"
    ),
    "expected_concepts": [
        "raw pointer",
        "null state",
        "pointee identity",
    ],
    "concept_checks": [],
    "hidden_test_file": "tests/trace_stream_fixture.cpp",
    "trace_mode": "runtime",
    "hints": [
        "Observe the object.",
        "It remains alive.",
        "Keep null safe.",
    ],
    "explanation": (
        "The display retains the live object's address."
    ),
    "learner_goal": "Keep the selected plant visible.",
}

bad = r'''
std::cout << "TRACE|CREATE_OBJECT|plant|type=Plant|value=label=mint\n";
std::cout << "TRACE|CREATE_OBJECT|display|type=GardenDisplay|pointer=p_\n";
std::cout << "TRACE|SET_NULL|display.p_|initial\n";
std::cout << "TRACE|BIND_POINTER|display.p_|plant\n";
std::cout << "TRACE|WRITE_VALUE|plant|value=label=lemon mint\n";
'''

files = {
    "tests/trace_stream_fixture.cpp": bad,
}

stream_issues = trace_stream_contract_issues(
    exercise,
    files,
)
assert stream_issues

shape_issues = pointer_trace_shape_issues(
    exercise,
    files,
)
assert shape_issues == []

normalized = normalize_hidden_runtime_artifact(
    bad,
    "pointers",
)

assert 'std::cout << "TRACE|' not in normalized
assert 'std::cerr << "TRACE|' in normalized
assert "TRACE|WRITE_VALUE|plant|value=label=lemon mint" in normalized

normalized_files = {
    "tests/trace_stream_fixture.cpp": normalized,
}

assert trace_stream_contract_issues(
    exercise,
    normalized_files,
) == []

assert pointer_trace_shape_issues(
    exercise,
    normalized_files,
) == []

draft = {
    "exercise": dict(exercise),
    "artifacts": [
        {
            "kind": "hidden_test",
            "path": "ignored.cpp",
            "content": bad,
        }
    ],
}

candidate = normalize_draft(
    draft=draft,
    exercise_id="trace_stream_fixture",
    topic="pointers",
    difficulty="easy",
    model="test",
    response_id="resp_test",
    generation_attempt=1,
)

hidden = candidate["files"][
    "tests/trace_stream_fixture_tests.cpp"
]

assert 'std::cout << "TRACE|' not in hidden
assert 'std::cerr << "TRACE|' in hidden
assert "TRACE|WRITE_VALUE|plant|value=label=lemon mint" in hidden

report = ValidationReport(
    source="bad",
    exercise_id=exercise["id"],
    checks=[],
)

validate_structure(
    exercise,
    report,
    bundled_files=files,
)

status = {
    check.id: check.status
    for check in report.checks
}

assert status[
    "artifacts.trace_stream_contract"
] == "fail"

assert status[
    "artifacts.pointer_trace_shape"
] == "pass"

print(
    "Step 30.5.1 runtime trace-stream contract regression: PASS"
)
