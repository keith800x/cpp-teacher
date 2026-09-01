#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(PROJECT_ROOT / "tools")
)

from exercise_validator import (
    ValidationReport,
    validate_structure,
)


# Immutable embedded fixture.
# Never depend on candidates/generated/... in a regression test because
# AI authoring candidates are mutable data.
exercise = {
    "exercise_schema_version": 1,
    "id": "ranger_pointer_easy_regression",
    "topic": "pointers",
    "title": "Keep the Ranger Console on the Selected Sighting",
    "difficulty": "easy",
    "type": "fix_code",
    "scenario": (
        "A ranger console observes one selected sighting that remains "
        "alive throughout the review."
    ),
    "problem_statement": (
        "RangerConsole::highlight receives a live Sighting, but the "
        "console does not remember it after the call."
    ),
    "constraints": [
        "Keep the public API unchanged.",
        "The console does not own the sighting.",
        "The sighting remains alive during the review.",
    ],
    "learning_objective": (
        "Store one non-owning raw pointer to an existing live object."
    ),
    "instructions": (
        "Modify the implementation so the console remembers the "
        "selected sighting."
    ),
    "starter_code": '''
#include <string>

struct Sighting {
    std::string animal;
};

class RangerConsole {
public:
    void highlight(const Sighting& sighting) {
        (void)sighting;
    }

    std::string highlightedAnimal() const {
        if (highlighted_ == nullptr) {
            return "No sighting selected";
        }

        return highlighted_->animal;
    }

private:
    const Sighting* highlighted_ = nullptr;
};
''',
    "reference_solution": '''
#include <string>

struct Sighting {
    std::string animal;
};

class RangerConsole {
public:
    void highlight(const Sighting& sighting) {
        highlighted_ = &sighting;
    }

    std::string highlightedAnimal() const {
        if (highlighted_ == nullptr) {
            return "No sighting selected";
        }

        return highlighted_->animal;
    }

private:
    const Sighting* highlighted_ = nullptr;
};
''',
    "expected_concepts": [
        "non-owning raw pointer",
        "null pointer state",
        "storing an existing object's address",
    ],
    "concept_checks": [],
    "hidden_test_file":
        "tests/ranger_pointer_easy_regression_tests.cpp",
    "trace_mode": "runtime",
    "hints": [
        "The console observes an existing object.",
        "The sighting remains alive.",
        "Preserve the initial empty state.",
    ],
    "explanation": (
        "The console stores the selected live sighting's address "
        "without taking ownership."
    ),
    "learner_goal": (
        "Keep the ranger console on the selected sighting."
    ),
}

files = {
    "tests/ranger_pointer_easy_regression_tests.cpp": '''
#include <cassert>
#include <iostream>
#include <string>

int main() {
    std::cerr << "TRACE|ENTER_SCOPE|main|ranger review\\n";

    Sighting riverSighting{"river otter"};
    std::cerr << "TRACE|CREATE_OBJECT|riverSighting|type=Sighting|value=animal=river otter\\n";

    RangerConsole console;
    std::cerr << "TRACE|CREATE_OBJECT|console|type=RangerConsole|pointer=highlighted_\\n";
    std::cerr << "TRACE|SET_NULL|console.highlighted_|initial selection\\n";

    const std::string emptyMessage =
        console.highlightedAnimal();

    console.highlight(
        riverSighting
    );

    const std::string selectedAnimal =
        console.highlightedAnimal();

    const bool selectionWorked =
        selectedAnimal == "river otter";

    if (selectionWorked) {
        std::cerr << "TRACE|BIND_POINTER|console.highlighted_|riverSighting\\n";
    } else {
        std::cerr << "TRACE|SET_NULL|console.highlighted_|selection missing\\n";
    }

    assert(
        emptyMessage ==
        "No sighting selected"
    );

    assert(
        selectionWorked
    );

    std::cerr << "TRACE|EXIT_SCOPE|main|ranger review complete\\n";
    return 0;
}
'''
}

report = ValidationReport(
    source="embedded ranger fixture",
    exercise_id=exercise["id"],
    checks=[],
)

validate_structure(
    exercise,
    report,
    bundled_files=files,
)

failures = [
    check
    for check in report.checks
    if check.status == "fail"
]

assert not failures, (
    "\n".join(
        f"{check.id}: {check.message}"
        for check in failures
    )
)

status = {
    check.id: check.status
    for check in report.checks
}

for check_id in [
    "schema.pointer_concept_checks",
    "artifacts.pointer_trace_contract",
    "artifacts.pointer_trace_shape",
    "difficulty.quality",
]:
    assert status[
        check_id
    ] == "pass"

print(
    "Step 30.4 Ranger Easy pointer regression: PASS"
)
