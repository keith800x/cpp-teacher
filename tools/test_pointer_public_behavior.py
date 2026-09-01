#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from exercise_validator import (
    ValidationReport,
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
assert int(version_match.group(1)) >= 12

for required in [
    "NEVER add a learner-visible `friend` declaration",
    "mutate that SAME original caller-owned object directly",
    'check_id == "pedagogy.pointer_no_test_hooks"',
]:
    assert required in generator_source, required


def make_exercise(
    starter_code: str,
    reference_solution: str
) -> dict:
    return {
        "exercise_schema_version": 1,
        "id": "pointer_public_behavior_fixture",
        "topic": "pointers",
        "title": "Keep the Kitchen Display on the Selected Recipe",
        "difficulty": "easy",
        "type": "fix_code",
        "scenario": (
            "A cafe kitchen display observes one recipe card owned by the "
            "menu system, and that card remains alive while the display "
            "continues showing its title to the prep team."
        ),
        "problem_statement": (
            "KitchenDisplay::feature receives a RecipeCard, but "
            "KitchenDisplay::featuredTitle still reports no selection."
        ),
        "constraints": [
            "Keep the public API unchanged.",
            "The selected RecipeCard remains alive.",
            "Do not add dynamic allocation.",
        ],
        "learning_objective": (
            "Observe one live object through a raw non-owning pointer."
        ),
        "instructions": (
            "Make the display retain the selected recipe."
        ),
        "starter_code": starter_code,
        "reference_solution": reference_solution,
        "expected_concepts": [
            "raw non-owning pointer",
            "null pointer state",
            "safe dereference",
        ],
        "concept_checks": [],
        "hidden_test_file":
            "tests/pointer_public_behavior_fixture.cpp",
        "trace_mode": "runtime",
        "hints": [
            "The display observes an existing object.",
            "The selected object remains alive.",
            "Keep the empty state safe.",
        ],
        "explanation": (
            "The display retains the address of the live recipe card."
        ),
        "learner_goal": (
            "Keep the selected recipe visible after feature returns."
        ),
    }


bad_starter = '''
#include <string>

struct RecipeCard {
    std::string title;
};

class KitchenDisplay {
public:
    void feature(const RecipeCard& card) {
        featured_ = nullptr;
    }

    std::string featuredTitle() const {
        if (featured_ == nullptr) {
            return "No recipe selected";
        }
        return featured_->title;
    }

private:
    const RecipeCard* featured_ = nullptr;

    friend bool displayPointsTo(
        const KitchenDisplay&,
        const RecipeCard&
    );
};
'''

bad_reference = bad_starter.replace(
    "featured_ = nullptr;",
    "featured_ = &card;",
    1,
)

bad_files = {
    "tests/pointer_public_behavior_fixture.cpp": '''
bool displayPointsTo(
    const KitchenDisplay& display,
    const RecipeCard& card
) {
    return display.featured_ == &card;
}

int main() {
    RecipeCard card{"Soup"};
    KitchenDisplay display;
    display.feature(card);
    return displayPointsTo(display, card) ? 0 : 1;
}
'''
}

bad_report = ValidationReport(
    source="bad fixture",
    exercise_id="pointer_public_behavior_fixture",
    checks=[],
)

validate_structure(
    make_exercise(
        bad_starter,
        bad_reference,
    ),
    bad_report,
    bundled_files=bad_files,
)

bad_status = {
    check.id: check.status
    for check in bad_report.checks
}

assert (
    bad_status[
        "pedagogy.pointer_no_test_hooks"
    ] == "fail"
)


good_starter = '''
#include <string>

struct RecipeCard {
    std::string title;
};

class KitchenDisplay {
public:
    void feature(const RecipeCard& card) {
        featured_ = nullptr;
    }

    std::string featuredTitle() const {
        if (featured_ == nullptr) {
            return "No recipe selected";
        }
        return featured_->title;
    }

private:
    const RecipeCard* featured_ = nullptr;
};
'''

good_reference = good_starter.replace(
    "featured_ = nullptr;",
    "featured_ = &card;",
    1,
)

good_files = {
    "tests/pointer_public_behavior_fixture.cpp": '''
#include <cassert>
#include <iostream>
#include <string>

int main() {
    RecipeCard soup{"Roasted Tomato Soup"};
    std::cerr << "TRACE|CREATE_OBJECT|soup|type=RecipeCard|value=title=Roasted Tomato Soup\\n";

    KitchenDisplay display;
    std::cerr << "TRACE|CREATE_OBJECT|display|type=KitchenDisplay|pointer=featured_\\n";
    std::cerr << "TRACE|SET_NULL|display.featured_|initial selection\\n";

    display.feature(soup);

    const bool initialReadWorked =
        display.featuredTitle() ==
        "Roasted Tomato Soup";

    soup.title = "Tomato Soup - Updated";

    const bool observesOriginal =
        display.featuredTitle() ==
        "Tomato Soup - Updated";

    if (
        initialReadWorked &&
        observesOriginal
    ) {
        std::cerr << "TRACE|BIND_POINTER|display.featured_|soup\\n";
    } else {
        std::cerr << "TRACE|SET_NULL|display.featured_|selection missing\\n";
    }

    assert(initialReadWorked);
    assert(observesOriginal);
    return 0;
}
'''
}

good_report = ValidationReport(
    source="good fixture",
    exercise_id="pointer_public_behavior_fixture",
    checks=[],
)

validate_structure(
    make_exercise(
        good_starter,
        good_reference,
    ),
    good_report,
    bundled_files=good_files,
)

failures = [
    check
    for check in good_report.checks
    if check.status == "fail"
]

assert not failures, (
    "\n".join(
        f"{check.id}: {check.message}"
        for check in failures
    )
)

good_status = {
    check.id: check.status
    for check in good_report.checks
}

assert (
    good_status[
        "pedagogy.pointer_no_test_hooks"
    ] == "pass"
)

assert (
    good_status[
        "artifacts.pointer_trace_shape"
    ] == "pass"
)

assert (
    good_status[
        "difficulty.quality"
    ] == "pass"
)

print(
    "Step 30.5 pointer public-behavior regression test: PASS"
)
