#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from exercise_validator import (
    ValidationReport,
    difficulty_quality_result,
    pointer_trace_shape_issues,
    validate_structure,
)

generator_source = (
    PROJECT_ROOT / "tools" / "generate_exercise.py"
).read_text(encoding="utf-8")

version_match = re.search(
    r"^PROMPT_VERSION\s*=\s*(\d+)\s*$",
    generator_source,
    re.MULTILINE,
)

assert version_match
assert int(version_match.group(1)) >= 11
assert "STACK POINTEE example" in generator_source
assert "BIND_POINTER|console.highlighted_|riverSighting" in generator_source
assert 'check_id == "artifacts.pointer_trace_shape"' in generator_source

exercise = {
    "exercise_schema_version": 1,
    "id": "pointer_trace_shape_fixture",
    "topic": "pointers",
    "title": "Keep the Ranger Console on the Selected Sighting",
    "difficulty": "easy",
    "type": "fix_code",
    "scenario": "A console observes one live sighting.",
    "problem_statement": (
        "RangerConsole::highlight receives a live Sighting, but "
        "highlightedAnimal still reports no selection."
    ),
    "constraints": [
        "Keep the public API unchanged.",
        "The console does not own the sighting.",
    ],
    "learning_objective": "Store one non-owning const raw pointer.",
    "instructions": "Keep the selected sighting visible.",
    "starter_code": '''
#include <string>
struct Sighting { std::string animal; };
class RangerConsole {
public:
    void highlight(const Sighting& sighting) {
        highlighted_ = nullptr;
    }
private:
    const Sighting* highlighted_ = nullptr;
};
''',
    "reference_solution": '''
#include <string>
struct Sighting { std::string animal; };
class RangerConsole {
public:
    void highlight(const Sighting& sighting) {
        highlighted_ = &sighting;
    }
private:
    const Sighting* highlighted_ = nullptr;
};
''',
    "expected_concepts": [
        "non-owning raw pointer",
        "null pointer state",
    ],
    "concept_checks": [],
    "hidden_test_file": "tests/pointer_trace_shape_fixture_tests.cpp",
    "trace_mode": "runtime",
    "hints": [
        "The console observes an existing object.",
        "The object remains alive.",
        "Preserve the null initial state.",
    ],
    "explanation": "The console stores the address of the selected object.",
    "learner_goal": "Keep the console on the selected sighting.",
}

bad_files = {
    "tests/pointer_trace_shape_fixture_tests.cpp": r'''
std::cerr << "TRACE|CREATE_OBJECT|console|type=RangerConsole|holder=highlighted_\n";
std::cerr << "TRACE|SET_NULL|highlighted_|initial\n";
std::cerr << "TRACE|BIND_POINTER|highlighted_|missingSighting\n";
'''
}

issues = pointer_trace_shape_issues(
    exercise,
    bad_files,
)

issue_text = "\n".join(issues)

assert "BIND_POINTER subject 'highlighted_'" in issue_text
assert "BIND_POINTER target 'missingSighting'" in issue_text
assert "SET_NULL subject 'highlighted_'" in issue_text

bad_report = ValidationReport(
    source="fixture",
    exercise_id=exercise["id"],
    checks=[],
)

validate_structure(
    exercise,
    bad_report,
    bundled_files=bad_files,
)

bad_status = {
    check.id: check.status
    for check in bad_report.checks
}

assert bad_status["artifacts.pointer_trace_shape"] == "fail"

good_files = {
    "tests/pointer_trace_shape_fixture_tests.cpp": r'''
std::cerr << "TRACE|CREATE_OBJECT|riverSighting|type=Sighting|value=animal=river otter\n";
std::cerr << "TRACE|CREATE_OBJECT|console|type=RangerConsole|pointer=highlighted_\n";
std::cerr << "TRACE|SET_NULL|console.highlighted_|pointer cleared\n";
std::cerr << "TRACE|BIND_POINTER|console.highlighted_|riverSighting\n";
'''
}

assert pointer_trace_shape_issues(
    exercise,
    good_files,
) == []

valid, detail, evidence = difficulty_quality_result(
    exercise,
    good_files,
)

assert valid, detail
assert evidence["pointer_subjects"] == 1
assert evidence["pointer_holder_objects"] == 1
assert evidence["pointer_targets"] == 1
assert evidence["pointer_resources"] == 0
assert evidence["pointer_decisions"] == 2
assert evidence["null_state"] is True
assert evidence["reseating"] is False

good_report = ValidationReport(
    source="fixture",
    exercise_id=exercise["id"],
    checks=[],
)

validate_structure(
    exercise,
    good_report,
    bundled_files=good_files,
)

good_status = {
    check.id: check.status
    for check in good_report.checks
}

assert good_status["artifacts.pointer_trace_shape"] == "pass"
assert good_status["difficulty.quality"] == "pass"

print("Step 30.4 pointer trace-shape regression test: PASS")
