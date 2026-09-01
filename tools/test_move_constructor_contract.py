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

from exercise_validator import move_difficulty_evidence


analyzer = (
    PROJECT_ROOT /
    "src" /
    "Analyzer.cpp"
).read_text(
    encoding="utf-8"
)

generator = (
    PROJECT_ROOT /
    "tools" /
    "generate_exercise.py"
).read_text(
    encoding="utf-8"
)


move_branch_match = re.search(
    r"""const std::string requiredType =
            spec\.className \+ " &&";

        const json\* constructorNode =
            findUserDeclaredConstructorWithParameterType\(
                \*classNode,
                spec\.className,
                requiredType,
                (true|false)
            \);""",
    analyzer,
)

assert move_branch_match, (
    "Could not locate move_constructor analyzer branch."
)

assert move_branch_match.group(1) == "false", (
    "move_constructor must not require noexcept. "
    "noexcept is a separate difficulty invariant."
)

assert (
    "User-declared noexcept move constructor" not in analyzer
), (
    "Analyzer result text still incorrectly defines "
    "move_constructor as noexcept-only."
)

assert (
    "User-declared move constructor" in analyzer
), "Updated move_constructor result text is missing."

prompt_version_match = re.search(
    r"^PROMPT_VERSION\s*=\s*(\d+)\s*$",
    generator,
    re.MULTILINE,
)

assert prompt_version_match, (
    "Could not read generator prompt version."
)

assert int(prompt_version_match.group(1)) >= 7, (
    "Move-constructor contract requires prompt version 7 or newer."
)

expected_guidance = (
    '"move_constructor": '
    '"field: class; detects a user-declared T(T&&) move constructor; '
    'noexcept is a separate difficulty invariant",'
)

assert expected_guidance in generator, (
    "Generator guidance must explain that noexcept is "
    "separate from the move_constructor concept check."
)

base_exercise = {
    "topic": "move_semantics",
    "difficulty": "easy",
    "scenario": "A report is handed to an archive.",
    "problem_statement": (
        "After archive returns, the source report must be empty."
    ),
    "learning_objective": (
        "Implement a move constructor and leave the source empty."
    ),
    "constraints": [],
    "starter_code": """
class FieldReport
{
public:
    FieldReport(FieldReport&& source)
        : text_(source.text_)
    {
    }
private:
    Text text_;
};
""",
    "reference_solution": """
class FieldReport
{
public:
    FieldReport(FieldReport&& source)
        : text_(std::move(source.text_))
    {
        source.clear();
    }
private:
    Text text_;
};
""",
    "concept_checks": [
        {
            "type": "move_constructor",
            "class": "FieldReport",
        }
    ],
}

hidden = """
const bool sourceIsEmpty = deliveredReport.empty();
"""

evidence = move_difficulty_evidence(
    base_exercise,
    {
        "tests/field_report_tests.cpp": hidden,
    },
)

assert evidence["move_constructor_check"] is True
assert evidence["moved_from_state"] is True
assert evidence["noexcept_move"] is False
assert evidence["advanced_invariants"] == 1, evidence

with_noexcept = dict(base_exercise)
with_noexcept["reference_solution"] = (
    base_exercise["reference_solution"].replace(
        "FieldReport(FieldReport&& source)",
        "FieldReport(FieldReport&& source) noexcept",
    )
)

noexcept_evidence = move_difficulty_evidence(
    with_noexcept,
    {
        "tests/field_report_tests.cpp": hidden,
    },
)

assert noexcept_evidence["noexcept_move"] is True
assert noexcept_evidence["advanced_invariants"] == 2, noexcept_evidence

# Step 30.8.0: class-member std::move initializers use the learner-class AST.
for required in [
    "std::string astDumpFilterName(const Exercise& exercise)",
    "findMemberInitializerContainingStdMove(",
    "actualArgument == expectedArgument",
    "CXXCtorInitializer",
    "Member initializer for '",
]:
    assert required in analyzer, required

assert "needsMainFunctionFilter" not in analyzer

print(
    "Step 30.8.0 move-constructor semantic contract test: PASS"
)
