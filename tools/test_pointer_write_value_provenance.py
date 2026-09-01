#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from exercise_validator import (
    ValidationReport,
    pointer_write_value_provenance_issues,
    validate_structure,
)
from generate_exercise import normalize_hidden_runtime_artifact

source = (ROOT / "tools" / "generate_exercise.py").read_text(encoding="utf-8")
version = re.search(r"^PROMPT_VERSION\s*=\s*(\d+)\s*$", source, re.MULTILINE)
assert version and int(version.group(1)) >= 16

for required in [
    "artifacts.pointer_write_value_provenance",
    "ordinary local raw pointer variable",
    "omit via= entirely",
]:
    assert required in source, required

exercise = {
    "topic": "pointers",
    "hidden_test_file": "tests/provenance.cpp",
}

bad = {
    "tests/provenance.cpp": r'''\
std::cerr << "TRACE|ALLOCATE_RESOURCE|resource#2|value=code_=CR-18,priority_=4\n";
replacement->rename("CR-18B");
std::cerr << "TRACE|WRITE_VALUE|resource#2|via=replacement|value=code_=CR-18B,priority_=4\n";
'''
}
issues = pointer_write_value_provenance_issues(exercise, bad)
assert len(issues) == 1
assert "via='replacement'" in issues[0]

good_scope = {
    "tests/provenance.cpp": r'''\
std::cerr << "TRACE|ENTER_SCOPE|rename|\n";
std::cerr << "TRACE|WRITE_VALUE|resource#2|via=rename|value=code_=CR-18B,priority_=4\n";
std::cerr << "TRACE|EXIT_SCOPE|rename|\n";
'''
}
assert pointer_write_value_provenance_issues(exercise, good_scope) == []

normalized = normalize_hidden_runtime_artifact(
    r'''\
std::cerr << "TRACE|ENTER_SCOPE|rename|\n";
std::cerr << "TRACE|WRITE_VALUE|resource#1|via=rename|value=x=1\n";
std::cerr << "TRACE|WRITE_VALUE|resource#2|via=replacement|value=x=2\n";
std::cerr << "TRACE|WRITE_VALUE|resource#3|value=x=3|through=console.active_\n";
''',
    "pointers",
)
assert "via=rename" in normalized
assert "via=replacement" not in normalized
assert "TRACE|WRITE_VALUE|resource#2|value=x=2" in normalized
assert "through=console.active_" in normalized

candidate_path = ROOT / "candidates" / "generated" / "ai_pointers_20260827_101013_80fcb9.json"
candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
hidden_path = candidate["exercise"]["hidden_test_file"]
hidden = candidate["files"][hidden_path]
assert "via=replacement" not in hidden
assert "TRACE|WRITE_VALUE|resource#2|value=code_=CR-18B,priority_=4" in hidden
assert pointer_write_value_provenance_issues(candidate["exercise"], candidate["files"]) == []

report = ValidationReport(
    source=str(candidate_path),
    exercise_id=candidate["exercise"]["id"],
    checks=[],
)
validate_structure(
    candidate["exercise"],
    report,
    bundled_files=candidate["files"],
)
failures = [c for c in report.checks if c.status == "fail"]
assert not failures, "\n".join(f"{c.id}: {c.message}" for c in failures)
status = {c.id: c.status for c in report.checks}
assert status["artifacts.pointer_write_value_provenance"] == "pass"
assert status["difficulty.quality"] == "pass"

print("Step 30.6.5 pointer WRITE_VALUE provenance regression: PASS")
