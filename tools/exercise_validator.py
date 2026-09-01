#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parents[1]

CPP_TEACHER_PATH = (
    PROJECT_ROOT /
    "build" /
    "cpp_teacher"
)

TOPICS_PATH = (
    PROJECT_ROOT /
    "catalog" /
    "topics.json"
)

DIFFICULTY_PROFILES_PATH = (
    PROJECT_ROOT /
    "catalog" /
    "difficulty_profiles.json"
)

LIBRARY_PATH = (
    PROJECT_ROOT /
    "catalog" /
    "exercise_library.json"
)

OUTPUT_DIRECTORY = (
    PROJECT_ROOT /
    "output"
)

WORKSPACE_DIRECTORY = (
    PROJECT_ROOT /
    ".validator_workspace"
)

VALID_DIFFICULTIES = {
    "easy",
    "medium",
    "hard",
}

VALID_EXERCISE_TYPES = {
    "fix_code",
    "implement_code",
    "debug_code",
}

VALID_TRACE_MODES = {
    "runtime",
    "runtime_derived_raii",
    "source_pattern",
}

CONCEPT_CHECK_REQUIREMENTS = {
    "non_const_reference_parameter": {
        "function",
        "parameter",
    },
    "const_reference_parameter": {
        "function",
        "parameter",
    },
    "non_const_reference_variable": {
        "variable",
        "argument",
    },
    "const_reference_variable": {
        "variable",
        "argument",
    },
    "std_move_initializer": {
        "variable",
        "argument",
    },
    "virtual_destructor": {
        "class",
    },
    "copy_constructor": {
        "class",
    },
    "move_constructor": {
        "class",
    },
}

PUBLIC_FORBIDDEN_PATTERNS = [
    (
        re.compile(
            r"\bScopeMarker\b",
            re.IGNORECASE
        ),
        "ScopeMarker"
    ),
    (
        re.compile(
            r"\bTrackedResource\b",
            re.IGNORECASE
        ),
        "TrackedResource"
    ),
    (
        re.compile(
            r"\btrace[A-Za-z0-9_]*\s*\(",
            re.IGNORECASE
        ),
        "trace helper call"
    ),
    (
        re.compile(
            r"\bRuntimeTrace[A-Za-z0-9_]*\b",
            re.IGNORECASE
        ),
        "runtime-trace implementation type"
    ),
    (
        re.compile(
            r"\bMemoryTimeline[A-Za-z0-9_]*\b",
            re.IGNORECASE
        ),
        "memory-timeline implementation type"
    ),
    (
        re.compile(
            r"\bhidden[_ -]?test\b",
            re.IGNORECASE
        ),
        "hidden-test implementation wording"
    ),
    (
        re.compile(
            r"\bgrader\b",
            re.IGNORECASE
        ),
        "grader implementation wording"
    ),
]

POINTER_LEARNER_TEST_HOOK_PATTERNS = [
    (
        re.compile(
            r"\bfriend\b"
        ),
        "friend declaration"
    ),
]


LEARNER_GOAL_SOLUTION_PATTERNS = [
    re.compile(r"\bwritable\s+reference\b", re.IGNORECASE),
    re.compile(r"\bconst\s+reference\b", re.IGNORECASE),
    re.compile(r"\breference\s+parameter\b", re.IGNORECASE),
    re.compile(r"\blvalue\s+reference\b", re.IGNORECASE),
    re.compile(r"\bstd::move\b", re.IGNORECASE),
    re.compile(r"\bmove\s+constructor\b", re.IGNORECASE),
    re.compile(r"\bcopy\s+constructor\b", re.IGNORECASE),
    re.compile(r"\bRAII\b", re.IGNORECASE),
    re.compile(r"\bunique_ptr\b", re.IGNORECASE),
    re.compile(r"\bshared_ptr\b", re.IGNORECASE),
    re.compile(r"\bweak_ptr\b", re.IGNORECASE),
]


def starter_code_identifiers(source: str) -> list[str]:
    if not isinstance(source, str):
        return []

    names = set(
        re.findall(
            r"\b(?:class|struct)\s+([A-Za-z_]\w*)",
            source
        )
    )

    for match in re.finditer(
        r"(?m)^\s*(?:[A-Za-z_][\w:<>,*&\s]*?)\s+([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:const\s*)?(?:noexcept\s*)?\{",
        source
    ):
        name = match.group(1)
        if name not in {"if", "for", "while", "switch", "catch"}:
            names.add(name)

    return sorted(names)


DIRECT_SOLUTION_HINT_PATTERNS = [
    re.compile(
        r"std::move\s*\(",
        re.IGNORECASE
    ),
    re.compile(
        r"\badd\s+(?:an?\s+)?&",
        re.IGNORECASE
    ),
    re.compile(
        r"\buse\s+int\s*&",
        re.IGNORECASE
    ),
    re.compile(
        r"\buse\s+const\s+[^.]{0,30}&",
        re.IGNORECASE
    ),
]


ALLOWED_CPP_HEADERS = {
    "algorithm", "array", "cassert", "cstddef", "cstdint", "cstdio",
    "deque", "functional", "iostream", "limits", "map", "memory",
    "optional", "queue", "stdexcept", "string", "type_traits",
    "unordered_map", "utility", "vector",
}

DANGEROUS_CPP_PATTERNS = [
    (re.compile(r"\b(?:std::)?system\s*\(", re.IGNORECASE), "process execution via system()"),
    (re.compile(r"\b_?popen\s*\(", re.IGNORECASE), "process execution via popen()"),
    (re.compile(r"\b(?:fork|vfork)\s*\(", re.IGNORECASE), "process creation"),
    (re.compile(r"\bexec(?:l|le|lp|lpe|v|ve|vp|vpe)?\s*\(", re.IGNORECASE), "exec-family process execution"),
    (re.compile(r"\b(?:CreateProcess|WinExec|ShellExecute)\w*\s*\(", re.IGNORECASE), "Windows process execution"),
    (re.compile(r"\b(?:socket|connect|listen|accept|sendto|recvfrom)\s*\(", re.IGNORECASE), "network access"),
    (re.compile(r"\b(?:std::)?filesystem\b", re.IGNORECASE), "filesystem API"),
    (re.compile(r"\b(?:ifstream|ofstream|fstream)\b", re.IGNORECASE), "file stream access"),
    (re.compile(r"\b(?:fopen|freopen|tmpfile)\s*\(", re.IGNORECASE), "C file access"),
    (re.compile(r"(?:/etc/|/proc/|/sys/|/dev/|[A-Za-z]:\\\\)", re.IGNORECASE), "direct operating-system path access"),
]

QUOTED_INCLUDE_PATTERN = re.compile(
    r'^\s*#\s*include\s*"([^"]+)"',
    re.MULTILINE
)

ANGLE_INCLUDE_PATTERN = re.compile(
    r"^\s*#\s*include\s*<([^>]+)>",
    re.MULTILINE
)


def cpp_source_safety_issues(source: str) -> list[str]:
    issues: list[str] = []

    for include in QUOTED_INCLUDE_PATTERN.findall(source):
        issues.append(
            f"quoted project/system include '{include}' is not allowed in generated code"
        )

    for header in ANGLE_INCLUDE_PATTERN.findall(source):
        normalized = header.strip()
        if normalized not in ALLOWED_CPP_HEADERS:
            issues.append(
                f"header <{normalized}> is outside the generated-exercise allowlist"
            )

    for pattern, description in DANGEROUS_CPP_PATTERNS:
        if pattern.search(source):
            issues.append(description)

    return sorted(set(issues))


def candidate_cpp_sources(
    exercise: dict,
    bundled_files: dict[str, str] | None
) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []

    for field in ["starter_code", "reference_solution"]:
        value = exercise.get(field)
        if isinstance(value, str):
            result.append((field, value))

    if bundled_files is not None:
        for path, content in bundled_files.items():
            if isinstance(content, str):
                result.append((path, content))
    else:
        for field in ["hidden_test_file", "support_file", "analysis_support_file"]:
            raw = exercise.get(field)
            if not isinstance(raw, str):
                continue

            path = PROJECT_ROOT / raw
            if not path.exists():
                continue

            try:
                result.append((raw, path.read_text(encoding="utf-8")))
            except OSError:
                pass

    return result


@dataclass
class Check:
    id: str
    category: str
    status: str
    message: str


@dataclass
class ValidationReport:
    source: str
    exercise_id: str
    checks: list[Check]

    @property
    def valid(self) -> bool:
        return not any(
            check.status == "fail"
            for check in self.checks
        )

    @property
    def failures(self) -> int:
        return sum(
            check.status == "fail"
            for check in self.checks
        )

    @property
    def warnings(self) -> int:
        return sum(
            check.status == "warn"
            for check in self.checks
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "validator_version": 2,
            "source": self.source,
            "exercise_id": self.exercise_id,
            "valid": self.valid,
            "failure_count": self.failures,
            "warning_count": self.warnings,
            "checks": [
                asdict(check)
                for check in self.checks
            ],
        }


def add_check(
    report: ValidationReport,
    check_id: str,
    category: str,
    status: str,
    message: str,
):
    report.checks.append(
        Check(
            id=check_id,
            category=category,
            status=status,
            message=message,
        )
    )


def load_json(path: Path) -> dict:
    with path.open(
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(file)

    if not isinstance(
        data,
        dict
    ):
        raise ValueError(
            f"{path} must contain a JSON object."
        )

    return data


def known_topic_ids() -> set[str]:
    data = load_json(
        TOPICS_PATH
    )

    return {
        item["id"]
        for item in
        data.get(
            "topics",
            []
        )
        if isinstance(
            item,
            dict
        ) and isinstance(
            item.get("id"),
            str
        )
    }


def non_empty_string(
    value: Any
) -> bool:
    return (
        isinstance(
            value,
            str
        ) and
        bool(
            value.strip()
        )
    )


def relative_project_path(
    raw_value: Any,
    allowed_prefix: str
) -> Path | None:
    if not non_empty_string(
        raw_value
    ):
        return None

    candidate = Path(
        raw_value
    )

    if candidate.is_absolute():
        return None

    if ".." in candidate.parts:
        return None

    normalized = (
        PROJECT_ROOT /
        candidate
    ).resolve()

    try:
        normalized.relative_to(
            PROJECT_ROOT.resolve()
        )
    except ValueError:
        return None

    if not str(
        candidate.as_posix()
    ).startswith(
        allowed_prefix + "/"
    ):
        return None

    return candidate



def difficulty_profiles() -> dict:
    if not DIFFICULTY_PROFILES_PATH.exists():
        return {}

    try:
        data = load_json(
            DIFFICULTY_PROFILES_PATH
        )
    except (
        OSError,
        ValueError,
        json.JSONDecodeError
    ):
        return {}

    topics = data.get(
        "topics",
        {}
    )

    return (
        topics
        if isinstance(
            topics,
            dict
        )
        else {}
    )


REFERENCE_CHECK_TYPES = {
    "non_const_reference_parameter",
    "const_reference_parameter",
    "non_const_reference_variable",
    "const_reference_variable",
}


def reference_difficulty_evidence(
    exercise: dict
) -> dict:
    checks = [
        check
        for check in exercise.get(
            "concept_checks",
            []
        )
        if (
            isinstance(
                check,
                dict
            ) and
            check.get(
                "type"
            ) in REFERENCE_CHECK_TYPES
        )
    ]

    functions: dict[
        str,
        list[
            dict
        ]
    ] = {}

    writable_functions = set()

    for check in checks:
        function_name = str(
            check.get(
                "function",
                "<local-reference>"
            )
        )

        functions.setdefault(
            function_name,
            []
        ).append(
            check
        )

        if check.get(
            "type"
        ) in {
            "non_const_reference_parameter",
            "non_const_reference_variable",
        }:
            writable_functions.add(
                function_name
            )

    max_checks_per_function = max(
        (
            len(items)
            for items in functions.values()
        ),
        default=0,
    )

    return {
        "reference_decisions":
            len(checks),
        "distinct_functions":
            len(functions),
        "max_checks_per_function":
            max_checks_per_function,
        "writable_functions":
            len(writable_functions),
        "writable_decisions":
            sum(
                check.get(
                    "type"
                ) in {
                    "non_const_reference_parameter",
                    "non_const_reference_variable",
                }
                for check in checks
            ),
        "read_only_decisions":
            sum(
                check.get(
                    "type"
                ) in {
                    "const_reference_parameter",
                    "const_reference_variable",
                }
                for check in checks
            ),
    }


CUSTOM_LOCAL_DECLARATION_PATTERN = re.compile(
    r"^\s*"
    r"(?:const\s+)?"
    r"(?P<type>[A-Z][A-Za-z0-9_:<>]*)"
    r"\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"\s*(?:\(|\{|=)"
)


def cpp_line_without_literals(
    line: str
) -> str:
    return re.sub(
        r'"(?:\\.|[^"\\])*"',
        '""',
        line
    )


def custom_local_declarations(
    source: str
) -> dict[str, int]:
    depth = 0
    result: dict[
        str,
        int
    ] = {}

    for raw_line in source.splitlines():
        line = cpp_line_without_literals(
            raw_line
        )

        stripped = line.strip()

        if not stripped:
            continue

        leading_closes = 0

        for character in stripped:
            if character == "}":
                leading_closes += 1
            else:
                break

        depth = max(
            0,
            depth -
            leading_closes
        )

        if ";" in stripped:
            match = (
                CUSTOM_LOCAL_DECLARATION_PATTERN.match(
                    stripped
                )
            )

            if match:
                result[
                    match.group(
                        "name"
                    )
                ] = depth

        open_count = (
            line.count(
                "{"
            )
        )

        close_count = (
            line.count(
                "}"
            ) -
            leading_closes
        )

        depth += (
            open_count -
            close_count
        )

        depth = max(
            depth,
            0
        )

    return result


def raii_difficulty_evidence(
    exercise: dict
) -> dict:
    starter = custom_local_declarations(
        str(
            exercise.get(
                "starter_code",
                ""
            )
        )
    )

    reference = custom_local_declarations(
        str(
            exercise.get(
                "reference_solution",
                ""
            )
        )
    )

    moved = []

    for name, starter_depth in (
        starter.items()
    ):
        if name not in reference:
            continue

        reference_depth = reference[
            name
        ]

        if (
            reference_depth !=
            starter_depth
        ):
            moved.append(
                (
                    name,
                    starter_depth,
                    reference_depth,
                )
            )

    target_depths = [
        item[2]
        for item in moved
    ]

    return {
        "resource_declarations":
            len(
                set(
                    starter
                ) |
                set(
                    reference
                )
            ),
        "moved_scope_declarations":
            len(
                moved
            ),
        "max_target_scope_depth":
            max(
                target_depths,
                default=0
            ),
        "distinct_target_depths":
            len(
                set(
                    target_depths
                )
            ),
        "moved_names":
            [
                item[0]
                for item in moved
            ],
    }


def hidden_artifact_text(
    exercise: dict,
    bundled_files: dict[str, str] | None
) -> str:
    parts = []

    if bundled_files is not None:
        for content in bundled_files.values():
            if isinstance(
                content,
                str
            ):
                parts.append(
                    content
                )
    else:
        for field in [
            "hidden_test_file",
            "support_file",
            "analysis_support_file",
        ]:
            raw = exercise.get(
                field
            )

            if not isinstance(
                raw,
                str
            ):
                continue

            path = (
                PROJECT_ROOT /
                raw
            )

            if not path.exists():
                continue

            try:
                parts.append(
                    path.read_text(
                        encoding="utf-8"
                    )
                )
            except OSError:
                pass

    return "\n".join(
        parts
    )


APPROVED_TRACE_STDERR_SINK_PATTERNS = [
    re.compile(r"\bstd::cerr\b"),
    re.compile(r"\bstd::clog\b"),
    re.compile(r"\b(?:std::)?fprintf\s*\(\s*stderr\s*,"),
]


def trace_stream_contract_issues(
    exercise: dict,
    bundled_files: dict[str, str] | None
) -> list[str]:
    hidden = hidden_artifact_text(
        exercise,
        bundled_files
    )

    issues: list[str] = []

    for statement in hidden.split(";"):
        if "TRACE|" not in statement:
            continue

        if any(
            pattern.search(statement)
            for pattern in APPROVED_TRACE_STDERR_SINK_PATTERNS
        ):
            continue

        compact = " ".join(
            statement.strip().split()
        )

        if len(compact) > 180:
            compact = compact[:177] + "..."

        issues.append(
            "TRACE event is not emitted to stderr with std::cerr, std::clog, "
            "or fprintf(stderr,...): " + compact
        )

    return issues


def move_difficulty_evidence(
    exercise: dict,
    bundled_files: dict[str, str] | None
) -> dict:
    starter = str(
        exercise.get(
            "starter_code",
            ""
        )
    )

    reference = str(
        exercise.get(
            "reference_solution",
            ""
        )
    )

    hidden = hidden_artifact_text(
        exercise,
        bundled_files
    )

    public_metadata = "\n".join(
        [
            str(
                exercise.get(
                    "scenario",
                    ""
                )
            ),
            str(
                exercise.get(
                    "problem_statement",
                    ""
                )
            ),
            str(
                exercise.get(
                    "learning_objective",
                    ""
                )
            ),
            "\n".join(
                str(item)
                for item in exercise.get(
                    "constraints",
                    []
                )
                if isinstance(
                    item,
                    str
                )
            ),
        ]
    )

    combined = (
        public_metadata +
        "\n" +
        hidden
    )

    move_check = any(
        (
            isinstance(
                check,
                dict
            ) and
            check.get(
                "type"
            ) ==
            "move_constructor"
        )
        for check in exercise.get(
            "concept_checks",
            []
        )
    )

    noexcept_move = bool(
        re.search(
            r"\b[A-Za-z_][A-Za-z0-9_]*"
            r"\s*\(\s*"
            r"[A-Za-z_][A-Za-z0-9_]*"
            r"\s*&&"
            r"[^)]*\)"
            r"\s*noexcept",
            reference
        )
    )

    copy_deleted = bool(
        re.search(
            r"\(\s*const\s+"
            r"[A-Za-z_][A-Za-z0-9_]*"
            r"\s*&\s*\)"
            r"\s*=\s*delete",
            starter
        )
    )

    unique_ptr_count = len(
        re.findall(
            r"std::unique_ptr\s*<",
            reference
        )
    )

    resource_identity = bool(
        re.search(
            r"\b(?:originalResource|resourceIdentity|sameResource|id\s*\(\)|MOVE_RESOURCE)\b",
            hidden,
            flags=re.IGNORECASE
        ) or
        re.search(
            (
                r"\b(?:original|same|preserv(?:e|ed|es|ing)?|"
                r"retain(?:s|ed|ing)?|keep(?:s|ing)?)\b"
                r".{0,100}"
                r"\b(?:resource\s+)?(?:identity|token|id)\b"
            ),
            public_metadata,
            flags=re.IGNORECASE | re.DOTALL
        ) or
        re.search(
            (
                r"\b(?:resource\s+)?(?:identity|token|id)\b"
                r".{0,100}"
                r"\b(?:original|same|preserv(?:e|ed|es|ing)?|"
                r"retain(?:s|ed|ing)?|keep(?:s|ing)?)\b"
            ),
            public_metadata,
            flags=re.IGNORECASE | re.DOTALL
        )
    )

    moved_from_state = bool(
        re.search(
            r"\b(?:moved[- ]from|sourceIsEmpty|source.*empty|failedPacket\.empty|other\..*nullptr)\b",
            hidden + "\n" + public_metadata,
            flags=re.IGNORECASE
        )
    )

    no_duplicate_allocation = bool(
        re.search(
            r"\b(?:duplicate|replacement|second)\b.{0,60}\ballocat",
            combined,
            flags=re.IGNORECASE | re.DOTALL
        ) or
        re.search(
            r"\bmust\s+not\s+allocate\b",
            combined,
            flags=re.IGNORECASE
        )
    )

    uses_std_move = bool(
        re.search(
            r"\bstd::move\s*\(",
            reference
        )
    )

    exclusive_ownership = (
        unique_ptr_count >= 1 and
        copy_deleted
    )

    advanced_flags = {
        "noexcept_move":
            noexcept_move,
        "resource_identity":
            resource_identity,
        "moved_from_state":
            moved_from_state,
        "no_duplicate_allocation":
            no_duplicate_allocation,
        "exclusive_ownership":
            exclusive_ownership,
    }

    return {
        "move_constructor_check":
            move_check,
        "uses_std_move":
            uses_std_move,
        "unique_ptr_occurrences":
            unique_ptr_count,
        "copy_deleted":
            copy_deleted,
        "advanced_invariants":
            sum(
                bool(value)
                for value in advanced_flags.values()
            ),
        **advanced_flags,
    }



POINTER_NAMED_TRACE_EVENT_PATTERN = re.compile(
    r"TRACE\|"
    r"(?P<event>[A-Z_]*POINTER[A-Z_]*)"
    r"\|"
)

SUPPORTED_POINTER_NAMED_TRACE_EVENTS = {
    "BIND_POINTER",
}


def unsupported_pointer_trace_events(
    exercise: dict,
    bundled_files: dict[str, str] | None
) -> list[str]:
    if exercise.get(
        "topic"
    ) != "pointers":
        return []

    hidden = hidden_artifact_text(
        exercise,
        bundled_files
    )

    events = {
        match.group(
            "event"
        )
        for match in
        POINTER_NAMED_TRACE_EVENT_PATTERN.finditer(
            hidden
        )
    }

    return sorted(
        events -
        SUPPORTED_POINTER_NAMED_TRACE_EVENTS
    )


POINTER_SUBJECT_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*\."
    r"[A-Za-z_][A-Za-z0-9_]*$"
)

POINTER_RESOURCE_ID_PATTERN = re.compile(
    r"^resource#[A-Za-z0-9_%+-]+$"
)

POINTER_STACK_OBJECT_TARGET_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*$"
)

POINTER_CREATE_OBJECT_TRACE_PATTERN = re.compile(
    r"TRACE\|CREATE_OBJECT\|"
    r"(?P<subject>[^|\\\n\"]+)"
    r"\|"
    r"(?P<detail>[^\\\n\"]*)"
)

POINTER_ALLOCATE_TRACE_PATTERN = re.compile(
    r"TRACE\|ALLOCATE_RESOURCE\|"
    r"(?P<subject>[^|\\\n\"]+)"
    r"\|"
    r"(?P<detail>[^\\\n\"]*)"
)

POINTER_RAW_BIND_TRACE_PATTERN = re.compile(
    r"TRACE\|BIND_POINTER\|"
    r"(?P<subject>[^|\\\n\"]+)"
    r"\|"
    r"(?P<target>[^|\\\n\"]+)"
)

POINTER_RAW_NULL_TRACE_PATTERN = re.compile(
    r"TRACE\|SET_NULL\|"
    r"(?P<subject>[^|\\\n\"]+)"
    r"(?:\|(?P<detail>[^\\\n\"]*))?"
)

POINTER_RAW_WRITE_TRACE_PATTERN = re.compile(
    r"TRACE\|WRITE_VALUE\|"
    r"(?P<subject>[^|\\\n\"]+)"
    r"\|"
    r"(?P<detail>[^\\\n\"]*)"
)


def pointer_trace_detail_values(
    detail: str
) -> dict[str, str]:
    result: dict[str, str] = {}

    for item in str(
        detail
    ).split(
        "|"
    ):
        if "=" not in item:
            continue

        key, value = item.split(
            "=",
            1
        )

        key = key.strip()
        value = value.strip()

        if key:
            result[
                key
            ] = value

    return result


POINTER_ENTER_SCOPE_TRACE_PATTERN = re.compile(
    r"TRACE\|ENTER_SCOPE\|"
    r"(?P<subject>[^|\\\n\"]+)"
)

POINTER_BIND_ALIAS_TRACE_PATTERN = re.compile(
    r"TRACE\|BIND_ALIAS\|"
    r"(?P<subject>[^|\\\n\"]+)"
)


def pointer_write_value_provenance_issues(
    exercise: dict,
    bundled_files: dict[str, str] | None
) -> list[str]:
    if exercise.get("topic") != "pointers":
        return []

    hidden = hidden_artifact_text(exercise, bundled_files)

    known_via_names = {
        match.group("subject").strip()
        for match in POINTER_ENTER_SCOPE_TRACE_PATTERN.finditer(hidden)
    }
    known_via_names.update(
        match.group("subject").strip()
        for match in POINTER_BIND_ALIAS_TRACE_PATTERN.finditer(hidden)
    )

    issues: list[str] = []
    for match in POINTER_RAW_WRITE_TRACE_PATTERN.finditer(hidden):
        detail_values = pointer_trace_detail_values(match.group("detail"))
        via_name = detail_values.get("via", "").strip()
        if via_name and via_name not in known_via_names:
            issues.append(
                "WRITE_VALUE uses via='" + via_name +
                "', but that name is not represented by a TRACE ENTER_SCOPE "
                "subject or BIND_ALIAS subject. For a mutation performed "
                "directly through an ordinary C++ local pointer variable, "
                "omit via=. Use through=object.field_ only when the actual "
                "mutation occurred through that traced holder pointer field."
            )

    return issues


def pointer_trace_chronology_issues(
    exercise: dict,
    bundled_files: dict[str, str] | None
) -> list[str]:
    if exercise.get(
        "topic"
    ) != "pointers":
        return []

    hidden = hidden_artifact_text(
        exercise,
        bundled_files
    )

    created_objects = {
        match.group(
            "subject"
        ).strip()
        for match in
        POINTER_CREATE_OBJECT_TRACE_PATTERN.finditer(
            hidden
        )
    }

    binds_by_target: dict[
        str,
        list[tuple[int, str]]
    ] = {}

    for match in (
        POINTER_RAW_BIND_TRACE_PATTERN.finditer(
            hidden
        )
    ):
        target = match.group(
            "target"
        ).strip()

        if target not in created_objects:
            continue

        binds_by_target.setdefault(
            target,
            []
        ).append(
            (
                match.start(),
                match.group(
                    "subject"
                ).strip(),
            )
        )

    writes_by_object: dict[
        str,
        list[int]
    ] = {}

    for match in (
        POINTER_RAW_WRITE_TRACE_PATTERN.finditer(
            hidden
        )
    ):
        subject = match.group(
            "subject"
        ).strip()

        if subject not in created_objects:
            continue

        detail_values = (
            pointer_trace_detail_values(
                match.group(
                    "detail"
                )
            )
        )

        if (
            detail_values.get(
                "through",
                ""
            ).strip() or
            detail_values.get(
                "via_pointer",
                ""
            ).strip()
        ):
            continue

        writes_by_object.setdefault(
            subject,
            []
        ).append(
            match.start()
        )

    issues: list[str] = []

    for target, bind_entries in (
        binds_by_target.items()
    ):
        writes = writes_by_object.get(
            target,
            []
        )

        if not writes:
            continue

        first_bind_position, first_subject = min(
            bind_entries,
            key=lambda item: item[0]
        )

        first_write_position = min(
            writes
        )

        if (
            first_write_position <
            first_bind_position
        ):
            issues.append(
                (
                    "Pointer trace chronology for "
                    f"'{first_subject}' -> '{target}' is reversed: "
                    f"WRITE_VALUE for stack pointee '{target}' appears "
                    "before its first BIND_POINTER. Emit the observed "
                    "BIND_POINTER immediately after the operation that "
                    "establishes the relationship (and before a later "
                    "caller-side pointee mutation), then emit the direct "
                    "WRITE_VALUE after that real mutation."
                )
            )

    return issues


def pointer_trace_shape_issues(
    exercise: dict,
    bundled_files: dict[str, str] | None
) -> list[str]:
    if exercise.get(
        "topic"
    ) != "pointers":
        return []

    hidden = hidden_artifact_text(
        exercise,
        bundled_files
    )

    issues: list[str] = []

    holder_fields: dict[
        str,
        set[str]
    ] = {}

    created_objects: set[str] = set()

    for match in (
        POINTER_CREATE_OBJECT_TRACE_PATTERN.finditer(
            hidden
        )
    ):
        object_name = match.group(
            "subject"
        ).strip()

        created_objects.add(
            object_name
        )

        detail_values = (
            pointer_trace_detail_values(
                match.group(
                    "detail"
                )
            )
        )

        pointer_field = detail_values.get(
            "pointer",
            ""
        ).strip()

        if pointer_field:
            holder_fields.setdefault(
                object_name,
                set()
            ).add(
                pointer_field
            )

    allocated_resources: set[str] = set()

    for match in (
        POINTER_ALLOCATE_TRACE_PATTERN.finditer(
            hidden
        )
    ):
        resource = match.group(
            "subject"
        ).strip()

        if not POINTER_RESOURCE_ID_PATTERN.fullmatch(
            resource
        ):
            issues.append(
                (
                    "ALLOCATE_RESOURCE subject "
                    f"'{resource}' must use a stable resource#N id."
                )
            )
            continue

        allocated_resources.add(
            resource
        )

    bind_pairs: set[
        tuple[str, str]
    ] = set()

    bind_count = 0

    for match in (
        POINTER_RAW_BIND_TRACE_PATTERN.finditer(
            hidden
        )
    ):
        bind_count += 1

        subject = match.group(
            "subject"
        ).strip()

        target = match.group(
            "target"
        ).strip()

        if not POINTER_SUBJECT_PATTERN.fullmatch(
            subject
        ):
            issues.append(
                (
                    "BIND_POINTER subject "
                    f"'{subject}' must be fully qualified as object.field_."
                )
            )
        else:
            object_name, field_name = subject.split(
                ".",
                1
            )

            if object_name not in created_objects:
                issues.append(
                    (
                        "BIND_POINTER subject "
                        f"'{subject}' uses holder object '{object_name}', "
                        "but no CREATE_OBJECT event creates that holder."
                    )
                )
            elif field_name not in holder_fields.get(
                object_name,
                set()
            ):
                issues.append(
                    (
                        "BIND_POINTER subject "
                        f"'{subject}' is not declared as a pointer field. "
                        f"Use CREATE_OBJECT|{object_name}|type=...|"
                        f"pointer={field_name}."
                    )
                )

        target_is_resource = bool(
            POINTER_RESOURCE_ID_PATTERN.fullmatch(
                target
            )
        )

        target_is_stack_object = (
            bool(
                POINTER_STACK_OBJECT_TARGET_PATTERN.fullmatch(
                    target
                )
            ) and
            target in created_objects
        )

        if target_is_resource:
            if target not in allocated_resources:
                issues.append(
                    (
                        "BIND_POINTER target "
                        f"'{target}' has no matching ALLOCATE_RESOURCE "
                        "trace declaration."
                    )
                )
        elif not target_is_stack_object:
            issues.append(
                (
                    "BIND_POINTER target "
                    f"'{target}' must name either a stack object created "
                    "by CREATE_OBJECT or a stable resource#N id created "
                    "by ALLOCATE_RESOURCE."
                )
            )

        if (
            POINTER_SUBJECT_PATTERN.fullmatch(
                subject
            ) and
            (
                target_is_resource or
                target_is_stack_object
            )
        ):
            bind_pairs.add(
                (
                    subject,
                    target,
                )
            )

    for match in (
        POINTER_RAW_NULL_TRACE_PATTERN.finditer(
            hidden
        )
    ):
        subject = match.group(
            "subject"
        ).strip()

        if not POINTER_SUBJECT_PATTERN.fullmatch(
            subject
        ):
            issues.append(
                (
                    "SET_NULL subject "
                    f"'{subject}' must be fully qualified as object.field_."
                )
            )
            continue

        object_name, field_name = subject.split(
            ".",
            1
        )

        if object_name not in created_objects:
            issues.append(
                (
                    "SET_NULL subject "
                    f"'{subject}' uses holder object '{object_name}', "
                    "but no CREATE_OBJECT event creates that holder."
                )
            )
        elif field_name not in holder_fields.get(
            object_name,
            set()
        ):
            issues.append(
                (
                    "SET_NULL subject "
                    f"'{subject}' is not declared by "
                    f"CREATE_OBJECT|{object_name}|...|pointer={field_name}."
                )
            )

    for match in (
        POINTER_RAW_WRITE_TRACE_PATTERN.finditer(
            hidden
        )
    ):
        target = match.group(
            "subject"
        ).strip()

        detail_values = (
            pointer_trace_detail_values(
                match.group(
                    "detail"
                )
            )
        )

        through = (
            detail_values.get(
                "through"
            ) or
            detail_values.get(
                "via_pointer"
            ) or
            ""
        ).strip()

        if (
            not through and
            target in created_objects
        ):
            object_value = (
                detail_values.get(
                    "value",
                    ""
                )
            ).strip()

            if not object_value:
                issues.append(
                    (
                        "WRITE_VALUE target "
                        f"'{target}' is a CREATE_OBJECT stack object. Direct "
                        "stack-object visualization updates must use "
                        "WRITE_VALUE|object|value=field=value with no through= "
                        "or via_pointer=."
                    )
                )

            continue

        if not through:
            continue

        if not POINTER_SUBJECT_PATTERN.fullmatch(
            through
        ):
            issues.append(
                (
                    "WRITE_VALUE pointer path "
                    f"'{through}' must be fully qualified as object.field_."
                )
            )
            continue

        object_name, field_name = through.split(
            ".",
            1
        )

        if object_name not in created_objects:
            issues.append(
                (
                    "WRITE_VALUE through="
                    f"'{through}' uses holder object '{object_name}', "
                    "but no CREATE_OBJECT event creates that holder."
                )
            )
        elif field_name not in holder_fields.get(
            object_name,
            set()
        ):
            issues.append(
                (
                    "WRITE_VALUE through="
                    f"'{through}' is not declared by "
                    f"CREATE_OBJECT|{object_name}|...|pointer={field_name}."
                )
            )

        if not POINTER_RESOURCE_ID_PATTERN.fullmatch(
            target
        ):
            issues.append(
                (
                    "Pointer-mediated WRITE_VALUE target "
                    f"'{target}' must be the pointed resource#N, not a "
                    "derived stack value."
                )
            )
            continue

        if target not in allocated_resources:
            issues.append(
                (
                    "Pointer-mediated WRITE_VALUE target "
                    f"'{target}' has no ALLOCATE_RESOURCE declaration."
                )
            )

        if (
            through,
            target,
        ) not in bind_pairs:
            issues.append(
                (
                    "Pointer-mediated WRITE_VALUE "
                    f"through='{through}' targets '{target}', but the hidden "
                    "source has no matching BIND_POINTER|"
                    f"{through}|{target} relationship."
                )
            )

    if bind_count == 0:
        issues.append(
            (
                "Pointers hidden instrumentation must contain at least one "
                "BIND_POINTER|object.field_|<stackObject-or-resource#N> event "
                "so pointer identity is measurable."
            )
        )

    return issues


POINTER_BIND_TRACE_PATTERN = re.compile(
    r"TRACE\|BIND_POINTER\|"
    r"(?P<subject>[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*)"
    r"\|"
    r"(?P<target>(?:resource#[A-Za-z0-9_%+-]+|"
    r"[A-Za-z_][A-Za-z0-9_]*))"
)

POINTER_NULL_TRACE_PATTERN = re.compile(
    r"TRACE\|SET_NULL\|"
    r"(?P<subject>[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*)"
    r"\|"
)

POINTER_WRITE_TRACE_PATTERN = re.compile(
    r"TRACE\|WRITE_VALUE\|"
    r"(?P<resource>resource#[A-Za-z0-9_%+-]+)"
    r"\|[^\n\"]*?"
    r"(?:through|via_pointer)="
    r"(?P<subject>[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*)"
)

POINTER_FREE_TRACE_PATTERN = re.compile(
    r"TRACE\|FREE_RESOURCE\|"
    r"(?P<resource>resource#[A-Za-z0-9_%+-]+)"
    r"\|"
)

RAW_POINTER_DECLARATION_PATTERN = re.compile(
    r"\b(?:const\s+)?"
    r"[A-Za-z_][A-Za-z0-9_:<>]*"
    r"\s*\*\s*"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
)


def pointer_difficulty_evidence(
    exercise: dict,
    bundled_files: dict[str, str] | None
) -> dict:
    starter = str(
        exercise.get(
            "starter_code",
            ""
        )
    )

    reference = str(
        exercise.get(
            "reference_solution",
            ""
        )
    )

    hidden = hidden_artifact_text(
        exercise,
        bundled_files
    )

    raw_pointer_matches = list(
        RAW_POINTER_DECLARATION_PATTERN.finditer(
            reference
        )
    )

    raw_pointer_names = {
        match.group(
            "name"
        )
        for match in raw_pointer_matches
    }

    smart_pointer_count = len(
        re.findall(
            r"\bstd::(?:unique_ptr|shared_ptr|weak_ptr)\s*<",
            reference
        )
    )

    bindings: dict[str, set[str]] = {}

    for match in POINTER_BIND_TRACE_PATTERN.finditer(
        hidden
    ):
        subject = match.group(
            "subject"
        )
        target = match.group(
            "target"
        )

        bindings.setdefault(
            subject,
            set()
        ).add(
            target
        )

    pointer_subjects = set(
        bindings
    )

    pointer_holder_objects = {
        subject.split(
            ".",
            1
        )[0]
        for subject in pointer_subjects
    }

    null_subjects = {
        match.group(
            "subject"
        )
        for match in POINTER_NULL_TRACE_PATTERN.finditer(
            hidden
        )
    }

    write_subjects = {
        match.group(
            "subject"
        )
        for match in POINTER_WRITE_TRACE_PATTERN.finditer(
            hidden
        )
    }

    freed_resources = {
        match.group(
            "resource"
        )
        for match in POINTER_FREE_TRACE_PATTERN.finditer(
            hidden
        )
    }

    subjects_by_target: dict[
        str,
        set[str]
    ] = {}

    for subject, targets in bindings.items():
        for target in targets:
            subjects_by_target.setdefault(
                target,
                set()
            ).add(
                subject
            )

    aliasing_resources = {
        target
        for target, subjects in (
            subjects_by_target.items()
        )
        if len(
            subjects
        ) >= 2
    }

    reseated_subjects = {
        subject
        for subject, targets in bindings.items()
        if len(
            targets
        ) >= 2
    }

    bound_targets = set(
        subjects_by_target
    )

    bound_resources = {
        target
        for target in bound_targets
        if POINTER_RESOURCE_ID_PATTERN.fullmatch(
            target
        )
    }

    lifetime_resources = (
        bound_resources &
        freed_resources
    )

    null_state = bool(
        null_subjects
    )

    write_through = bool(
        write_subjects
    )

    aliasing = bool(
        aliasing_resources
    )

    reseating = bool(
        reseated_subjects
    )

    lifetime_boundary = bool(
        lifetime_resources
    )

    pointer_decisions = (
        len(
            pointer_subjects
        ) +
        int(
            null_state
        ) +
        int(
            write_through
        ) +
        int(
            aliasing
        ) +
        int(
            reseating
        ) +
        int(
            lifetime_boundary
        )
    )

    return {
        "raw_pointer_declarations":
            len(
                raw_pointer_matches
            ),
        "raw_pointer_names":
            sorted(
                raw_pointer_names
            ),
        "smart_pointer_occurrences":
            smart_pointer_count,
        "pointer_subjects":
            len(
                pointer_subjects
            ),
        "pointer_subject_names":
            sorted(
                pointer_subjects
            ),
        "pointer_holder_objects":
            len(
                pointer_holder_objects
            ),
        "pointer_holder_names":
            sorted(
                pointer_holder_objects
            ),
        "pointer_targets":
            len(
                bound_targets
            ),
        "pointer_resources":
            len(
                bound_resources
            ),
        "null_pointer_subjects":
            len(
                null_subjects
            ),
        "writable_pointer_paths":
            len(
                write_subjects
            ),
        "aliasing_resources":
            len(
                aliasing_resources
            ),
        "reseated_pointer_subjects":
            len(
                reseated_subjects
            ),
        "lifetime_resources":
            len(
                lifetime_resources
            ),
        "null_state":
            null_state,
        "write_through":
            write_through,
        "aliasing":
            aliasing,
        "reseating":
            reseating,
        "lifetime_boundary":
            lifetime_boundary,
        "pointer_decisions":
            pointer_decisions,
    }




def raii_hidden_test_text(
    exercise: dict,
    bundled_files: dict[str, str] | None,
) -> str:
    raw = exercise.get("hidden_test_file")
    if not isinstance(raw, str) or not raw.strip():
        return ""
    if bundled_files is not None:
        value = bundled_files.get(raw, "")
        return value if isinstance(value, str) else ""
    path = PROJECT_ROOT / raw
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def raii_helper_names_called_with_vector(
    hidden: str,
    vector_name: str,
) -> list[str]:
    if not hidden or not vector_name:
        return []

    escaped = re.escape(
        vector_name
    )

    names: list[str] = []

    for match in re.finditer(
        rf"\b(?P<helper>[A-Za-z_][A-Za-z0-9_]*)"
        rf"\s*\(\s*{escaped}\s*\)",
        hidden,
    ):
        helper = match.group(
            "helper"
        )

        if helper in {
            "if",
            "while",
            "for",
            "switch",
            "return",
        }:
            continue

        if helper not in names:
            names.append(
                helper
            )

    return names


def raii_exact_sequence_grading_issues(
    exercise: dict,
    bundled_files: dict[str, str] | None,
) -> list[str]:
    if exercise.get("topic") != "raii_scope":
        return []

    hidden = raii_hidden_test_text(
        exercise,
        bundled_files,
    )

    if not hidden:
        return []

    combined = hidden_artifact_text(
        exercise,
        bundled_files,
    )

    issues: list[str] = []

    expected_vectors = list(
        re.finditer(
            r"(?:const\s+)?std::vector\s*<\s*std::string\s*>\s+"
            r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*\{",
            hidden,
        )
    )

    for expected_vector in expected_vectors:
        expected_name_raw = expected_vector.group("name")
        expected_name = re.escape(expected_name_raw)

        direct_exact = re.search(
            rf"[A-Za-z_][A-Za-z0-9_]*\s*\(\s*\)"
            rf"\s*(?:!=|==)\s*{expected_name}\b",
            hidden,
        )

        direct_reverse = re.search(
            rf"\b{expected_name}\b\s*(?:!=|==)\s*"
            rf"[A-Za-z_][A-Za-z0-9_]*\s*\(\s*\)",
            hidden,
        )

        if direct_exact or direct_reverse:
            issues.append(
                "hidden test compares an entire RAII lifecycle audit vector "
                "to one exact expected sequence. Grade required creation/use/"
                "cleanup ordering relationships instead so equivalent lexical "
                "scope arrangements can pass."
            )
            continue

        helper_names = (
            raii_helper_names_called_with_vector(
                hidden,
                expected_name_raw,
            )
        )

        helper_exact = False

        for helper in helper_names:

            helper_definition = re.search(
                rf"""
                \b(?:inline\s+)?(?:static\s+)?
                (?:bool|int)\s+
                {re.escape(helper)}
                \s*\(
                    [^)]*
                    std::vector\s*<\s*std::string\s*>
                    [^,)]*
                    \b(?P<param>[A-Za-z_][A-Za-z0-9_]*)
                    [^)]*
                \)
                \s*\{{
                (?P<body>.*?)
                \}}
                """,
                combined,
                re.VERBOSE | re.DOTALL,
            )

            if helper_definition is None:
                continue

            parameter = re.escape(
                helper_definition.group("param")
            )

            body = helper_definition.group("body")

            exact_through_helper = re.search(
                rf"""
                [A-Za-z_][A-Za-z0-9_]*\s*\(\s*\)
                \s*(?:==|!=)\s*
                {parameter}\b
                """,
                body,
                re.VERBOSE,
            )

            reverse_through_helper = re.search(
                rf"""
                \b{parameter}\b
                \s*(?:==|!=)\s*
                [A-Za-z_][A-Za-z0-9_]*\s*\(\s*\)
                """,
                body,
                re.VERBOSE,
            )

            if exact_through_helper or reverse_through_helper:
                helper_exact = True
                break

        if helper_exact:
            issues.append(
                "hidden test passes its complete expected RAII lifecycle "
                "vector through a helper that performs exact whole-vector "
                "equality/inequality. Grade the required lifetime partial "
                "ordering instead so equivalent lexical-scope arrangements "
                "can pass."
            )

    return issues

def difficulty_quality_result(
    exercise: dict,
    bundled_files: dict[str, str] | None
) -> tuple[
    bool,
    str,
    dict
]:
    topic = exercise.get(
        "topic"
    )

    difficulty = exercise.get(
        "difficulty"
    )

    if (
        topic not in {
            "references",
            "raii_scope",
            "move_semantics",
            "pointers",
        } or
        difficulty not in
        VALID_DIFFICULTIES
    ):
        return (
            True,
            (
                "No topic-specific difficulty-quality rubric "
                "applies to this exercise."
            ),
            {},
        )

    if topic == "references":
        evidence = (
            reference_difficulty_evidence(
                exercise
            )
        )

        decisions = evidence[
            "reference_decisions"
        ]

        max_per_function = evidence[
            "max_checks_per_function"
        ]

        writable_functions = evidence[
            "writable_functions"
        ]

        distinct_functions = evidence[
            "distinct_functions"
        ]

        if difficulty == "easy":
            valid = (
                1 <= decisions <= 2 and
                max_per_function <= 1 and
                writable_functions <= 1
            )

            expectation = (
                "Easy References requires 1-2 reference decisions, "
                "at most one learner-fixable reference decision per "
                "function, and no more than one writable mutation path."
            )

        elif difficulty == "medium":
            looks_medium = (
                decisions >= 2 and
                (
                    decisions >= 3 or
                    max_per_function >= 2
                )
            )

            looks_hard = (
                decisions >= 4 and
                distinct_functions >= 2 and
                writable_functions >= 2
            )

            valid = (
                looks_medium and
                not looks_hard
            )

            expectation = (
                "Medium References requires several reference decisions "
                "or multiple decisions inside one function, while writable "
                "caller state remains concentrated in one primary function path."
            )

        else:
            valid = (
                decisions >= 4 and
                distinct_functions >= 2 and
                writable_functions >= 2
            )

            expectation = (
                "Hard References requires at least 4 measurable reference "
                "decisions across at least 2 functions, with writable caller "
                "state mutated through at least 2 distinct function paths."
            )

        detail = (
            f"{expectation} Observed: {decisions} reference decision(s), "
            f"{distinct_functions} function(s), max {max_per_function} "
            f"decision(s) in one function, {writable_functions} writable "
            "function path(s)."
        )

        return (
            valid,
            detail,
            evidence,
        )

    if topic == "raii_scope":
        evidence = (
            raii_difficulty_evidence(
                exercise
            )
        )

        moved = evidence[
            "moved_scope_declarations"
        ]

        max_depth = evidence[
            "max_target_scope_depth"
        ]

        distinct_depths = evidence[
            "distinct_target_depths"
        ]

        hard_shape = (
            moved >= 2 and
            (
                moved >= 3 or
                max_depth >= 3 or
                distinct_depths >= 2
            )
        )

        if difficulty == "easy":
            valid = (
                moved == 1 and
                max_depth <= 2
            )

            expectation = (
                "Easy RAII requires exactly one custom resource "
                "declaration to move into a narrower scope."
            )

        elif difficulty == "medium":
            valid = (
                moved >= 2 and
                max_depth <= 2 and
                distinct_depths <= 1 and
                not hard_shape
            )

            expectation = (
                "Medium RAII requires at least two resource declarations "
                "to change lifetime while sharing one cleanup boundary."
            )

        else:
            valid = hard_shape

            expectation = (
                "Hard RAII requires at least two changed resource lifetimes "
                "plus deeper nesting, multiple target cleanup depths, or at "
                "least three moved resource declarations."
            )

        moved_names = (
            ", ".join(
                evidence[
                    "moved_names"
                ]
            ) or
            "none"
        )

        detail = (
            f"{expectation} Observed: {moved} moved declaration(s) "
            f"({moved_names}), max target scope depth {max_depth}, "
            f"{distinct_depths} distinct target depth(s)."
        )

        return (
            valid,
            detail,
            evidence,
        )

    if topic == "pointers":
        evidence = pointer_difficulty_evidence(
            exercise,
            bundled_files
        )

        decisions = evidence[
            "pointer_decisions"
        ]

        subjects = evidence[
            "pointer_subjects"
        ]

        holder_objects = evidence[
            "pointer_holder_objects"
        ]

        writable_paths = evidence[
            "writable_pointer_paths"
        ]

        aliasing = evidence[
            "aliasing"
        ]

        lifetime_boundary = evidence[
            "lifetime_boundary"
        ]

        null_or_reseat = (
            evidence[
                "null_state"
            ] or
            evidence[
                "reseating"
            ]
        )

        raw_pointers = evidence[
            "raw_pointer_declarations"
        ]

        smart_pointers = evidence[
            "smart_pointer_occurrences"
        ]

        hard_shape = (
            decisions >= 6 and
            subjects >= 2 and
            holder_objects >= 2 and
            aliasing and
            lifetime_boundary and
            writable_paths >= 1 and
            null_or_reseat
        )

        if difficulty == "easy":
            valid = (
                raw_pointers >= 1 and
                smart_pointers == 0 and
                1 <= decisions <= 2 and
                subjects == 1 and
                writable_paths <= 1 and
                not aliasing and
                not lifetime_boundary
            )

            expectation = (
                "Easy Pointers requires exactly one traced raw-pointer "
                "subject, 1-2 pointer decisions, at most one write-through "
                "path, and no aliasing or pointee-lifetime boundary."
            )

        elif difficulty == "medium":
            valid = (
                raw_pointers >= 1 and
                smart_pointers == 0 and
                3 <= decisions <= 5 and
                not hard_shape
            )

            expectation = (
                "Medium Pointers requires 3-5 measurable pointer decisions "
                "using raw pointers, without the complete Hard aliasing + "
                "lifetime-boundary shape."
            )

        else:
            valid = (
                raw_pointers >= 2 and
                smart_pointers == 0 and
                hard_shape
            )

            expectation = (
                "Hard Pointers requires at least 6 measurable pointer "
                "decisions, at least 2 traced pointer subjects on at least "
                "2 pointer-holder objects, aliasing, write-through mutation, "
                "a pointee lifetime boundary, and an explicit null/reseat "
                "state transition."
            )

        flags = []

        for name in [
            "null_state",
            "write_through",
            "aliasing",
            "reseating",
            "lifetime_boundary",
        ]:
            if evidence.get(
                name
            ):
                flags.append(
                    name
                )

        detail = (
            f"{expectation} Observed: {decisions} pointer decision(s), "
            f"{subjects} traced pointer subject(s) across {holder_objects} "
            f"holder object(s), {writable_paths} write-through path(s), "
            f"raw pointer declarations "
            f"{raw_pointers}, smart pointer occurrences {smart_pointers}; "
            "behaviors: " +
            (
                ", ".join(
                    flags
                )
                if flags
                else "basic binding only"
            ) +
            "."
        )

        return (
            valid,
            detail,
            evidence,
        )

    evidence = move_difficulty_evidence(
        exercise,
        bundled_files
    )

    advanced = evidence[
        "advanced_invariants"
    ]

    required_hard = [
        "noexcept_move",
        "resource_identity",
        "moved_from_state",
        "no_duplicate_allocation",
        "exclusive_ownership",
    ]

    hard_complete = all(
        evidence.get(
            name,
            False
        )
        for name in required_hard
    )

    if difficulty == "easy":
        valid = (
            evidence[
                "move_constructor_check"
            ] and
            advanced <= 2
        )

        expectation = (
            "Easy Move Semantics requires a move-constructor exercise "
            "with at most two advanced ownership invariants."
        )

    elif difficulty == "medium":
        valid = (
            evidence[
                "move_constructor_check"
            ] and
            3 <= advanced <= 4 and
            not hard_complete
        )

        expectation = (
            "Medium Move Semantics requires 3-4 advanced ownership "
            "invariants, but not the complete hard invariant set."
        )

    else:
        valid = (
            evidence[
                "move_constructor_check"
            ] and
            hard_complete
        )

        expectation = (
            "Hard Move Semantics requires all five invariants: noexcept "
            "move construction, resource identity preservation, valid/empty "
            "moved-from state, no replacement allocation, and exclusive ownership."
        )

    enabled_invariants = [
        name
        for name in required_hard
        if evidence.get(
            name,
            False
        )
    ]

    detail = (
        f"{expectation} Observed {advanced}/5 advanced invariant(s): " +
        (
            ", ".join(
                enabled_invariants
            )
            if enabled_invariants
            else "none"
        ) +
        "."
    )

    return (
        valid,
        detail,
        evidence,
    )


def add_difficulty_quality_check(
    exercise: dict,
    report: ValidationReport,
    bundled_files: dict[str, str] | None
):
    valid, detail, _ = difficulty_quality_result(
        exercise,
        bundled_files
    )

    add_check(
        report,
        "difficulty.quality",
        "difficulty",
        (
            "pass"
            if valid
            else "fail"
        ),
        detail,
    )


def validate_structure(
    exercise: dict,
    report: ValidationReport,
    *,
    bundled_files: dict[str, str] | None = None,
):
    required_strings = {
        "id": 3,
        "topic": 2,
        "title": 8,
        "scenario": 60,
        "problem_statement": 80,
        "learning_objective": 30,
        "instructions": 40,
        "starter_code": 20,
        "reference_solution": 20,
        "explanation": 40,
        "hidden_test_file": 8,
    }

    version = exercise.get(
        "exercise_schema_version"
    )

    add_check(
        report,
        "schema.version",
        "schema",
        (
            "pass"
            if version == 1
            else "fail"
        ),
        (
            "exercise_schema_version is 1."
            if version == 1
            else (
                "exercise_schema_version must be 1."
            )
        ),
    )

    for field, minimum in (
        required_strings.items()
    ):
        value = exercise.get(
            field
        )

        valid = (
            non_empty_string(
                value
            ) and
            len(
                value.strip()
            ) >= minimum
        )

        add_check(
            report,
            f"schema.{field}",
            "schema",
            (
                "pass"
                if valid
                else "fail"
            ),
            (
                f"{field} is present."
                if valid
                else (
                    f"{field} must be a string "
                    f"with at least {minimum} characters."
                )
            ),
        )

    learner_goal = exercise.get(
        "learner_goal"
    )

    learner_goal_present = (
        non_empty_string(
            learner_goal
        ) and
        len(
            learner_goal.strip()
        ) >= 30
    )

    add_check(
        report,
        "schema.learner_goal",
        "schema",
        (
            "pass"
            if learner_goal_present
            else "warn"
        ),
        (
            "A learner-safe public goal is present."
            if learner_goal_present
            else (
                "Legacy exercise has no learner_goal; the UI will use "
                "a safe topic/problem fallback. New generated exercises "
                "must provide learner_goal."
            )
        ),
    )

    learner_goal_hits = (
        [
            pattern.pattern
            for pattern in LEARNER_GOAL_SOLUTION_PATTERNS
            if pattern.search(
                learner_goal or ""
            )
        ]
        if learner_goal_present
        else []
    )

    add_check(
        report,
        "pedagogy.learner_goal_no_answer",
        "pedagogy",
        (
            "pass"
            if not learner_goal_hits
            else "fail"
        ),
        (
            "Learner goal describes observable behavior without naming the target C++ mechanism."
            if not learner_goal_hits
            else (
                "learner_goal reveals the intended C++ mechanism; rewrite it in behavioral terms."
            )
        ),
    )

    exercise_id = exercise.get(
        "id",
        ""
    )

    id_valid = bool(
        re.fullmatch(
            r"[a-z0-9][a-z0-9_]*",
            exercise_id
        )
    )

    add_check(
        report,
        "schema.id_format",
        "schema",
        (
            "pass"
            if id_valid
            else "fail"
        ),
        (
            "Exercise id uses the stable lowercase underscore format."
            if id_valid
            else (
                "Exercise id may contain only lowercase "
                "letters, digits, and underscores."
            )
        ),
    )

    difficulty = exercise.get(
        "difficulty"
    )

    difficulty_valid = (
        difficulty in
        VALID_DIFFICULTIES
    )

    add_check(
        report,
        "schema.difficulty",
        "schema",
        (
            "pass"
            if difficulty_valid
            else "fail"
        ),
        (
            f"Difficulty is {difficulty}."
            if difficulty_valid
            else (
                "Difficulty must be exactly "
                "easy, medium, or hard."
            )
        ),
    )

    exercise_type = exercise.get(
        "type"
    )

    type_valid = (
        exercise_type in
        VALID_EXERCISE_TYPES
    )

    add_check(
        report,
        "schema.type",
        "schema",
        (
            "pass"
            if type_valid
            else "fail"
        ),
        (
            f"Exercise type is {exercise_type}."
            if type_valid
            else (
                "Exercise type must be fix_code, "
                "implement_code, or debug_code."
            )
        ),
    )

    topic = exercise.get(
        "topic"
    )

    topic_valid = (
        isinstance(
            topic,
            str
        ) and
        topic in
        known_topic_ids()
    )

    add_check(
        report,
        "schema.topic",
        "schema",
        (
            "pass"
            if topic_valid
            else "fail"
        ),
        (
            f"Topic '{topic}' exists in catalog/topics.json."
            if topic_valid
            else (
                f"Unknown topic '{topic}'. Add it to "
                "catalog/topics.json before generating exercises for it."
            )
        ),
    )

    constraints = exercise.get(
        "constraints"
    )

    constraints_valid = (
        isinstance(
            constraints,
            list
        ) and
        len(constraints) >= 1 and
        all(
            non_empty_string(item)
            and len(item.strip()) >= 8
            for item in constraints
        )
    )

    add_check(
        report,
        "schema.constraints",
        "schema",
        (
            "pass"
            if constraints_valid
            else "fail"
        ),
        (
            f"{len(constraints)} learner constraints provided."
            if constraints_valid
            else (
                "constraints must be a non-empty array "
                "of meaningful strings."
            )
        ),
    )

    concepts = exercise.get(
        "expected_concepts"
    )

    concepts_valid = (
        isinstance(
            concepts,
            list
        ) and
        len(concepts) >= 1 and
        all(
            non_empty_string(item)
            for item in concepts
        )
    )

    add_check(
        report,
        "schema.expected_concepts",
        "schema",
        (
            "pass"
            if concepts_valid
            else "fail"
        ),
        (
            f"{len(concepts)} expected concept tags provided."
            if concepts_valid
            else (
                "expected_concepts must contain at least one concept."
            )
        ),
    )

    hints = exercise.get(
        "hints"
    )

    hints_valid = (
        isinstance(
            hints,
            list
        ) and
        1 <= len(hints) <= 3 and
        all(
            non_empty_string(item)
            and len(item.strip()) >= 8
            for item in hints
        )
    )

    add_check(
        report,
        "schema.hints",
        "schema",
        (
            "pass"
            if hints_valid
            else "fail"
        ),
        (
            f"{len(hints)} progressive hint(s) provided."
            if hints_valid
            else (
                "hints must contain between 1 and 3 "
                "meaningful progressive hints."
            )
        ),
    )

    trace_mode = exercise.get(
        "trace_mode",
        "source_pattern"
    )

    trace_valid = (
        trace_mode in
        VALID_TRACE_MODES
    )

    add_check(
        report,
        "schema.trace_mode",
        "schema",
        (
            "pass"
            if trace_valid
            else "fail"
        ),
        (
            f"Trace mode '{trace_mode}' is supported."
            if trace_valid
            else (
                f"Unsupported trace mode '{trace_mode}'."
            )
        ),
    )

    starter = exercise.get(
        "starter_code",
        ""
    )

    reference = exercise.get(
        "reference_solution",
        ""
    )

    different = (
        isinstance(
            starter,
            str
        ) and
        isinstance(
            reference,
            str
        ) and
        starter.strip() !=
        reference.strip()
    )

    add_check(
        report,
        "pedagogy.starter_differs",
        "pedagogy",
        (
            "pass"
            if different
            else "fail"
        ),
        (
            "Starter code differs from the hidden reference solution."
            if different
            else (
                "Starter code must not already be the reference solution."
            )
        ),
    )

    todo_match = re.search(
        r"\b(?:TODO|FIXME)\b",
        starter,
        flags=re.IGNORECASE
    )

    add_check(
        report,
        "pedagogy.no_todo",
        "pedagogy",
        (
            "pass"
            if todo_match is None
            else "fail"
        ),
        (
            "Starter code contains no TODO/FIXME answer scaffolding."
            if todo_match is None
            else (
                "Starter code must present a real problem, "
                "not TODO/FIXME scaffolding."
            )
        ),
    )

    public_text = "\n".join(
        [
            str(
                exercise.get(
                    "scenario",
                    ""
                )
            ),
            str(
                exercise.get(
                    "problem_statement",
                    ""
                )
            ),
            str(
                exercise.get(
                    "learner_goal",
                    ""
                )
            ),
            str(
                exercise.get(
                    "instructions",
                    ""
                )
            ),
            "\n".join(
                str(item)
                for item in
                (
                    constraints
                    if isinstance(
                        constraints,
                        list
                    )
                    else []
                )
            ),
            starter,
        ]
    )

    forbidden_hits = []

    for pattern, label in (
        PUBLIC_FORBIDDEN_PATTERNS
    ):
        if pattern.search(
            public_text
        ):
            forbidden_hits.append(
                label
            )

    no_instrumentation = (
        not forbidden_hits
    )

    add_check(
        report,
        "pedagogy.no_instrumentation",
        "pedagogy",
        (
            "pass"
            if no_instrumentation
            else "fail"
        ),
        (
            "Learner-visible content contains ordinary domain C++ only."
            if no_instrumentation
            else (
                "Learner-visible content leaks internal instrumentation: " +
                ", ".join(
                    sorted(
                        set(
                            forbidden_hits
                        )
                    )
                )
            )
        ),
    )

    if exercise.get(
        "topic"
    ) == "pointers":
        pointer_test_hook_hits = [
            label
            for pattern, label in
            POINTER_LEARNER_TEST_HOOK_PATTERNS
            if pattern.search(
                starter
            )
        ]

        add_check(
            report,
            "pedagogy.pointer_no_test_hooks",
            "pedagogy",
            (
                "pass"
                if not pointer_test_hook_hits
                else "fail"
            ),
            (
                "Pointers learner code exposes no test-only friendship hook."
                if not pointer_test_hook_hits
                else (
                    "Pointers learner code must not expose hidden-test access "
                    "through a friend declaration. Prove pointee identity "
                    "through ordinary public behavior instead. Prefer selecting "
                    "an existing live object, changing that original object "
                    "after selection when the domain permits it, and verifying "
                    "that the holder observes the updated value."
                )
            ),
        )

    direct_hint_hits = [
        pattern.pattern
        for pattern in
        DIRECT_SOLUTION_HINT_PATTERNS
        if pattern.search(
            public_text
        )
    ]

    add_check(
        report,
        "pedagogy.no_direct_syntax_answer",
        "pedagogy",
        (
            "pass"
            if not direct_hint_hits
            else "warn"
        ),
        (
            "Problem statement avoids spelling out the exact solution syntax."
            if not direct_hint_hits
            else (
                "Public text may reveal exact solution syntax. "
                "Review this wording before publication."
            )
        ),
    )

    starter_identifiers = starter_code_identifiers(
        starter
    )

    problem_statement = str(
        exercise.get(
            "problem_statement",
            ""
        )
    )

    named_identifiers = [
        name
        for name in starter_identifiers
        if re.search(
            r"\b" + re.escape(name) + r"\b",
            problem_statement
        )
    ]

    problem_is_specific = (
        bool(
            named_identifiers
        )
        if starter_identifiers
        else True
    )

    add_check(
        report,
        "pedagogy.problem_names_code",
        "pedagogy",
        (
            "pass"
            if problem_is_specific
            else "warn"
        ),
        (
            "Problem statement names concrete code entities: " +
            ", ".join(
                named_identifiers
            )
            if problem_is_specific and named_identifiers
            else (
                "Problem statement should name at least one actual function/class from starter_code so the scenario is concrete."
                if not problem_is_specific
                else "No concrete function/class identifier was extractable from starter_code."
            )
        ),
    )

    concept_checks = exercise.get(
        "concept_checks",
        []
    )

    concept_checks_valid = (
        isinstance(
            concept_checks,
            list
        )
    )

    if concept_checks_valid:
        for index, item in enumerate(
            concept_checks
        ):
            if not isinstance(
                item,
                dict
            ):
                concept_checks_valid = False
                break

            check_type = item.get(
                "type"
            )

            required = (
                CONCEPT_CHECK_REQUIREMENTS.get(
                    check_type
                )
            )

            if required is None:
                concept_checks_valid = False
                break

            if any(
                not non_empty_string(
                    item.get(key)
                )
                for key in required
            ):
                concept_checks_valid = False
                break

    add_check(
        report,
        "schema.concept_checks",
        "schema",
        (
            "pass"
            if concept_checks_valid
            else "fail"
        ),
        (
            f"{len(concept_checks)} semantic check(s) are structurally valid."
            if concept_checks_valid
            else (
                "One or more concept_checks are unsupported "
                "or missing required fields."
            )
        ),
    )

    trace_stream_issues = (
        trace_stream_contract_issues(
            exercise,
            bundled_files
        )
        if exercise.get("trace_mode") == "runtime"
        else []
    )

    add_check(
        report,
        "artifacts.trace_stream_contract",
        "artifacts",
        "pass" if not trace_stream_issues else "fail",
        (
            "All runtime TRACE events are emitted on stderr."
            if not trace_stream_issues
            else (
                "Runtime trace stream issue(s): " +
                " ".join(trace_stream_issues)
            )
        ),
    )

    if topic == "pointers":
        pointer_concept_checks_valid = (
            concept_checks_valid and
            len(
                concept_checks
            ) == 0
        )

        add_check(
            report,
            "schema.pointer_concept_checks",
            "schema",
            (
                "pass"
                if pointer_concept_checks_valid
                else "fail"
            ),
            (
                "Pointers currently uses deterministic hidden behavior "
                "instead of an unrelated AST semantic check."
                if pointer_concept_checks_valid
                else (
                    "Pointers concept_checks must currently be an empty "
                    "array. Do not use References-style checks such as "
                    "const_reference_parameter to stand in for raw-pointer "
                    "behavior; prove pointer behavior with deterministic "
                    "hidden tests until a pointer-specific AST check exists."
                )
            ),
        )

        unsupported_pointer_events = (
            unsupported_pointer_trace_events(
                exercise,
                bundled_files
            )
        )

        add_check(
            report,
            "artifacts.pointer_trace_contract",
            "artifacts",
            (
                "pass"
                if not unsupported_pointer_events
                else "fail"
            ),
            (
                "Pointer hidden instrumentation uses only supported "
                "C++ Teacher trace events."
                if not unsupported_pointer_events
                else (
                    "Unsupported pointer trace event(s): " +
                    ", ".join(
                        unsupported_pointer_events
                    ) +
                    ". Do not invent pointer-only events such as "
                    "CREATE_POINTER, POINTER_DECISION, or READ_POINTER. "
                    "Represent pointer state with CREATE_OBJECT(pointer=...), "
                    "ALLOCATE_RESOURCE, BIND_POINTER, SET_NULL, "
                    "WRITE_VALUE(...through=object.field_), and "
                    "FREE_RESOURCE when a lifetime actually ends."
                )
            ),
        )

        pointer_shape_issues = (
            pointer_trace_shape_issues(
                exercise,
                bundled_files
            )
        )

        add_check(
            report,
            "artifacts.pointer_trace_shape",
            "artifacts",
            (
                "pass"
                if not pointer_shape_issues
                else "fail"
            ),
            (
                "Pointer trace event arguments use supported pointer subjects and "
                "stack-object/resource targets."
                if not pointer_shape_issues
                else (
                    "Pointer trace shape issue(s): " +
                    " ".join(
                        pointer_shape_issues
                    )
                )
            ),
        )

        pointer_provenance_issues = (
            pointer_write_value_provenance_issues(
                exercise,
                bundled_files
            )
        )

        add_check(
            report,
            "artifacts.pointer_write_value_provenance",
            "artifacts",
            (
                "pass"
                if not pointer_provenance_issues
                else "fail"
            ),
            (
                "Pointer WRITE_VALUE provenance uses only traced scopes/aliases, "
                "or omits provenance for direct local-pointer mutations."
                if not pointer_provenance_issues
                else (
                    "Pointer WRITE_VALUE provenance issue(s): " +
                    " ".join(pointer_provenance_issues)
                )
            ),
        )

        pointer_chronology_issues = (
            pointer_trace_chronology_issues(
                exercise,
                bundled_files
            )
        )

        add_check(
            report,
            "artifacts.pointer_trace_chronology",
            "artifacts",
            (
                "pass"
                if not pointer_chronology_issues
                else "fail"
            ),
            (
                "Pointer binding is established in the trace before later "
                "direct stack-pointee mutations."
                if not pointer_chronology_issues
                else (
                    "Pointer trace chronology issue(s): " +
                    " ".join(
                        pointer_chronology_issues
                    )
                )
            ),
        )

    add_difficulty_quality_check(
        exercise,
        report,
        bundled_files
    )

    source_issues = []

    for source_name, source in candidate_cpp_sources(
        exercise,
        bundled_files
    ):
        for issue in cpp_source_safety_issues(source):
            source_issues.append(
                f"{source_name}: {issue}"
            )

    add_check(
        report,
        "safety.generated_cpp",
        "safety",
        "pass" if not source_issues else "fail",
        (
            "Generated C++ passes the pre-execution header/API safety scan."
            if not source_issues
            else (
                "Generated C++ failed the pre-execution safety scan: " +
                "; ".join(source_issues)
            )
        ),
    )

    artifact_specs = [
        (
            "hidden_test_file",
            "tests",
            True
        ),
        (
            "support_file",
            "support",
            False
        ),
        (
            "analysis_support_file",
            "analysis_support",
            False
        ),
    ]

    for (
        field,
        prefix,
        required
    ) in artifact_specs:
        raw = exercise.get(
            field
        )

        if (
            raw is None and
            not required
        ):
            continue

        path = relative_project_path(
            raw,
            prefix
        )

        path_valid = (
            path is not None
        )

        if (
            path_valid and
            exercise_id and
            field == "hidden_test_file"
        ):
            path_valid = (
                path.name.startswith(
                    exercise_id
                )
            )

        exists = False

        if path_valid:
            if bundled_files is not None:
                exists = (
                    path.as_posix()
                    in bundled_files and
                    non_empty_string(
                        bundled_files[
                            path.as_posix()
                        ]
                    )
                )
            else:
                exists = (
                    PROJECT_ROOT /
                    path
                ).exists()

        add_check(
            report,
            f"artifacts.{field}",
            "artifacts",
            (
                "pass"
                if path_valid and exists
                else "fail"
            ),
            (
                f"{field} '{raw}' is available."
                if path_valid and exists
                else (
                    f"{field} must be a safe {prefix}/ path "
                    "and its file content must exist."
                )
            ),
        )

    if bundled_files is not None:
        referenced = {
            str(
                exercise.get(
                    field
                )
            )
            for field in [
                "hidden_test_file",
                "support_file",
                "analysis_support_file",
            ]
            if exercise.get(
                field
            )
        }

        extras = (
            set(
                bundled_files.keys()
            ) -
            referenced
        )

        add_check(
            report,
            "artifacts.no_unreferenced_files",
            "artifacts",
            (
                "pass"
                if not extras
                else "warn"
            ),
            (
                "Candidate bundle contains only referenced hidden artifacts."
                if not extras
                else (
                    "Candidate bundle contains unreferenced files: " +
                    ", ".join(
                        sorted(
                            extras
                        )
                    )
                )
            ),
        )


def timeline_path(
    exercise_id: str
) -> Path:
    return (
        OUTPUT_DIRECTORY /
        (
            f"{exercise_id}"
            "_memory_timeline.json"
        )
    )


def remove_timeline(
    exercise_id: str
):
    path = timeline_path(
        exercise_id
    )

    if path.exists():
        path.unlink()


def load_timeline(
    exercise_id: str
):
    path = timeline_path(
        exercise_id
    )

    if not path.exists():
        return None

    try:
        return load_json(
            path
        )
    except (
        OSError,
        ValueError,
        json.JSONDecodeError
    ):
        return None


def run_grade(
    exercise_path: Path,
    source: str
) -> dict:
    relative = exercise_path.resolve().relative_to(
        PROJECT_ROOT.resolve()
    )

    completed = subprocess.run(
        [
            str(
                CPP_TEACHER_PATH
            ),
            "--grade-json",
            str(relative),
        ],
        cwd=str(
            PROJECT_ROOT
        ),
        input=(
            source
            if source.endswith("\n")
            else source + "\n"
        ),
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            "cpp_teacher failed while validating exercise:\n" +
            completed.stderr
        )

    try:
        grade = json.loads(
            completed.stdout
        )
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "cpp_teacher did not return valid grade JSON."
        ) from error

    return grade


def timeline_detail_value(
    detail: Any,
    key: str
) -> str:
    if not isinstance(
        detail,
        str
    ):
        return ""

    prefix = key + "="

    for part in detail.split("|"):
        if part.startswith(prefix):
            return part[
                len(prefix):
            ].strip()

    return ""


def timeline_pointer_object(
    pointer_name: str
) -> str:
    if not isinstance(
        pointer_name,
        str
    ):
        return ""

    return pointer_name.split(
        ".",
        1
    )[0].strip()


def timeline_move_pointers(
    detail: Any
) -> tuple[str, str]:
    if not isinstance(
        detail,
        str
    ):
        return ("", "")

    movement = detail.split(
        "|",
        1
    )[0]

    if "->" not in movement:
        return ("", "")

    source, destination = (
        movement.split(
            "->",
            1
        )
    )

    return (
        source.strip(),
        destination.strip(),
    )


def validate_timeline_integrity(
    timeline: Any
) -> list[str]:
    issues: list[str] = []

    if not isinstance(
        timeline,
        dict
    ):
        return [
            "Timeline document is not an object."
        ]

    frames = timeline.get(
        "timeline"
    )

    if not isinstance(
        frames,
        list
    ):
        return [
            "Timeline does not contain a timeline array."
        ]

    previous_scopes: list[str] = []

    for index, frame in enumerate(
        frames
    ):
        if not isinstance(
            frame,
            dict
        ):
            issues.append(
                f"snapshot {index + 1}: frame is not an object"
            )
            continue

        expected_step = (
            index + 1
        )

        if frame.get(
            "step"
        ) != expected_step:
            issues.append(
                (
                    f"snapshot {expected_step}: expected step "
                    f"{expected_step}, got {frame.get('step')!r}"
                )
            )

        scopes = frame.get(
            "active_scopes",
            []
        )

        if not isinstance(
            scopes,
            list
        ) or not all(
            isinstance(
                scope,
                str
            )
            for scope in scopes
        ):
            issues.append(
                (
                    f"snapshot {expected_step}: "
                    "active_scopes must be a string array"
                )
            )

            scopes = []

        cause = frame.get(
            "cause",
            {}
        )

        if not isinstance(
            cause,
            dict
        ):
            issues.append(
                (
                    f"snapshot {expected_step}: "
                    "cause is not an object"
                )
            )

            cause = {}

        event_type = cause.get(
            "type",
            ""
        )

        subject = cause.get(
            "subject",
            ""
        )

        detail = cause.get(
            "detail",
            ""
        )

        stack_values = frame.get(
            "stack_values",
            []
        )

        aliases = frame.get(
            "aliases",
            []
        )

        objects = frame.get(
            "stack",
            []
        )

        heap = frame.get(
            "heap",
            []
        )

        for field_name, value in [
            ("stack_values", stack_values),
            ("aliases", aliases),
            ("stack", objects),
            ("heap", heap),
        ]:
            if not isinstance(
                value,
                list
            ):
                issues.append(
                    (
                        f"snapshot {expected_step}: "
                        f"{field_name} must be an array"
                    )
                )

        stack_values = (
            stack_values
            if isinstance(
                stack_values,
                list
            )
            else []
        )

        aliases = (
            aliases
            if isinstance(
                aliases,
                list
            )
            else []
        )

        objects = (
            objects
            if isinstance(
                objects,
                list
            )
            else []
        )

        heap = (
            heap
            if isinstance(
                heap,
                list
            )
            else []
        )

        value_map = {
            item.get(
                "name"
            ): item
            for item in stack_values
            if isinstance(
                item,
                dict
            ) and isinstance(
                item.get(
                    "name"
                ),
                str
            )
        }

        alias_map = {
            item.get(
                "name"
            ): item
            for item in aliases
            if isinstance(
                item,
                dict
            ) and isinstance(
                item.get(
                    "name"
                ),
                str
            )
        }

        object_map = {
            item.get(
                "name"
            ): item
            for item in objects
            if isinstance(
                item,
                dict
            ) and isinstance(
                item.get(
                    "name"
                ),
                str
            )
        }

        resource_map = {
            item.get(
                "id"
            ): item
            for item in heap
            if isinstance(
                item,
                dict
            ) and isinstance(
                item.get(
                    "id"
                ),
                str
            )
        }

        # Every currently alive alias must point at a real, alive stack
        # entity. References may bind to scalar values or class objects.
        for alias_name, alias in (
            alias_map.items()
        ):
            if not alias.get(
                "alive",
                True
            ):
                continue

            target = alias.get(
                "target"
            )

            target_state = (
                value_map.get(
                    target
                ) or
                object_map.get(
                    target
                )
            )

            if target_state is None:
                issues.append(
                    (
                        f"snapshot {expected_step}: alive alias "
                        f"'{alias_name}' targets unknown stack value "
                        f"or stack object '{target}'"
                    )
                )
            elif not target_state.get(
                "alive",
                True
            ):
                issues.append(
                    (
                        f"snapshot {expected_step}: alive alias "
                        f"'{alias_name}' targets dead stack value "
                        f"or stack object '{target}'"
                    )
                )

        # Alive values/aliases with a named scope should live inside an active scope.
        for collection_name, mapping in [
            ("stack value", value_map),
            ("alias", alias_map),
        ]:
            for name, item in mapping.items():
                if not item.get(
                    "alive",
                    True
                ):
                    continue

                scope_name = item.get(
                    "scope"
                )

                if (
                    isinstance(
                        scope_name,
                        str
                    ) and
                    scope_name and
                    scope_name not in scopes
                ):
                    issues.append(
                        (
                            f"snapshot {expected_step}: alive {collection_name} "
                            f"'{name}' belongs to inactive scope "
                            f"'{scope_name}'"
                        )
                    )

        if event_type == "ENTER_SCOPE":
            expected_scopes = (
                previous_scopes +
                [subject]
            )

            if scopes != expected_scopes:
                issues.append(
                    (
                        f"snapshot {expected_step}: ENTER_SCOPE "
                        f"'{subject}' should change active scopes from "
                        f"{previous_scopes!r} to {expected_scopes!r}, "
                        f"got {scopes!r}"
                    )
                )

        elif event_type == "EXIT_SCOPE":
            if (
                not previous_scopes or
                previous_scopes[-1] !=
                    subject
            ):
                issues.append(
                    (
                        f"snapshot {expected_step}: EXIT_SCOPE "
                        f"'{subject}' has no matching active top scope; "
                        f"previous scopes were {previous_scopes!r}"
                    )
                )
            else:
                expected_scopes = (
                    previous_scopes[:-1]
                )

                if scopes != expected_scopes:
                    issues.append(
                        (
                            f"snapshot {expected_step}: EXIT_SCOPE "
                            f"'{subject}' should leave scopes "
                            f"{expected_scopes!r}, got {scopes!r}"
                        )
                    )

        elif event_type == "BIND_ALIAS":
            alias = alias_map.get(
                subject
            )

            target = timeline_detail_value(
                detail,
                "target"
            )

            if alias is None:
                issues.append(
                    (
                        f"snapshot {expected_step}: BIND_ALIAS "
                        f"'{subject}' did not create an alias state"
                    )
                )
            else:
                if alias.get(
                    "target"
                ) != target:
                    issues.append(
                        (
                            f"snapshot {expected_step}: BIND_ALIAS "
                            f"'{subject}' state target does not match "
                            f"event target '{target}'"
                        )
                    )

            if (
                target not in value_map and
                target not in object_map
            ):
                issues.append(
                    (
                        f"snapshot {expected_step}: BIND_ALIAS "
                        f"'{subject}' targets '{target}', but no stack "
                        "value or stack object with that exact name exists"
                    )
                )

        elif event_type == "WRITE_VALUE":
            if (
                subject not in value_map and
                subject not in resource_map and
                subject not in object_map
            ):
                issues.append(
                    (
                        f"snapshot {expected_step}: WRITE_VALUE "
                        f"targets unknown stack value, stack object, or "
                        f"heap resource '{subject}'"
                    )
                )

            if (
                subject in object_map and
                not timeline_detail_value(
                    detail,
                    "value"
                )
            ):
                issues.append(
                    (
                        f"snapshot {expected_step}: WRITE_VALUE for "
                        f"stack object '{subject}' must include "
                        "value=field=value metadata"
                    )
                )

            via = timeline_detail_value(
                detail,
                "via"
            )

            if (
                via and
                via not in scopes and
                via not in alias_map
            ):
                issues.append(
                    (
                        f"snapshot {expected_step}: WRITE_VALUE "
                        f"uses via='{via}', but that name is neither "
                        "an active scope nor an alias"
                    )
                )

            through = (
                timeline_detail_value(
                    detail,
                    "through"
                ) or
                timeline_detail_value(
                    detail,
                    "via_pointer"
                )
            )

            if through:
                object_name = timeline_pointer_object(
                    through
                )

                field_name = (
                    through.split(
                        ".",
                        1
                    )[1]
                    if "." in through
                    else ""
                )

                obj = object_map.get(
                    object_name
                )

                if obj is None:
                    issues.append(
                        (
                            f"snapshot {expected_step}: WRITE_VALUE "
                            f"through='{through}' references unknown "
                            f"object '{object_name}'"
                        )
                    )
                else:
                    fields = obj.get(
                        "fields",
                        {}
                    )

                    field = (
                        fields.get(
                            field_name
                        )
                        if isinstance(
                            fields,
                            dict
                        )
                        else None
                    )

                    if (
                        not isinstance(
                            field,
                            dict
                        ) or
                        field.get(
                            "points_to"
                        ) != subject
                    ):
                        issues.append(
                            (
                                f"snapshot {expected_step}: WRITE_VALUE "
                                f"through='{through}' does not point to "
                                f"'{subject}'"
                            )
                        )

        elif event_type == "ALLOCATE_RESOURCE":
            resource = resource_map.get(
                subject
            )

            if resource is None:
                issues.append(
                    (
                        f"snapshot {expected_step}: "
                        f"ALLOCATE_RESOURCE '{subject}' did not create "
                        "a heap resource"
                    )
                )
            elif not resource.get(
                "alive",
                True
            ):
                issues.append(
                    (
                        f"snapshot {expected_step}: newly allocated "
                        f"resource '{subject}' is not alive"
                    )
                )

        elif event_type == "BIND_POINTER":
            object_name = (
                timeline_pointer_object(
                    subject
                )
            )

            obj = object_map.get(
                object_name
            )

            target_name = str(
                detail
            ).strip()

            resource = resource_map.get(
                target_name
            )

            target_object = object_map.get(
                target_name
            )

            if obj is None:
                issues.append(
                    (
                        f"snapshot {expected_step}: BIND_POINTER "
                        f"references unknown holder object '{object_name}'"
                    )
                )

            if (
                resource is None and
                target_object is None
            ):
                issues.append(
                    (
                        f"snapshot {expected_step}: BIND_POINTER "
                        f"references unknown pointee '{target_name}'; "
                        "expected a live stack object or heap resource"
                    )
                )

            if (
                isinstance(
                    target_object,
                    dict
                ) and
                not target_object.get(
                    "alive",
                    True
                )
            ):
                issues.append(
                    (
                        f"snapshot {expected_step}: BIND_POINTER "
                        f"targets dead stack object '{target_name}'"
                    )
                )

        elif event_type == "SET_NULL":
            object_name = timeline_pointer_object(
                subject
            )

            field_name = (
                subject.split(
                    ".",
                    1
                )[1]
                if "." in subject
                else ""
            )

            obj = object_map.get(
                object_name
            )

            if obj is None:
                issues.append(
                    (
                        f"snapshot {expected_step}: SET_NULL "
                        f"references unknown object '{object_name}'"
                    )
                )
            else:
                fields = obj.get(
                    "fields",
                    {}
                )

                field = (
                    fields.get(
                        field_name
                    )
                    if isinstance(
                        fields,
                        dict
                    )
                    else None
                )

                if (
                    not isinstance(
                        field,
                        dict
                    ) or
                    field.get(
                        "points_to"
                    )
                ):
                    issues.append(
                        (
                            f"snapshot {expected_step}: SET_NULL "
                            f"did not clear pointer '{subject}'"
                        )
                    )

        elif event_type == "MOVE_RESOURCE":
            resource = resource_map.get(
                subject
            )

            if resource is None:
                issues.append(
                    (
                        f"snapshot {expected_step}: MOVE_RESOURCE "
                        f"references unknown resource '{subject}'"
                    )
                )

            source_pointer, destination_pointer = (
                timeline_move_pointers(
                    detail
                )
            )

            source_object = (
                timeline_pointer_object(
                    source_pointer
                )
            )

            destination_object = (
                timeline_pointer_object(
                    destination_pointer
                )
            )

            if source_object not in object_map:
                issues.append(
                    (
                        f"snapshot {expected_step}: MOVE_RESOURCE "
                        f"source object '{source_object}' does not exist"
                    )
                )

            destination = object_map.get(
                destination_object
            )

            if destination is None:
                issues.append(
                    (
                        f"snapshot {expected_step}: MOVE_RESOURCE "
                        f"destination object '{destination_object}' "
                        "does not exist"
                    )
                )
            else:
                fields = destination.get(
                    "fields",
                    {}
                )

                destination_points = [
                    value.get(
                        "points_to"
                    )
                    for value in (
                        fields.values()
                        if isinstance(
                            fields,
                            dict
                        )
                        else []
                    )
                    if isinstance(
                        value,
                        dict
                    )
                ]

                if subject not in destination_points:
                    issues.append(
                        (
                            f"snapshot {expected_step}: MOVE_RESOURCE "
                            f"destination '{destination_pointer}' does "
                            f"not point to resource '{subject}'"
                        )
                    )

        elif event_type == "FREE_RESOURCE":
            resource = resource_map.get(
                subject
            )

            if resource is None:
                issues.append(
                    (
                        f"snapshot {expected_step}: FREE_RESOURCE "
                        f"references unknown resource '{subject}'"
                    )
                )
            elif resource.get(
                "alive",
                True
            ):
                issues.append(
                    (
                        f"snapshot {expected_step}: FREE_RESOURCE "
                        f"left resource '{subject}' alive"
                    )
                )

        elif event_type == "DESTROY_BEGIN":
            obj = object_map.get(
                subject
            )

            if obj is None:
                issues.append(
                    (
                        f"snapshot {expected_step}: DESTROY_BEGIN "
                        f"references unknown object '{subject}'"
                    )
                )
            elif obj.get(
                "lifetime"
            ) != "destroying":
                issues.append(
                    (
                        f"snapshot {expected_step}: DESTROY_BEGIN "
                        f"did not put '{subject}' in destroying state"
                    )
                )

        elif event_type in {
            "DESTROY_END",
            "DESTROY_OBJECT",
        }:
            obj = object_map.get(
                subject
            )

            if obj is None:
                issues.append(
                    (
                        f"snapshot {expected_step}: {event_type} "
                        f"references unknown object '{subject}'"
                    )
                )
            elif obj.get(
                "alive",
                True
            ):
                issues.append(
                    (
                        f"snapshot {expected_step}: {event_type} "
                        f"left object '{subject}' alive"
                    )
                )

        previous_scopes = list(
            scopes
        )

    if previous_scopes:
        issues.append(
            (
                "Timeline ends with unclosed active scopes: " +
                ", ".join(
                    previous_scopes
                )
            )
        )

    return sorted(
        set(
            issues
        )
    )


def validate_timeline_document(
    timeline: Any
) -> tuple[bool, str]:
    if not isinstance(
        timeline,
        dict
    ):
        return (
            False,
            "Timeline file was not generated."
        )

    frames = timeline.get(
        "timeline"
    )

    if not isinstance(
        frames,
        list
    ):
        return (
            False,
            "Timeline does not contain a timeline array."
        )

    if len(frames) < 2:
        return (
            False,
            (
                "Timeline must contain at least two snapshots "
                "to provide a meaningful visualization."
            )
        )

    return (
        True,
        (
            f"Visualization contains {len(frames)} snapshots."
        )
    )



REFERENCE_PARAMETER_CHECK_TYPES = {
    "non_const_reference_parameter",
    "const_reference_parameter",
}


def _find_matching_paren(
    source: str,
    open_index: int
) -> int | None:
    depth = 0
    in_string = False
    in_char = False
    escaped = False

    for index in range(
        open_index,
        len(source)
    ):
        ch = source[index]

        if escaped:
            escaped = False
            continue

        if ch == "\\" and (
            in_string or
            in_char
        ):
            escaped = True
            continue

        if ch == '"' and not in_char:
            in_string = not in_string
            continue

        if ch == "'" and not in_string:
            in_char = not in_char
            continue

        if in_string or in_char:
            continue

        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return index

    return None


def _split_parameter_spans(
    source: str,
    start: int,
    end: int
) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    segment_start = start
    angle_depth = 0
    paren_depth = 0
    bracket_depth = 0
    brace_depth = 0
    in_string = False
    in_char = False
    escaped = False

    for index in range(
        start,
        end
    ):
        ch = source[index]

        if escaped:
            escaped = False
            continue

        if ch == "\\" and (
            in_string or
            in_char
        ):
            escaped = True
            continue

        if ch == '"' and not in_char:
            in_string = not in_string
            continue

        if ch == "'" and not in_string:
            in_char = not in_char
            continue

        if in_string or in_char:
            continue

        if ch == "<":
            angle_depth += 1
        elif ch == ">" and angle_depth > 0:
            angle_depth -= 1
        elif ch == "(":
            paren_depth += 1
        elif ch == ")" and paren_depth > 0:
            paren_depth -= 1
        elif ch == "[":
            bracket_depth += 1
        elif ch == "]" and bracket_depth > 0:
            bracket_depth -= 1
        elif ch == "{":
            brace_depth += 1
        elif ch == "}" and brace_depth > 0:
            brace_depth -= 1
        elif (
            ch == "," and
            angle_depth == 0 and
            paren_depth == 0 and
            bracket_depth == 0 and
            brace_depth == 0
        ):
            spans.append(
                (
                    segment_start,
                    index
                )
            )
            segment_start = index + 1

    spans.append(
        (
            segment_start,
            end
        )
    )

    return spans


def parameter_declaration_span(
    source: str,
    function_name: str,
    parameter_name: str
) -> tuple[int, int, str] | None:
    pattern = re.compile(
        r"\b" +
        re.escape(function_name) +
        r"\s*\("
    )

    for match in pattern.finditer(
        source
    ):
        open_index = source.find(
            "(",
            match.start()
        )

        if open_index < 0:
            continue

        close_index = _find_matching_paren(
            source,
            open_index
        )

        if close_index is None:
            continue

        for raw_start, raw_end in (
            _split_parameter_spans(
                source,
                open_index + 1,
                close_index
            )
        ):
            fragment = source[
                raw_start:raw_end
            ]

            if re.search(
                r"\b" +
                re.escape(parameter_name) +
                r"\b",
                fragment
            ):
                leading = len(fragment) - len(
                    fragment.lstrip()
                )
                trailing = len(fragment) - len(
                    fragment.rstrip()
                )

                start = raw_start + leading
                end = raw_end - trailing

                return (
                    start,
                    end,
                    source[start:end]
                )

    return None


def reference_probe_name(
    concept_check: dict
) -> str:
    return (
        str(
            concept_check.get(
                "function",
                ""
            )
        ) +
        "." +
        str(
            concept_check.get(
                "parameter",
                ""
            )
        )
    )


def synthesize_reference_probe_set(
    starter_source: str,
    reference_source: str,
    concept_checks: list[dict]
) -> tuple[
    str | None,
    list[str],
    str
]:
    replacements = []
    details = []
    seen_spans = set()

    for concept_check in concept_checks:
        function_name = concept_check.get(
            "function"
        )

        parameter_name = concept_check.get(
            "parameter"
        )

        if not (
            isinstance(
                function_name,
                str
            ) and
            function_name and
            isinstance(
                parameter_name,
                str
            ) and
            parameter_name
        ):
            return (
                None,
                [],
                (
                    "concept check has no "
                    "function/parameter name"
                ),
            )

        starter_span = (
            parameter_declaration_span(
                starter_source,
                function_name,
                parameter_name
            )
        )

        reference_span = (
            parameter_declaration_span(
                reference_source,
                function_name,
                parameter_name
            )
        )

        label = (
            function_name +
            "." +
            parameter_name
        )

        if starter_span is None:
            return (
                None,
                [],
                (
                    "could not locate starter "
                    f"declaration for {label}"
                ),
            )

        if reference_span is None:
            return (
                None,
                [],
                (
                    "could not locate reference "
                    f"declaration for {label}"
                ),
            )

        (
            starter_start,
            starter_end,
            starter_decl,
        ) = starter_span

        (
            _,
            _,
            reference_decl,
        ) = reference_span

        span_key = (
            starter_start,
            starter_end,
        )

        if span_key in seen_spans:
            return (
                None,
                [],
                (
                    "multiple concept checks resolve "
                    f"to the same starter declaration: {label}"
                ),
            )

        seen_spans.add(
            span_key
        )

        if (
            starter_decl.strip() ==
            reference_decl.strip()
        ):
            return (
                None,
                [],
                (
                    "starter declaration for "
                    f"{label} already matches "
                    "the reference declaration"
                ),
            )

        replacements.append(
            (
                starter_start,
                starter_end,
                reference_decl,
            )
        )

        details.append(
            (
                f"{label}: "
                f"{starter_decl.strip()} -> "
                f"{reference_decl.strip()}"
            )
        )

    probe_source = (
        starter_source
    )

    for (
        start,
        end,
        replacement,
    ) in sorted(
        replacements,
        key=lambda item:
            item[0],
        reverse=True
    ):
        probe_source = (
            probe_source[:start] +
            replacement +
            probe_source[end:]
        )

    return (
        probe_source,
        details,
        (
            "; ".join(
                details
            )
        ),
    )


def hard_reference_probe_pairs(
    concept_checks: list[dict]
) -> list[
    tuple[
        dict,
        dict,
    ]
]:
    result = []

    for first_index in range(
        len(
            concept_checks
        )
    ):
        for second_index in range(
            first_index + 1,
            len(
                concept_checks
            )
        ):
            result.append(
                (
                    concept_checks[
                        first_index
                    ],
                    concept_checks[
                        second_index
                    ],
                )
            )

    return result


def synthesize_single_reference_probe(
    starter_source: str,
    reference_source: str,
    concept_check: dict
) -> tuple[str | None, str]:
    (
        probe_source,
        _,
        detail,
    ) = synthesize_reference_probe_set(
        starter_source,
        reference_source,
        [
            concept_check
        ]
    )

    return (
        probe_source,
        detail,
    )


def timeline_has_reference_binding(
    timeline: Any,
    *,
    function_name: str,
    parameter_name: str,
    expected_const: bool
) -> tuple[bool, str]:
    if not isinstance(
        timeline,
        dict
    ):
        return (
            False,
            "probe did not generate a timeline object"
        )

    frames = timeline.get(
        "timeline"
    )

    if not isinstance(
        frames,
        list
    ):
        return (
            False,
            "probe timeline has no timeline array"
        )

    bindings = []

    for frame in frames:
        if not isinstance(
            frame,
            dict
        ):
            continue

        cause = frame.get(
            "cause",
            {}
        )

        if not isinstance(
            cause,
            dict
        ):
            continue

        if (
            cause.get("type") != "BIND_ALIAS" or
            cause.get("subject") != parameter_name
        ):
            continue

        scopes = frame.get(
            "active_scopes",
            []
        )

        if (
            not isinstance(scopes, list) or
            function_name not in scopes
        ):
            continue

        detail = cause.get(
            "detail",
            ""
        )

        target = timeline_detail_value(
            detail,
            "target"
        )
        const_text = timeline_detail_value(
            detail,
            "const"
        ).lower()

        bindings.append(
            (
                target,
                const_text
            )
        )

    if not bindings:
        return (
            False,
            (
                f"no BIND_ALIAS for parameter '{parameter_name}' "
                f"was recorded while scope '{function_name}' was active"
            )
        )

    expected_const_text = (
        "true"
        if expected_const
        else "false"
    )

    if not any(
        target and
        const_text == expected_const_text
        for target, const_text in bindings
    ):
        return (
            False,
            (
                f"BIND_ALIAS for '{parameter_name}' did not record "
                f"const={expected_const_text} with a real target"
            )
        )

    targets = sorted(
        {
            target
            for target, _ in bindings
            if target
        }
    )

    if not expected_const:
        write_found = False

        for frame in frames:
            if not isinstance(
                frame,
                dict
            ):
                continue

            cause = frame.get(
                "cause",
                {}
            )

            if not isinstance(
                cause,
                dict
            ):
                continue

            if (
                cause.get("type") != "WRITE_VALUE" or
                cause.get("subject") not in targets
            ):
                continue

            scopes = frame.get(
                "active_scopes",
                []
            )

            if (
                not isinstance(scopes, list) or
                function_name not in scopes
            ):
                continue

            via = timeline_detail_value(
                cause.get(
                    "detail",
                    ""
                ),
                "via"
            )

            if via in {
                parameter_name,
                function_name,
            }:
                write_found = True
                break

        if not write_found:
            return (
                False,
                (
                    f"'{parameter_name}' was shown as an alias, but the "
                    "partial-probe timeline never showed the aliased caller "
                    "value being written while the function scope was active"
                )
            )

    return (
        True,
        (
            f"partial probe visualized '{parameter_name}' as a "
            f"{'const ' if expected_const else ''}reference alias "
            f"to {', '.join(targets)}" +
            (
                " and preserved the caller-value write"
                if not expected_const
                else ""
            )
        )
    )


def validate_partial_reference_probes(
    exercise: dict,
    exercise_path: Path,
    report: ValidationReport,
):
    concept_checks = [
        check
        for check in exercise.get(
            "concept_checks",
            []
        )
        if (
            isinstance(check, dict) and
            check.get("type") in
                REFERENCE_PARAMETER_CHECK_TYPES
        )
    ]

    if len(concept_checks) < 2:
        return

    starter_source = exercise.get(
        "starter_code",
        ""
    )
    reference_source = exercise.get(
        "reference_solution",
        ""
    )
    exercise_id = exercise.get(
        "id",
        ""
    )

    for concept_check in concept_checks:
        function_name = str(
            concept_check.get(
                "function",
                ""
            )
        )
        parameter_name = str(
            concept_check.get(
                "parameter",
                ""
            )
        )
        check_type = concept_check.get(
            "type"
        )
        expected_const = (
            check_type ==
            "const_reference_parameter"
        )
        check_id = (
            "runtime.partial_probe." +
            function_name +
            "." +
            parameter_name
        )

        probe_source, synthesis_detail = (
            synthesize_single_reference_probe(
                starter_source,
                reference_source,
                concept_check
            )
        )

        if probe_source is None:
            add_check(
                report,
                check_id,
                "visualization",
                "fail",
                (
                    "Could not synthesize a one-fix partial solution: " +
                    synthesis_detail
                ),
            )
            continue

        try:
            remove_timeline(
                exercise_id
            )

            probe_grade = run_grade(
                exercise_path,
                probe_source
            )
            probe_timeline = load_timeline(
                exercise_id
            )
        except (
            RuntimeError,
            subprocess.TimeoutExpired
        ) as error:
            add_check(
                report,
                check_id,
                "visualization",
                "fail",
                (
                    "Partial solution probe could not run: " +
                    str(error)
                ),
            )
            continue

        probe_compiles = bool(
            probe_grade.get(
                "compilation",
                {}
            ).get(
                "passed",
                False
            )
        )

        if not probe_compiles:
            diagnostics = probe_grade.get(
                "compilation",
                {}
            ).get(
                "diagnostics",
                ""
            )

            add_check(
                report,
                check_id,
                "visualization",
                "fail",
                (
                    "Synthesized one-fix partial solution did not compile. "
                    f"Applied: {synthesis_detail}. Diagnostics: " +
                    str(diagnostics)[:2000]
                ),
            )
            continue

        probe_overall_passed = (
            probe_grade.get(
                "passed"
            ) is True
        )

        if probe_overall_passed:
            add_check(
                report,
                check_id,
                "visualization",
                "fail",
                (
                    "A one-fix partial solution unexpectedly passed the whole "
                    "multi-concept exercise. Hidden grading may not enforce the "
                    "other declared concepts independently. Applied: " +
                    synthesis_detail
                ),
            )
            continue

        timeline_valid, timeline_message = (
            validate_timeline_document(
                probe_timeline
            )
        )

        if not timeline_valid:
            add_check(
                report,
                check_id,
                "visualization",
                "fail",
                (
                    "Partial solution probe compiled but did not produce "
                    "a meaningful timeline. " +
                    timeline_message
                ),
            )
            continue

        integrity_issues = (
            validate_timeline_integrity(
                probe_timeline
            )
        )

        if integrity_issues:
            add_check(
                report,
                check_id,
                "visualization",
                "fail",
                (
                    "Partial solution timeline is internally inconsistent: " +
                    "; ".join(
                        integrity_issues
                    )
                ),
            )
            continue

        represented, representation_detail = (
            timeline_has_reference_binding(
                probe_timeline,
                function_name=function_name,
                parameter_name=parameter_name,
                expected_const=expected_const,
            )
        )

        add_check(
            report,
            check_id,
            "visualization",
            (
                "pass"
                if represented
                else "fail"
            ),
            (
                (
                    "One-fix partial solution is represented correctly. "
                    f"Applied: {synthesis_detail}. " +
                    representation_detail
                )
                if represented
                else (
                    "One-fix partial solution is NOT represented correctly. "
                    f"Applied: {synthesis_detail}. " +
                    representation_detail +
                    " Hidden instrumentation must classify each parameter "
                    "independently instead of using one all-or-nothing "
                    "signature boolean."
                )
            ),
        )


def validate_pairwise_reference_probes(
    exercise: dict,
    exercise_path: Path,
    report: ValidationReport,
):
    if (
        exercise.get(
            "topic"
        ) != "references" or
        exercise.get(
            "difficulty"
        ) != "hard"
    ):
        return

    concept_checks = [
        check
        for check in exercise.get(
            "concept_checks",
            []
        )
        if (
            isinstance(
                check,
                dict
            ) and
            check.get(
                "type"
            ) in
            REFERENCE_PARAMETER_CHECK_TYPES
        )
    ]

    if len(
        concept_checks
    ) < 4:
        # difficulty.quality will already explain why
        # this is not a valid Hard References exercise.
        return

    starter_source = str(
        exercise.get(
            "starter_code",
            ""
        )
    )

    reference_source = str(
        exercise.get(
            "reference_solution",
            ""
        )
    )

    exercise_id = str(
        exercise.get(
            "id",
            ""
        )
    )

    for (
        first_check,
        second_check,
    ) in hard_reference_probe_pairs(
        concept_checks
    ):
        first_name = (
            reference_probe_name(
                first_check
            )
        )

        second_name = (
            reference_probe_name(
                second_check
            )
        )

        check_id = (
            "runtime.combined_probe." +
            first_name +
            "__" +
            second_name
        )

        (
            probe_source,
            synthesis_details,
            synthesis_summary,
        ) = synthesize_reference_probe_set(
            starter_source,
            reference_source,
            [
                first_check,
                second_check,
            ]
        )

        if probe_source is None:
            add_check(
                report,
                check_id,
                "visualization",
                "fail",
                (
                    "Could not synthesize a two-fix "
                    "combined solution: " +
                    synthesis_summary
                ),
            )

            continue

        try:
            remove_timeline(
                exercise_id
            )

            probe_grade = run_grade(
                exercise_path,
                probe_source
            )

            probe_timeline = load_timeline(
                exercise_id
            )
        except (
            RuntimeError,
            subprocess.TimeoutExpired
        ) as error:
            add_check(
                report,
                check_id,
                "visualization",
                "fail",
                (
                    "Combined partial solution "
                    "probe could not run: " +
                    str(
                        error
                    )
                ),
            )

            continue

        probe_compiles = bool(
            probe_grade.get(
                "compilation",
                {}
            ).get(
                "passed",
                False
            )
        )

        if not probe_compiles:
            diagnostics = (
                probe_grade.get(
                    "compilation",
                    {}
                ).get(
                    "diagnostics",
                    ""
                )
            )

            add_check(
                report,
                check_id,
                "visualization",
                "fail",
                (
                    "Synthesized two-fix partial "
                    "solution did not compile. "
                    f"Applied: {synthesis_summary}. "
                    "Diagnostics: " +
                    str(
                        diagnostics
                    )[:2000]
                ),
            )

            continue

        if (
            probe_grade.get(
                "passed"
            ) is True
        ):
            add_check(
                report,
                check_id,
                "visualization",
                "fail",
                (
                    "A two-fix partial solution "
                    "unexpectedly passed the whole Hard "
                    "References exercise. Hidden grading "
                    "may not enforce the remaining concepts "
                    "independently. Applied: " +
                    synthesis_summary
                ),
            )

            continue

        (
            timeline_valid,
            timeline_message,
        ) = validate_timeline_document(
            probe_timeline
        )

        if not timeline_valid:
            add_check(
                report,
                check_id,
                "visualization",
                "fail",
                (
                    "Combined partial solution compiled "
                    "but did not produce a meaningful "
                    "timeline. " +
                    timeline_message
                ),
            )

            continue

        integrity_issues = (
            validate_timeline_integrity(
                probe_timeline
            )
        )

        if integrity_issues:
            add_check(
                report,
                check_id,
                "visualization",
                "fail",
                (
                    "Combined partial solution timeline "
                    "is internally inconsistent: " +
                    "; ".join(
                        integrity_issues
                    )
                ),
            )

            continue

        representation_details = []
        representation_failures = []

        for concept_check in [
            first_check,
            second_check,
        ]:
            function_name = str(
                concept_check.get(
                    "function",
                    ""
                )
            )

            parameter_name = str(
                concept_check.get(
                    "parameter",
                    ""
                )
            )

            expected_const = (
                concept_check.get(
                    "type"
                ) ==
                "const_reference_parameter"
            )

            (
                represented,
                representation_detail,
            ) = timeline_has_reference_binding(
                probe_timeline,
                function_name=function_name,
                parameter_name=parameter_name,
                expected_const=expected_const,
            )

            if represented:
                representation_details.append(
                    (
                        f"{function_name}."
                        f"{parameter_name}: "
                        f"{representation_detail}"
                    )
                )
            else:
                representation_failures.append(
                    (
                        f"{function_name}."
                        f"{parameter_name}: "
                        f"{representation_detail}"
                    )
                )

        pair_is_valid = (
            not representation_failures
        )

        add_check(
            report,
            check_id,
            "visualization",
            (
                "pass"
                if pair_is_valid
                else "fail"
            ),
            (
                (
                    "Two-fix combined solution is "
                    "represented correctly. Applied: " +
                    synthesis_summary +
                    ". Both fixes coexist in one timeline: " +
                    "; ".join(
                        representation_details
                    )
                )
                if pair_is_valid
                else (
                    "Two-fix combined solution is NOT "
                    "represented correctly. Applied: " +
                    synthesis_summary +
                    ". Missing/incorrect representation: " +
                    "; ".join(
                        representation_failures
                    ) +
                    ". Hard References instrumentation "
                    "must preserve multiple simultaneous "
                    "partial fixes instead of treating them "
                    "as isolated cases."
                )
            ),
        )


def runtime_validate(
    exercise: dict,
    exercise_path: Path,
    report: ValidationReport,
):
    if not CPP_TEACHER_PATH.exists():
        add_check(
            report,
            "runtime.grader_built",
            "environment",
            "fail",
            (
                "build/cpp_teacher does not exist. "
                "Build the project before full validation."
            ),
        )

        return

    add_check(
        report,
        "runtime.grader_built",
        "environment",
        "pass",
        "C++ grader executable is available.",
    )

    exercise_id = exercise[
        "id"
    ]

    try:
        remove_timeline(
            exercise_id
        )

        starter_grade = run_grade(
            exercise_path,
            exercise[
                "starter_code"
            ]
        )

        starter_timeline = load_timeline(
            exercise_id
        )
    except (
        RuntimeError,
        subprocess.TimeoutExpired
    ) as error:
        add_check(
            report,
            "runtime.starter_execution",
            "runtime",
            "fail",
            str(error),
        )

        return

    starter_compiles = bool(
        starter_grade.get(
            "compilation",
            {}
        ).get(
            "passed",
            False
        )
    )

    add_check(
        report,
        "runtime.starter_compiles",
        "runtime",
        (
            "pass"
            if starter_compiles
            else "fail"
        ),
        (
            "Starter code compiles successfully."
            if starter_compiles
            else (
                "Starter code must compile. The exercise should "
                "present a real behavioral/design problem, not a syntax stub."
            )
        ),
    )

    starter_rejected = (
        starter_grade.get(
            "passed"
        ) is False
    )

    add_check(
        report,
        "runtime.starter_rejected",
        "runtime",
        (
            "pass"
            if starter_rejected
            else "fail"
        ),
        (
            "Starter code is correctly rejected by the grader."
            if starter_rejected
            else (
                "Starter code already passes; the learner would have "
                "nothing meaningful to solve."
            )
        ),
    )

    starter_hidden = (
        starter_grade.get(
            "hidden_tests",
            {}
        )
    )

    starter_hidden_used = bool(
        starter_hidden.get(
            "used",
            False
        )
    )

    starter_hidden_failed = (
        starter_hidden_used and
        starter_hidden.get(
            "passed"
        ) is False
    )

    add_check(
        report,
        "runtime.starter_hidden_tests_fail",
        "runtime",
        (
            "pass"
            if starter_hidden_failed
            else "fail"
        ),
        (
            "Hidden tests distinguish the broken starter from a correct solution."
            if starter_hidden_failed
            else (
                "The starter must fail the exercise's hidden behavioral tests."
            )
        ),
    )

    starter_timeline_valid, starter_timeline_message = (
        validate_timeline_document(
            starter_timeline
        )
    )

    add_check(
        report,
        "runtime.starter_visualization",
        "visualization",
        (
            "pass"
            if starter_timeline_valid
            else "fail"
        ),
        starter_timeline_message,
    )

    starter_integrity_issues = (
        validate_timeline_integrity(
            starter_timeline
        )
        if starter_timeline_valid
        else []
    )

    add_check(
        report,
        "runtime.starter_visualization_integrity",
        "visualization",
        (
            "pass"
            if (
                starter_timeline_valid and
                not starter_integrity_issues
            )
            else "fail"
        ),
        (
            "Starter visualization has consistent scopes, aliases, values, objects, and resources."
            if (
                starter_timeline_valid and
                not starter_integrity_issues
            )
            else (
                "Starter visualization integrity failed: " +
                "; ".join(
                    starter_integrity_issues
                    if starter_integrity_issues
                    else [
                        "timeline was not valid enough for integrity checking"
                    ]
                )
            )
        ),
    )

    validate_partial_reference_probes(
        exercise,
        exercise_path,
        report,
    )

    validate_pairwise_reference_probes(
        exercise,
        exercise_path,
        report,
    )

    try:
        remove_timeline(
            exercise_id
        )

        reference_grade = run_grade(
            exercise_path,
            exercise[
                "reference_solution"
            ]
        )

        reference_timeline = load_timeline(
            exercise_id
        )
    except (
        RuntimeError,
        subprocess.TimeoutExpired
    ) as error:
        add_check(
            report,
            "runtime.reference_execution",
            "runtime",
            "fail",
            str(error),
        )

        return

    reference_passed = bool(
        reference_grade.get(
            "passed",
            False
        )
    )

    add_check(
        report,
        "runtime.reference_passes",
        "runtime",
        (
            "pass"
            if reference_passed
            else "fail"
        ),
        (
            "Hidden reference solution passes the deterministic grader."
            if reference_passed
            else (
                "Hidden reference solution failed. "
                "This candidate cannot be published."
            )
        ),
    )

    reference_hidden = (
        reference_grade.get(
            "hidden_tests",
            {}
        )
    )

    reference_hidden_valid = (
        bool(
            reference_hidden.get(
                "used",
                False
            )
        ) and
        reference_hidden.get(
            "passed"
        ) is True
    )

    add_check(
        report,
        "runtime.reference_hidden_tests_pass",
        "runtime",
        (
            "pass"
            if reference_hidden_valid
            else "fail"
        ),
        (
            "Reference solution passes the hidden behavioral tests."
            if reference_hidden_valid
            else (
                "Reference solution must use and pass hidden tests."
            )
        ),
    )

    semantic = (
        reference_grade.get(
            "semantic_checks",
            {}
        )
    )

    concept_checks_present = bool(
        exercise.get(
            "concept_checks",
            []
        )
    )

    if concept_checks_present:
        semantic_passed = (
            semantic.get(
                "passed"
            ) is True
        )

        add_check(
            report,
            "runtime.reference_semantic_checks",
            "runtime",
            (
                "pass"
                if semantic_passed
                else "fail"
            ),
            (
                "Reference solution satisfies all declared semantic checks."
                if semantic_passed
                else (
                    "Reference solution does not satisfy its "
                    "declared semantic concept checks."
                )
            ),
        )
    else:
        add_check(
            report,
            "runtime.reference_semantic_checks",
            "runtime",
            "pass",
            (
                "This exercise intentionally relies on hidden behavioral/lifetime "
                "tests rather than a supported AST concept check."
            ),
        )

    runtime_warnings = (
        reference_grade.get(
            "runtime",
            {}
        ).get(
            "trace_warnings",
            []
        )
    )

    no_reference_warnings = (
        not runtime_warnings
    )

    add_check(
        report,
        "runtime.reference_no_trace_warnings",
        "runtime",
        (
            "pass"
            if no_reference_warnings
            else "fail"
        ),
        (
            "Reference runtime trace contains no warning events."
            if no_reference_warnings
            else (
                "Reference solution emitted runtime trace warnings."
            )
        ),
    )

    reference_timeline_valid, reference_timeline_message = (
        validate_timeline_document(
            reference_timeline
        )
    )

    add_check(
        report,
        "runtime.reference_visualization",
        "visualization",
        (
            "pass"
            if reference_timeline_valid
            else "fail"
        ),
        reference_timeline_message,
    )


    reference_integrity_issues = (
        validate_timeline_integrity(
            reference_timeline
        )
        if reference_timeline_valid
        else []
    )

    add_check(
        report,
        "runtime.reference_visualization_integrity",
        "visualization",
        (
            "pass"
            if (
                reference_timeline_valid and
                not reference_integrity_issues
            )
            else "fail"
        ),
        (
            "Reference visualization has consistent scopes, aliases, values, objects, and resources."
            if (
                reference_timeline_valid and
                not reference_integrity_issues
            )
            else (
                "Reference visualization integrity failed: " +
                "; ".join(
                    reference_integrity_issues
                    if reference_integrity_issues
                    else [
                        "timeline was not valid enough for integrity checking"
                    ]
                )
            )
        ),
    )


def materialize_candidate(
    bundle: dict
) -> tuple[Path, dict, Path]:
    workspace = (
        WORKSPACE_DIRECTORY /
        uuid4().hex
    )

    workspace.mkdir(
        parents=True,
        exist_ok=False
    )

    exercise = copy.deepcopy(
        bundle["exercise"]
    )

    files = bundle.get(
        "files",
        {}
    )

    for field in [
        "hidden_test_file",
        "support_file",
        "analysis_support_file",
    ]:
        original = exercise.get(
            field
        )

        if not original:
            continue

        content = files.get(
            original
        )

        if not isinstance(
            content,
            str
        ):
            continue

        destination = (
            workspace /
            original
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        destination.write_text(
            content,
            encoding="utf-8"
        )

        exercise[field] = str(
            destination.relative_to(
                PROJECT_ROOT
            )
        )

    exercise_path = (
        workspace /
        "exercise.json"
    )

    exercise_path.write_text(
        json.dumps(
            exercise,
            indent=2
        ) +
        "\n",
        encoding="utf-8"
    )

    return (
        exercise_path,
        exercise,
        workspace,
    )


def validate_candidate_bundle(
    candidate_path: Path,
    *,
    structural_only: bool = False,
) -> ValidationReport:
    bundle = load_json(
        candidate_path
    )

    exercise = bundle.get(
        "exercise"
    )

    exercise_id = (
        exercise.get(
            "id",
            "<unknown>"
        )
        if isinstance(
            exercise,
            dict
        )
        else "<unknown>"
    )

    report = ValidationReport(
        source=str(
            candidate_path
        ),
        exercise_id=exercise_id,
        checks=[],
    )

    candidate_version = (
        bundle.get(
            "candidate_schema_version"
        )
    )

    add_check(
        report,
        "candidate.version",
        "schema",
        (
            "pass"
            if candidate_version == 1
            else "fail"
        ),
        (
            "candidate_schema_version is 1."
            if candidate_version == 1
            else (
                "candidate_schema_version must be 1."
            )
        ),
    )

    files = bundle.get(
        "files"
    )

    files_valid = (
        isinstance(
            files,
            dict
        ) and
        all(
            isinstance(
                key,
                str
            ) and
            non_empty_string(
                value
            )
            for key, value in
            files.items()
        )
    )

    add_check(
        report,
        "candidate.files",
        "schema",
        (
            "pass"
            if files_valid
            else "fail"
        ),
        (
            f"Candidate bundles {len(files)} hidden artifact file(s)."
            if files_valid
            else (
                "Candidate files must be a path-to-source string object."
            )
        ),
    )

    if not isinstance(
        exercise,
        dict
    ):
        add_check(
            report,
            "candidate.exercise",
            "schema",
            "fail",
            "Candidate must contain an exercise object.",
        )

        return report

    validate_structure(
        exercise,
        report,
        bundled_files=(
            files
            if isinstance(
                files,
                dict
            )
            else {}
        ),
    )

    if exercise.get("topic") == "raii_scope":
        raii_grading_issues = raii_exact_sequence_grading_issues(
            exercise,
            files if isinstance(files, dict) else {},
        )

        metadata = bundle.get("generation_metadata", {})
        prompt_version = (
            metadata.get("prompt_version", 0)
            if isinstance(metadata, dict)
            else 0
        )

        if raii_grading_issues:
            status = (
                "fail"
                if isinstance(prompt_version, int) and prompt_version >= 17
                else "warn"
            )
        else:
            status = "pass"

        add_check(
            report,
            "artifacts.raii_grading_equivalence",
            "artifacts",
            status,
            (
                "RAII hidden grading checks required lifetime boundaries "
                "without requiring one exact complete lifecycle sequence."
                if not raii_grading_issues
                else (
                    "RAII grading-equivalence issue(s): " +
                    " ".join(raii_grading_issues) +
                    (
                        " New prompt-v17+ candidates must repair this before validation."
                        if status == "fail"
                        else " Legacy candidate warning: repair before manually locking this exercise."
                    )
                )
            ),
        )

    if (
        structural_only or
        not report.valid
    ):
        return report

    workspace = None

    try:
        (
            exercise_path,
            materialized_exercise,
            workspace,
        ) = materialize_candidate(
            bundle
        )

        runtime_validate(
            materialized_exercise,
            exercise_path,
            report,
        )
    finally:
        if (
            workspace is not None and
            workspace.exists()
        ):
            shutil.rmtree(
                workspace,
                ignore_errors=True
            )

    return report


def validate_published_exercise(
    exercise_path: Path,
    *,
    structural_only: bool = False,
) -> ValidationReport:
    exercise = load_json(
        exercise_path
    )

    report = ValidationReport(
        source=str(
            exercise_path
        ),
        exercise_id=str(
            exercise.get(
                "id",
                "<unknown>"
            )
        ),
        checks=[],
    )

    validate_structure(
        exercise,
        report,
        bundled_files=None,
    )

    if (
        structural_only or
        not report.valid
    ):
        return report

    runtime_validate(
        exercise,
        exercise_path,
        report,
    )

    return report


def published_exercise_paths() -> list[Path]:
    library = load_json(
        LIBRARY_PATH
    )

    result = []

    for item in library.get(
        "exercises",
        []
    ):
        if not item.get(
            "published",
            False
        ):
            continue

        exercise_file = item.get(
            "exercise_file"
        )

        if not isinstance(
            exercise_file,
            str
        ):
            continue

        result.append(
            PROJECT_ROOT /
            exercise_file
        )

    return result


def print_report(
    report: ValidationReport
):
    state = (
        "VALID"
        if report.valid
        else "INVALID"
    )

    print(
        f"\n{state}: {report.exercise_id}"
    )

    print(
        f"Source: {report.source}"
    )

    for check in report.checks:
        symbol = {
            "pass": "PASS",
            "fail": "FAIL",
            "warn": "WARN",
        }[
            check.status
        ]

        print(
            (
                f"[{symbol}] "
                f"{check.category}/"
                f"{check.id}: "
                f"{check.message}"
            )
        )

    print(
        (
            f"Summary: "
            f"{report.failures} failure(s), "
            f"{report.warnings} warning(s)"
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate C++ Teacher exercise candidates "
            "before publication."
        )
    )

    parser.add_argument(
        "path",
        nargs="?",
        help=(
            "Candidate bundle JSON or published exercise JSON."
        ),
    )

    parser.add_argument(
        "--all-published",
        action="store_true",
        help=(
            "Validate every published exercise in the library."
        ),
    )

    parser.add_argument(
        "--published",
        action="store_true",
        help=(
            "Treat PATH as a published exercise JSON rather "
            "than a candidate bundle."
        ),
    )

    parser.add_argument(
        "--structural-only",
        action="store_true",
        help=(
            "Run schema/pedagogy/artifact checks without "
            "executing the C++ grader."
        ),
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help=(
            "Print machine-readable validation report JSON."
        ),
    )

    args = parser.parse_args()

    reports: list[
        ValidationReport
    ] = []

    try:
        if args.all_published:
            for path in (
                published_exercise_paths()
            ):
                reports.append(
                    validate_published_exercise(
                        path,
                        structural_only=(
                            args.structural_only
                        ),
                    )
                )
        else:
            if not args.path:
                parser.error(
                    "PATH is required unless --all-published is used."
                )

            path = Path(
                args.path
            )

            if not path.is_absolute():
                path = (
                    PROJECT_ROOT /
                    path
                )

            path = path.resolve()

            if args.published:
                reports.append(
                    validate_published_exercise(
                        path,
                        structural_only=(
                            args.structural_only
                        ),
                    )
                )
            else:
                reports.append(
                    validate_candidate_bundle(
                        path,
                        structural_only=(
                            args.structural_only
                        ),
                    )
                )
    except (
        OSError,
        ValueError,
        json.JSONDecodeError
    ) as error:
        print(
            f"Validator error: {error}",
            file=sys.stderr
        )

        return 2

    if args.json:
        payload = {
            "validator_version": 2,
            "valid": all(
                report.valid
                for report in reports
            ),
            "reports": [
                report.to_dict()
                for report in reports
            ],
        }

        print(
            json.dumps(
                payload,
                indent=2
            )
        )
    else:
        for report in reports:
            print_report(
                report
            )

    return (
        0
        if all(
            report.valid
            for report in reports
        )
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
