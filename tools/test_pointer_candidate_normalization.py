#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(PROJECT_ROOT / "tools")
)

from generate_exercise import (
    normalize_concept_checks,
    normalize_draft,
)


pointer_exercise = {
    "concept_checks": [
        {
            "type": "const_reference_parameter",
            "function": "RangerConsole::highlight",
            "parameter": "sighting",
        },
        {
            "type": "move_constructor",
            "class": "RangerConsole",
        },
    ]
}

assert normalize_concept_checks(
    pointer_exercise,
    "pointers"
) == []


references_exercise = {
    "concept_checks": [
        {
            "type": "non_const_reference_parameter",
            "function": "updateCount",
            "parameter": "count",
            "variable": "",
            "argument": "",
            "class": "",
        }
    ]
}

reference_checks = normalize_concept_checks(
    references_exercise,
    "references"
)

assert reference_checks == [
    {
        "type": "non_const_reference_parameter",
        "function": "updateCount",
        "parameter": "count",
    }
]


draft = {
    "exercise": {
        "exercise_schema_version": 1,
        "id": "placeholder",
        "topic": "pointers",
        "title": "Keep the Ranger Console on the Selected Sighting",
        "difficulty": "easy",
        "type": "fix_code",
        "scenario": (
            "A ranger console observes a sighting that remains alive "
            "throughout the review."
        ),
        "problem_statement": (
            "RangerConsole::highlight receives a live Sighting, but "
            "highlightedAnimal still reports no selection."
        ),
        "constraints": [
            "Keep the public API unchanged.",
            "The console does not own the sighting.",
        ],
        "learning_objective": (
            "Store one non-owning raw pointer to an existing live object."
        ),
        "learner_goal": (
            "Keep the console on the selected sighting."
        ),
        "instructions": (
            "Modify the existing implementation only."
        ),
        "starter_code": (
            "struct Sighting{}; "
            "class RangerConsole { "
            "const Sighting* highlighted_ = nullptr; "
            "};"
        ),
        "reference_solution": (
            "struct Sighting{}; "
            "class RangerConsole { "
            "const Sighting* highlighted_ = nullptr; "
            "};"
        ),
        "expected_concepts": [
            "non-owning raw pointer",
        ],
        # Deliberately reproduce the exact metadata problem from
        # the Ranger repair. The normalizer must erase it.
        "concept_checks": [
            {
                "type": "const_reference_parameter",
                "function": "RangerConsole::highlight",
                "parameter": "sighting",
            }
        ],
        "hidden_test_file": "ignored.cpp",
        "trace_mode": "runtime",
        "hints": [
            "The console only observes the object.",
        ],
        "explanation": (
            "The pointer does not own the selected sighting."
        ),
    },
    "artifacts": [
        {
            "kind": "hidden_test",
            "path": "ignored.cpp",
            "content": (
                '#include <iostream>\n'
                'int main() {\n'
                '  std::cerr << '
                '"TRACE|CREATE_OBJECT|console|type=RangerConsole|'
                'pointer=highlighted_\\\\n";\n'
                '  std::cerr << '
                '"TRACE|ALLOCATE_RESOURCE|resource#1|value=animal=otter\\\\n";\n'
                '  std::cerr << '
                '"TRACE|BIND_POINTER|console.highlighted_|resource#1\\\\n";\n'
                '  return 0;\n'
                '}\n'
            ),
        }
    ],
}

candidate = normalize_draft(
    draft=draft,
    exercise_id="ai_pointers_normalization_test",
    topic="pointers",
    difficulty="easy",
    model="test-model",
    response_id="resp_test",
    generation_attempt=10,
)

assert candidate["exercise"]["topic"] == "pointers"
assert candidate["exercise"]["concept_checks"] == []

assert (
    candidate["exercise"]["hidden_test_file"]
    == "tests/ai_pointers_normalization_test_tests.cpp"
)

# Ensure the generated candidate metadata still reports the current
# prompt version rather than mutating an unrelated contract.
assert (
    candidate["generation_metadata"]["prompt_version"]
    >= 10
)

source = (
    PROJECT_ROOT /
    "tools" /
    "generate_exercise.py"
).read_text(
    encoding="utf-8"
)

assert 'if topic == "pointers":' in source
assert 'return []' in source
assert "normalize_concept_checks(" in source

print(
    "Step 30.3 pointer candidate-normalization regression test: PASS"
)
