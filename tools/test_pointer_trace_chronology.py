#!/usr/bin/env python3

from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))

from exercise_validator import (
    ValidationReport,
    pointer_trace_chronology_issues,
    validate_structure,
)

generator_source = (
    PROJECT_ROOT / "tools" / "generate_exercise.py"
).read_text(encoding="utf-8")

version = re.search(
    r"^PROMPT_VERSION\s*=\s*(\d+)\s*$",
    generator_source,
    re.MULTILINE,
)

assert version
assert int(version.group(1)) >= 15

for required in [
    "TRACE CHRONOLOGY IS SEMANTIC",
    "artifacts.pointer_trace_chronology",
    "Required teaching order",
]:
    assert required in generator_source, required

exercise = {
    "exercise_schema_version": 1,
    "id": "pointer_trace_chronology_fixture",
    "topic": "pointers",
    "title": "Keep the Arrival Board Updated",
    "difficulty": "easy",
    "type": "fix_code",
    "scenario": (
        "A transit board observes one live shuttle selected by a dispatcher. "
        "The dispatcher may later change that same shuttle's destination."
    ),
    "problem_statement": (
        "ArrivalBoard::watch receives a live Shuttle but currently does not "
        "retain the selected shuttle for later destination reads."
    ),
    "constraints": [
        "Keep the public API unchanged.",
        "The selected Shuttle remains alive.",
        "The board observes at most one Shuttle.",
    ],
    "learning_objective": (
        "Observe one existing live object through a non-owning raw pointer."
    ),
    "instructions": (
        "Correct ArrivalBoard::watch while keeping the existing queries intact."
    ),
    "starter_code": '''
#include <string>

class Shuttle {
public:
    explicit Shuttle(std::string destination)
        : destination_(destination) {}

    void setDestination(const std::string& destination) {
        destination_ = destination;
    }

    const std::string& destination() const {
        return destination_;
    }

private:
    std::string destination_;
};

class ArrivalBoard {
public:
    ArrivalBoard() : watched_(nullptr) {}

    void watch(Shuttle& shuttle) {
        (void)shuttle;
        watched_ = nullptr;
    }

    bool isWatching() const {
        return watched_ != nullptr;
    }

    std::string currentDestination() const {
        return watched_ == nullptr
            ? "No shuttle selected"
            : watched_->destination();
    }

private:
    Shuttle* watched_;
};
''',
    "reference_solution": '''
#include <string>

class Shuttle {
public:
    explicit Shuttle(std::string destination)
        : destination_(destination) {}

    void setDestination(const std::string& destination) {
        destination_ = destination;
    }

    const std::string& destination() const {
        return destination_;
    }

private:
    std::string destination_;
};

class ArrivalBoard {
public:
    ArrivalBoard() : watched_(nullptr) {}

    void watch(Shuttle& shuttle) {
        watched_ = &shuttle;
    }

    bool isWatching() const {
        return watched_ != nullptr;
    }

    std::string currentDestination() const {
        return watched_ == nullptr
            ? "No shuttle selected"
            : watched_->destination();
    }

private:
    Shuttle* watched_;
};
''',
    "expected_concepts": [
        "raw non-owning pointer member",
        "null pointer state",
        "binding to an existing object",
    ],
    "concept_checks": [],
    "hidden_test_file": "tests/pointer_trace_chronology_fixture.cpp",
    "trace_mode": "runtime",
    "hints": [
        "The board observes an existing Shuttle.",
        "The Shuttle stays alive.",
        "The later destination must come from the same Shuttle.",
    ],
    "explanation": (
        "The board retains the identity of the live selected Shuttle."
    ),
    "learner_goal": (
        "Keep showing the selected shuttle's current destination after "
        "the dispatcher changes that same shuttle elsewhere."
    ),
}

bad_files = {
    "tests/pointer_trace_chronology_fixture.cpp": r'''
std::cerr << "TRACE|CREATE_OBJECT|harborLoop|type=Shuttle|value=destination_=Harbor terminal\n";
std::cerr << "TRACE|CREATE_OBJECT|board|type=ArrivalBoard|pointer=watched_\n";
std::cerr << "TRACE|SET_NULL|board.watched_|pointer cleared\n";

board.watch(harborLoop);

harborLoop.setDestination("Museum district");
std::cerr << "TRACE|WRITE_VALUE|harborLoop|value=destination_=Museum district\n";

if (board.isWatching() && board.currentDestination() == "Museum district") {
    std::cerr << "TRACE|BIND_POINTER|board.watched_|harborLoop\n";
} else {
    std::cerr << "TRACE|SET_NULL|board.watched_|pointer cleared\n";
}
'''
}

bad_issues = pointer_trace_chronology_issues(exercise, bad_files)
assert len(bad_issues) == 1
assert (
    "WRITE_VALUE for stack pointee 'harborLoop' appears before its first BIND_POINTER"
    in bad_issues[0]
)

bad_report = ValidationReport(
    source="bad chronology fixture",
    exercise_id=exercise["id"],
    checks=[],
)
validate_structure(exercise, bad_report, bundled_files=bad_files)
bad_status = {check.id: check.status for check in bad_report.checks}
assert bad_status["artifacts.pointer_trace_chronology"] == "fail"

good_files = {
    "tests/pointer_trace_chronology_fixture.cpp": r'''
std::cerr << "TRACE|CREATE_OBJECT|harborLoop|type=Shuttle|value=destination_=Harbor terminal\n";
std::cerr << "TRACE|CREATE_OBJECT|board|type=ArrivalBoard|pointer=watched_\n";
std::cerr << "TRACE|SET_NULL|board.watched_|pointer cleared\n";

board.watch(harborLoop);

const bool watchingWorked =
    board.isWatching() &&
    board.currentDestination() == "Harbor terminal";

if (watchingWorked) {
    std::cerr << "TRACE|BIND_POINTER|board.watched_|harborLoop\n";
} else {
    std::cerr << "TRACE|SET_NULL|board.watched_|pointer cleared\n";
}

assert(watchingWorked);

harborLoop.setDestination("Museum district");
std::cerr << "TRACE|WRITE_VALUE|harborLoop|value=destination_=Museum district\n";

assert(board.currentDestination() == "Museum district");
'''
}

assert pointer_trace_chronology_issues(exercise, good_files) == []

good_report = ValidationReport(
    source="good chronology fixture",
    exercise_id=exercise["id"],
    checks=[],
)
validate_structure(exercise, good_report, bundled_files=good_files)
failures = [check for check in good_report.checks if check.status == "fail"]
assert not failures, "\n".join(
    f"{check.id}: {check.message}"
    for check in failures
)
good_status = {check.id: check.status for check in good_report.checks}
assert good_status["artifacts.pointer_trace_chronology"] == "pass"
assert good_status["difficulty.quality"] == "pass"

print("Step 30.6.2 pointer trace-chronology regression test: PASS")
