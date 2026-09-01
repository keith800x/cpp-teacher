#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from exercise_validator import (
    difficulty_quality_result,
    pointer_difficulty_evidence,
)

topics = json.loads(
    (PROJECT_ROOT / "catalog" / "topics.json").read_text(
        encoding="utf-8"
    )
)

topic_ids = {
    item["id"]
    for item in topics["topics"]
}

assert "pointers" in topic_ids

profiles = json.loads(
    (
        PROJECT_ROOT /
        "catalog" /
        "difficulty_profiles.json"
    ).read_text(
        encoding="utf-8"
    )
)

assert "pointers" in profiles["topics"]

generator_source = (
    PROJECT_ROOT /
    "tools" /
    "generate_exercise.py"
).read_text(
    encoding="utf-8"
)

prompt_version_match = re.search(
    r"^PROMPT_VERSION\s*=\s*(\d+)\s*$",
    generator_source,
    re.MULTILINE,
)

assert prompt_version_match
assert int(
    prompt_version_match.group(
        1
    )
) >= 8
assert "Pointer-topic rules (topic=pointers only):" in generator_source
assert "TRACE|SET_NULL|object.field_|pointer cleared" in generator_source
assert "through=object.field_" in generator_source

state_builder_source = (
    PROJECT_ROOT /
    "src" /
    "MemoryStateBuilder.cpp"
).read_text(
    encoding="utf-8"
)

assert "resources.find(event.subject)" in state_builder_source
assert "resourceIt->second.value" in state_builder_source


def exercise(
    difficulty: str,
    starter: str,
    reference: str,
) -> dict:
    return {
        "topic": "pointers",
        "difficulty": difficulty,
        "starter_code": starter,
        "reference_solution": reference,
        "scenario": "A domain object observes caller-owned state.",
        "problem_statement": "Repair the pointer behavior.",
        "learning_objective": "Reason about a raw pointer and its pointee.",
        "constraints": [],
        "concept_checks": [],
    }


easy = exercise(
    "easy",
    '''
class Gauge {
public:
    Reading* current_;
};
''',
    '''
class Gauge {
public:
    Reading* current_;
};
''',
)

easy_hidden = {
    "tests/easy.cpp": r'''
std::fprintf(stderr, "TRACE|CREATE_OBJECT|gauge|type=Gauge|pointer=current_\n");
std::fprintf(stderr, "TRACE|ALLOCATE_RESOURCE|resource#1|value=level=8\n");
std::fprintf(stderr, "TRACE|BIND_POINTER|gauge.current_|resource#1\n");
std::fprintf(stderr, "TRACE|ENTER_SCOPE|adjustReading|update reading\n");
std::fprintf(stderr, "TRACE|WRITE_VALUE|resource#1|via=adjustReading|through=gauge.current_|value=level=9\n");
std::fprintf(stderr, "TRACE|EXIT_SCOPE|adjustReading|done\n");
'''
}

easy_evidence = pointer_difficulty_evidence(
    easy,
    easy_hidden,
)

assert easy_evidence["pointer_decisions"] == 2, easy_evidence
assert easy_evidence["pointer_subjects"] == 1
assert easy_evidence["writable_pointer_paths"] == 1
assert easy_evidence["aliasing"] is False
assert easy_evidence["lifetime_boundary"] is False

valid, detail, _ = difficulty_quality_result(
    easy,
    easy_hidden,
)

assert valid, detail


medium = exercise(
    "medium",
    '''
class RouteSelector {
public:
    Route* current_;
};
''',
    '''
class RouteSelector {
public:
    Route* current_;
};
''',
)

medium_hidden = {
    "tests/medium.cpp": r'''
std::fprintf(stderr, "TRACE|CREATE_OBJECT|selector|type=RouteSelector|pointer=current_\n");
std::fprintf(stderr, "TRACE|ALLOCATE_RESOURCE|resource#1|value=north\n");
std::fprintf(stderr, "TRACE|ALLOCATE_RESOURCE|resource#2|value=south\n");
std::fprintf(stderr, "TRACE|BIND_POINTER|selector.current_|resource#1\n");
std::fprintf(stderr, "TRACE|SET_NULL|selector.current_|no active route\n");
std::fprintf(stderr, "TRACE|BIND_POINTER|selector.current_|resource#2\n");
std::fprintf(stderr, "TRACE|ENTER_SCOPE|renameRoute|rename selected route\n");
std::fprintf(stderr, "TRACE|WRITE_VALUE|resource#2|via=renameRoute|through=selector.current_|value=south-express\n");
std::fprintf(stderr, "TRACE|EXIT_SCOPE|renameRoute|done\n");
'''
}

medium_evidence = pointer_difficulty_evidence(
    medium,
    medium_hidden,
)

assert medium_evidence["pointer_decisions"] == 4, medium_evidence
assert medium_evidence["null_state"] is True
assert medium_evidence["reseating"] is True
assert medium_evidence["write_through"] is True
assert medium_evidence["lifetime_boundary"] is False

valid, detail, _ = difficulty_quality_result(
    medium,
    medium_hidden,
)

assert valid, detail


hard = exercise(
    "hard",
    '''
class PrimaryView {
public:
    Sensor* target_;
};

class MirrorView {
public:
    Sensor* target_;
};
''',
    '''
class PrimaryView {
public:
    Sensor* target_;
};

class MirrorView {
public:
    Sensor* target_;
};
''',
)

hard_hidden = {
    "tests/hard.cpp": r'''
std::fprintf(stderr, "TRACE|CREATE_OBJECT|primaryView|type=PrimaryView|pointer=target_\n");
std::fprintf(stderr, "TRACE|CREATE_OBJECT|mirrorView|type=MirrorView|pointer=target_\n");
std::fprintf(stderr, "TRACE|ALLOCATE_RESOURCE|resource#1|value=temperature=70\n");
std::fprintf(stderr, "TRACE|BIND_POINTER|primaryView.target_|resource#1\n");
std::fprintf(stderr, "TRACE|BIND_POINTER|mirrorView.target_|resource#1\n");
std::fprintf(stderr, "TRACE|ENTER_SCOPE|adjustSensor|adjust through primary\n");
std::fprintf(stderr, "TRACE|WRITE_VALUE|resource#1|via=adjustSensor|through=primaryView.target_|value=temperature=71\n");
std::fprintf(stderr, "TRACE|EXIT_SCOPE|adjustSensor|done\n");
std::fprintf(stderr, "TRACE|FREE_RESOURCE|resource#1|sensor lifetime ended\n");
std::fprintf(stderr, "TRACE|SET_NULL|primaryView.target_|pointee ended\n");
std::fprintf(stderr, "TRACE|SET_NULL|mirrorView.target_|pointee ended\n");
'''
}

hard_evidence = pointer_difficulty_evidence(
    hard,
    hard_hidden,
)

assert hard_evidence["pointer_decisions"] == 6, hard_evidence
assert hard_evidence["pointer_subjects"] == 2
assert hard_evidence["pointer_holder_objects"] == 2
assert hard_evidence["aliasing"] is True
assert hard_evidence["write_through"] is True
assert hard_evidence["lifetime_boundary"] is True
assert hard_evidence["null_state"] is True

valid, detail, _ = difficulty_quality_result(
    hard,
    hard_hidden,
)

assert valid, detail

hard_as_medium = dict(hard)
hard_as_medium["difficulty"] = "medium"

valid, _, _ = difficulty_quality_result(
    hard_as_medium,
    hard_hidden,
)

assert not valid

print("Step 30.0 Pointers foundation regression test: PASS")
