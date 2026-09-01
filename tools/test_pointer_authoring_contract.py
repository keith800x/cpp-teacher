#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(PROJECT_ROOT / "tools")
)

from exercise_validator import (
    ValidationReport,
    difficulty_quality_result,
    unsupported_pointer_trace_events,
    validate_structure,
)


generator_source = (
    PROJECT_ROOT /
    "tools" /
    "generate_exercise.py"
).read_text(
    encoding="utf-8"
)

version_match = re.search(
    r"^PROMPT_VERSION\s*=\s*(\d+)\s*$",
    generator_source,
    re.MULTILINE,
)

assert version_match
assert int(version_match.group(1)) >= 9

for required_text in [
    "concept_checks MUST be [] for Pointers",
    "NEVER emit CREATE_POINTER",
    "POINTER_DECISION",
    "READ_POINTER",
    "CREATE_OBJECT with pointer=field_",
    "emit BIND_POINTER only when the learner-visible pointer really holds",
    'check_id == "artifacts.pointer_trace_contract"',
    'check_id == "schema.pointer_concept_checks"',
]:
    assert required_text in generator_source, required_text


def base_exercise() -> dict:
    return {
        "exercise_schema_version": 1,
        "id": "pointer_contract_fixture",
        "topic": "pointers",
        "title": "Remember the selected sensor reading",
        "difficulty": "easy",
        "type": "fix_code",
        "scenario": (
            "A monitoring console observes one sensor that remains alive "
            "throughout a review session."
        ),
        "problem_statement": (
            "Console::select receives the live Sensor chosen by an operator, "
            "but Console::label still reports that nothing is selected after "
            "the call. Preserve the existing no-selection behavior before "
            "the first selection."
        ),
        "constraints": [
            "Keep the existing public API unchanged.",
            "The console does not own the selected sensor.",
        ],
        "learning_objective": (
            "Store and observe a non-owning raw pointer to an existing live "
            "object."
        ),
        "instructions": (
            "Modify the existing implementation so the console remembers "
            "the selected sensor without taking ownership."
        ),
        "starter_code": '''
struct Sensor { int level; };

class Console {
public:
    void select(const Sensor& sensor) {
        selected_ = nullptr;
    }

private:
    const Sensor* selected_ = nullptr;
};
''',
        "reference_solution": '''
struct Sensor { int level; };

class Console {
public:
    void select(const Sensor& sensor) {
        selected_ = &sensor;
    }

private:
    const Sensor* selected_ = nullptr;
};
''',
        "expected_concepts": [
            "non-owning raw pointer",
            "null pointer state",
        ],
        "concept_checks": [],
        "hidden_test_file":
            "tests/pointer_contract_fixture_tests.cpp",
        "trace_mode": "runtime",
        "hints": [
            "The selected Sensor already exists.",
            "The console only observes it.",
            "Keep the initial no-selection state.",
        ],
        "explanation": (
            "The console remembers the live Sensor without owning it."
        ),
        "learner_goal": (
            "Keep the console on the sensor selected during the review."
        ),
    }


bad = base_exercise()
bad["concept_checks"] = [
    {
        "type": "const_reference_parameter",
        "function": "Console::select",
        "parameter": "sensor",
    }
]

bad_files = {
    "tests/pointer_contract_fixture_tests.cpp": '''
std::fprintf(stderr, "TRACE|CREATE_POINTER|console.selected_|nullptr\\n");
std::fprintf(stderr, "TRACE|POINTER_DECISION|console.selected_|not_null\\n");
std::fprintf(stderr, "TRACE|READ_POINTER|console.selected_|level=8\\n");
'''
}

assert unsupported_pointer_trace_events(
    bad,
    bad_files,
) == [
    "CREATE_POINTER",
    "POINTER_DECISION",
    "READ_POINTER",
]

bad_report = ValidationReport(
    source="fixture",
    exercise_id=bad["id"],
    checks=[],
)

validate_structure(
    bad,
    bad_report,
    bundled_files=bad_files,
)

bad_status = {
    check.id: check.status
    for check in bad_report.checks
}

assert bad_status["schema.pointer_concept_checks"] == "fail"
assert bad_status["artifacts.pointer_trace_contract"] == "fail"
assert bad_status["difficulty.quality"] == "fail"


good = base_exercise()

good_files = {
    "tests/pointer_contract_fixture_tests.cpp": '''
std::fprintf(stderr, "TRACE|CREATE_OBJECT|console|type=Console|pointer=selected_\\n");
std::fprintf(stderr, "TRACE|ALLOCATE_RESOURCE|resource#1|value=level=8\\n");
if (selected) {
    std::fprintf(stderr, "TRACE|BIND_POINTER|console.selected_|resource#1\\n");
} else {
    std::fprintf(stderr, "TRACE|SET_NULL|console.selected_|no selection\\n");
}
'''
}

assert unsupported_pointer_trace_events(
    good,
    good_files,
) == []

valid, detail, evidence = difficulty_quality_result(
    good,
    good_files,
)

assert valid, detail
assert evidence["pointer_subjects"] == 1
assert evidence["pointer_decisions"] == 2
assert evidence["null_state"] is True
assert evidence["aliasing"] is False
assert evidence["lifetime_boundary"] is False

good_report = ValidationReport(
    source="fixture",
    exercise_id=good["id"],
    checks=[],
)

validate_structure(
    good,
    good_report,
    bundled_files=good_files,
)

good_status = {
    check.id: check.status
    for check in good_report.checks
}

assert good_status["schema.pointer_concept_checks"] == "pass"
assert good_status["artifacts.pointer_trace_contract"] == "pass"
assert good_status["difficulty.quality"] == "pass"

print(
    "Step 30.1 pointer authoring-contract regression test: PASS"
)
