#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

sys.path.insert(0, str(ROOT / "tools"))
import exercise_validator as module

candidate = json.loads(
    (
        ROOT
        / "candidates/generated/ai_raii_scope_20260825_084030_ac7a49.json"
    ).read_text(encoding="utf-8")
)
exercise = candidate["exercise"]
files = candidate["files"]

assert module.raii_exact_sequence_grading_issues(exercise, files) == []

hidden = files[exercise["hidden_test_file"]]
for required in [
    "eventIndex(",
    "requireBefore(",
    "close:calibrationConsole",
    "review:securityOverride->eveningBrief",
    "close:securityOverride",
    "render:projectionRig->eveningBrief",
    "close:projectionRig",
    "announce:eveningBrief",
]:
    assert required in hidden, required

bad_files = dict(files)
bad_files[exercise["hidden_test_file"]] = r'''
#include <string>
#include <vector>
int main() {
    const std::vector<std::string> expected = {
        "open:a",
        "close:a"
    };
    if (museumAudit() != expected) {
        return 2;
    }
    return 0;
}
'''
assert module.raii_exact_sequence_grading_issues(exercise, bad_files)

generator = (ROOT / "tools/generate_exercise.py").read_text(encoding="utf-8")
prompt_version_match = re.search(
    r"^PROMPT_VERSION\s*=\s*(\d+)\s*$",
    generator,
    flags=re.MULTILINE,
)
assert prompt_version_match is not None
assert int(prompt_version_match.group(1)) >= 17
assert "RAII/scope-topic rules" in generator
assert "artifacts.raii_grading_equivalence" in generator
validator = (ROOT / "tools/exercise_validator.py").read_text(encoding="utf-8")
assert "prompt_version >= 17" in validator
assert "Legacy candidate warning" in validator


# Regression: Step 30.7.0 must not shadow the existing two-argument
# hidden_artifact_text() helper used by Move/Pointers/trace checks.
validator_text = (
    ROOT / "tools/exercise_validator.py"
).read_text(encoding="utf-8")

assert validator_text.count("def hidden_artifact_text(") == 1
assert "def raii_hidden_test_text(" in validator_text

# Existing helper must still accept exactly the original two arguments.
combined = module.hidden_artifact_text(
    exercise,
    files,
)
assert isinstance(combined, str)
assert "TRACE|" in combined

# RAII-specific lookup must return only the hidden test artifact.
raii_hidden = module.raii_hidden_test_text(
    exercise,
    files,
)
assert raii_hidden == files[exercise["hidden_test_file"]]


# Step 30.7.3: exact whole-vector grading behind a support helper
# must also be rejected.
helper_indirect_files = dict(files)
helper_indirect_files[exercise["hidden_test_file"]] = r"""
#include <string>
#include <vector>
int main() {
    const std::vector<std::string> expected = {
        "open:a",
        "use:a",
        "close:a"
    };
    if (!auditMatches(expected)) {
        return 2;
    }
    return 0;
}
"""
helper_indirect_files[exercise["support_file"]] = r"""
#include <string>
#include <vector>
inline std::vector<std::string>& audit() {
    static std::vector<std::string> events;
    return events;
}
inline bool auditMatches(
    const std::vector<std::string>& expected) {
    return audit() == expected;
}
"""
helper_indirect_issues = module.raii_exact_sequence_grading_issues(
    exercise,
    helper_indirect_files,
)
assert helper_indirect_issues


# Step 30.7.6: an unused legacy exact-match helper in support is not grading.
unused_helper_files = dict(files)
unused_helper_files[exercise["hidden_test_file"]] = r"""
#include <string>
#include <vector>
int main() {
    const std::vector<std::string> required = {
        "open:a",
        "use:a",
        "close:a"
    };
    for (const std::string& event : required) {
        (void)event;
    }
    return 0;
}
"""
unused_helper_files[exercise["support_file"]] = r"""
#include <string>
#include <vector>
inline std::vector<std::string>& audit() {
    static std::vector<std::string> events;
    return events;
}
inline bool auditMatches(
    const std::vector<std::string>& expected) {
    return audit() == expected;
}
"""
assert module.raii_exact_sequence_grading_issues(
    exercise,
    unused_helper_files,
) == []

print("Step 30.9.0 RAII grading-equivalence regression: PASS")
