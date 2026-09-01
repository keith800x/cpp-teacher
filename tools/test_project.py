#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIRECTORY = PROJECT_ROOT / "tools"
VISUALIZER_DIRECTORY = PROJECT_ROOT / "visualizer"
BUILD_DIRECTORY = PROJECT_ROOT / "build"
CPP_TEACHER_PATH = BUILD_DIRECTORY / "cpp_teacher"


class TestFailure(RuntimeError):
    pass


def run(
    command: list[str],
    *,
    label: str,
    capture: bool = True,
) -> subprocess.CompletedProcess:
    print(f"\n== {label} ==")
    print("$ " + " ".join(command))

    completed = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        text=True,
        capture_output=capture,
        check=False,
    )

    if capture:
        if completed.stdout:
            print(completed.stdout, end="")

        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)

    if completed.returncode != 0:
        raise TestFailure(
            f"{label} failed with exit code {completed.returncode}."
        )

    print(f"PASS: {label}")
    return completed


def syntax_tests() -> None:
    print("\n== Python syntax ==")

    python_files = []

    server = PROJECT_ROOT / "dev_server.py"
    if server.exists():
        python_files.append(server)

    python_files.extend(
        sorted(
            path
            for path in TOOLS_DIRECTORY.glob("*.py")
            if path.is_file()
        )
    )

    for path in python_files:
        py_compile.compile(
            str(path),
            doraise=True,
        )

        print(
            "PASS:",
            path.relative_to(PROJECT_ROOT),
        )

    node = (
        shutil.which("node")
        or
        shutil.which("nodejs")
    )

    javascript_files = [
        path
        for path in sorted(
            VISUALIZER_DIRECTORY.glob("*.js")
        )
        if path.is_file()
    ]

    if node is None:
        if javascript_files:
            print(
                "\nSKIP: JavaScript syntax checks "
                "(Node.js is not installed in this WSL environment)."
            )
            print(
                "      The browser application does not require Node.js. "
                "Install Node later if you want this additional development check."
            )

        return

    for path in javascript_files:
        run(
            [
                node,
                "--check",
                str(path),
            ],
            label=(
                "JavaScript syntax: "
                + str(path.relative_to(PROJECT_ROOT))
            ),
        )


def offline_unit_tests() -> None:
    excluded = {
        "test_project.py",
    }

    tests = [
        path
        for path in sorted(
            TOOLS_DIRECTORY.glob("test_*.py")
        )
        if (
            path.is_file()
            and path.name not in excluded
        )
    ]

    if not tests:
        print(
            "\nNo tools/test_*.py offline tests were found."
        )
        return

    for path in tests:
        run(
            [
                sys.executable,
                str(path),
            ],
            label=(
                "Offline regression: "
                + path.name
            ),
        )


def structural_validation() -> None:
    validator = TOOLS_DIRECTORY / "exercise_validator.py"

    if not validator.exists():
        raise TestFailure(
            "tools/exercise_validator.py is missing."
        )

    completed = run(
        [
            sys.executable,
            str(validator),
            "--all-published",
            "--structural-only",
            "--json",
        ],
        label="Published exercise structural validation",
    )

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise TestFailure(
            "Structural validator output was not valid JSON."
        ) from error

    if not payload.get("valid"):
        raise TestFailure(
            "At least one published exercise failed structural validation."
        )


def ensure_cpp_build() -> None:
    cmake = shutil.which("cmake")

    if cmake is None:
        raise TestFailure(
            "CMake is required for the full test suite."
        )

    if not (
        BUILD_DIRECTORY /
        "CMakeCache.txt"
    ).exists():
        run(
            [
                cmake,
                "-S",
                ".",
                "-B",
                "build",
            ],
            label="Configure C++ Teacher",
        )

    run(
        [
            cmake,
            "--build",
            "build",
        ],
        label="Build C++ Teacher",
    )

    if not CPP_TEACHER_PATH.exists():
        raise TestFailure(
            "build/cpp_teacher was not produced."
        )


def full_runtime_validation() -> None:
    ensure_cpp_build()

    run(
        [
            sys.executable,
            str(
                TOOLS_DIRECTORY /
                "exercise_validator.py"
            ),
            "--all-published",
        ],
        label="Full published exercise validation",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the unified C++ Teacher regression suite."
        )
    )

    mode = parser.add_mutually_exclusive_group()

    mode.add_argument(
        "--fast",
        action="store_true",
        help=(
            "Syntax + offline regression tests + structural "
            "exercise validation. This is the default."
        ),
    )

    mode.add_argument(
        "--full",
        action="store_true",
        help=(
            "Fast suite plus automatic CMake build and full "
            "compiler/AST/runtime/visualization validation."
        ),
    )

    args = parser.parse_args()

    try:
        syntax_tests()
        offline_unit_tests()
        structural_validation()

        if args.full:
            full_runtime_validation()

    except (
        TestFailure,
        py_compile.PyCompileError,
    ) as error:
        print(
            f"\nTEST SUITE FAILED: {error}",
            file=sys.stderr,
        )
        return 1

    print("\n========================================")
    print("C++ Teacher regression suite: PASS")
    print(
        "Mode:",
        "full" if args.full else "fast",
    )
    print("========================================")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
