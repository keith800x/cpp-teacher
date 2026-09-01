#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from exercise_validator import (
    difficulty_quality_result,
    pointer_trace_shape_issues,
)

exercise = {
    "topic": "pointers",
    "difficulty": "easy",
    "starter_code": (
        "struct Sighting {}; "
        "class Console { const Sighting* selected_ = nullptr; };"
    ),
    "reference_solution": (
        "struct Sighting {}; "
        "class Console { const Sighting* selected_ = nullptr; };"
    ),
    "hidden_test_file": "tests/native_pointer_target.cpp",
}

stack_files = {
    "tests/native_pointer_target.cpp": r'''
std::cerr << "TRACE|CREATE_OBJECT|riverSighting|type=Sighting|value=animal=otter\n";
std::cerr << "TRACE|CREATE_OBJECT|console|type=Console|pointer=selected_\n";
std::cerr << "TRACE|SET_NULL|console.selected_|initial\n";
std::cerr << "TRACE|BIND_POINTER|console.selected_|riverSighting\n";
'''
}

assert pointer_trace_shape_issues(exercise, stack_files) == []

valid, detail, evidence = difficulty_quality_result(
    exercise,
    stack_files,
)

assert valid, detail
assert evidence["pointer_targets"] == 1
assert evidence["pointer_resources"] == 0

heap_files = {
    "tests/native_pointer_target.cpp": r'''
std::cerr << "TRACE|CREATE_OBJECT|console|type=Console|pointer=selected_\n";
std::cerr << "TRACE|ALLOCATE_RESOURCE|resource#1|value=animal=otter\n";
std::cerr << "TRACE|BIND_POINTER|console.selected_|resource#1\n";
'''
}

assert pointer_trace_shape_issues(exercise, heap_files) == []

unknown_files = {
    "tests/native_pointer_target.cpp": r'''
std::cerr << "TRACE|CREATE_OBJECT|console|type=Console|pointer=selected_\n";
std::cerr << "TRACE|BIND_POINTER|console.selected_|missingSighting\n";
'''
}

issues = pointer_trace_shape_issues(
    exercise,
    unknown_files,
)

assert any(
    "stack object created by CREATE_OBJECT" in issue
    for issue in issues
)

print("Step 30.4 native pointer-target regression test: PASS")
