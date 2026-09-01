#!/usr/bin/env python3

from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(ROOT / "tools"),
)

from exercise_validator import (
    cpp_source_safety_issues,
    difficulty_quality_result,
)


CANDIDATE_ID = "ai_move_semantics_20260828_130937_6f2161"

candidate = json.loads(
    (
        ROOT /
        "candidates/generated" /
        f"{CANDIDATE_ID}.json"
    ).read_text(
        encoding="utf-8"
    )
)

exercise = candidate["exercise"]
files = candidate["files"]

assert exercise["topic"] == "move_semantics"
assert exercise["difficulty"] == "medium"

# Learner-visible code must never expose hidden project support.
for field in [
    "starter_code",
    "reference_solution",
]:
    source = exercise[field]

    assert (
        '#include "support/' not in
        source
    )

    assert not re.search(
        r'(?m)^\s*#\s*include\s*"',
        source,
    )

    assert not cpp_source_safety_issues(
        source
    ), (
        field,
        cpp_source_safety_issues(
            source
        ),
    )

# Hidden support remains available and a hidden analysis-only copy is present.
support_path = exercise[
    "support_file"
]

analysis_path = exercise[
    "analysis_support_file"
]

assert support_path in files
assert analysis_path in files
assert files[analysis_path] == files[support_path]

# This Medium task naturally carries exactly three recognized ownership
# invariants: noexcept, stable resource identity, and moved-from emptiness.
valid, detail, evidence = (
    difficulty_quality_result(
        exercise,
        files,
    )
)

assert valid, (
    detail,
    evidence,
)

assert evidence[
    "move_constructor_check"
]

assert evidence[
    "noexcept_move"
]

assert evidence[
    "resource_identity"
]

assert evidence[
    "moved_from_state"
]

assert not evidence[
    "exclusive_ownership"
]

assert not evidence[
    "no_duplicate_allocation"
]

assert evidence[
    "advanced_invariants"
] == 3, evidence

# The source text really expresses identity preservation; this is not
# expected_concepts padding.
metadata = "\n".join(
    [
        exercise[
            "problem_statement"
        ],
        *exercise[
            "constraints"
        ],
    ]
).lower()

assert (
    "original crate" in metadata
    or "original crate token" in metadata
)

assert (
    "ledger token" in metadata
)

hidden = files[
    exercise[
        "hidden_test_file"
    ]
]

assert "crateToken() == 71" in hidden
assert "ledgerToken() == 19" in hidden
assert "!intakeTransfer.hasCrate()" in hidden
assert "!intakeTransfer.hasLedger()" in hidden

# Generator regression: quoted includes are stripped deterministically and
# Move support receives hidden analysis support when needed.
generator_path = (
    ROOT /
    "tools/generate_exercise.py"
)

generator_source = generator_path.read_text(
    encoding="utf-8"
)

for required in [
    "PROMPT_VERSION = 18",
    "def strip_generated_quoted_includes(",
    "GENERATED_QUOTED_INCLUDE_LINE_PATTERN",
    "learner_source_field",
    'topic == "move_semantics"',
    "Reuse it only for hidden AST",
    "For Medium Move Semantics",
]:
    assert required in generator_source, required

# Execute just the include stripping helper.
tree = ast.parse(
    generator_source,
    filename=str(generator_path),
)

wanted = {
    "strip_generated_quoted_includes",
}

selected = [
    node
    for node in tree.body
    if (
        isinstance(
            node,
            ast.FunctionDef,
        ) and
        node.name in wanted
    )
]

pattern_assign = next(
    node
    for node in tree.body
    if (
        isinstance(
            node,
            ast.Assign,
        ) and
        any(
            isinstance(
                target,
                ast.Name,
            ) and
            target.id ==
                "GENERATED_QUOTED_INCLUDE_LINE_PATTERN"
            for target in node.targets
        )
    )
)

module = ast.Module(
    body=[
        pattern_assign,
        *selected,
    ],
    type_ignores=[],
)

ast.fix_missing_locations(
    module
)

namespace = {
    "re": re,
}

exec(
    compile(
        module,
        str(generator_path),
        "exec",
    ),
    namespace,
)

strip = namespace[
    "strip_generated_quoted_includes"
]

probe = (
    '#include <utility>\n'
    '#include "support/private.hpp"\n'
    '\n'
    'class Probe {};\n'
)

cleaned = strip(
    probe
)

assert "#include <utility>" in cleaned
assert "support/private.hpp" not in cleaned
assert "class Probe" in cleaned

# Behavioral smoke: runtime grader assembly is support + learner + hidden.
compiler = (
    shutil.which("g++") or
    shutil.which("clang++")
)

if compiler:
    def compile_run(
        name: str,
        learner_source: str,
    ):
        with tempfile.TemporaryDirectory(
            prefix=f"cpp_teacher_{name}_"
        ) as temp_dir:
            temp = Path(temp_dir)
            source = temp / f"{name}.cpp"
            executable = temp / name

            source.write_text(
                files[
                    support_path
                ] +
                "\n" +
                learner_source +
                "\n" +
                hidden,
                encoding="utf-8",
            )

            built = subprocess.run(
                [
                    compiler,
                    "-std=c++20",
                    str(source),
                    "-o",
                    str(executable),
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            assert built.returncode == 0, (
                built.stderr
            )

            return subprocess.run(
                [
                    str(executable)
                ],
                text=True,
                capture_output=True,
                check=False,
            )

    reference = compile_run(
        "move_medium_reference",
        exercise[
            "reference_solution"
        ],
    )

    starter = compile_run(
        "move_medium_starter",
        exercise[
            "starter_code"
        ],
    )

    assert reference.returncode == 0, (
        reference.stderr
    )

    assert starter.returncode != 0, (
        "Broken Medium Move starter unexpectedly passed."
    )

print(
    "Step 30.9.0 Move Medium candidate-normalization regression: PASS"
)
