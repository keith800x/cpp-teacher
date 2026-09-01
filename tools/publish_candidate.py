#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from exercise_validator import (
    PROJECT_ROOT,
    LIBRARY_PATH,
    load_json,
    validate_candidate_bundle,
    print_report,
)


def write_json(
    path: Path,
    data: dict
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        json.dumps(
            data,
            indent=2
        ) +
        "\n",
        encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate and publish a C++ Teacher exercise candidate."
        )
    )

    parser.add_argument(
        "candidate",
        help="Path to candidate bundle JSON.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Validate fully but do not write exercise/library files."
        ),
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Allow replacing existing exercise/artifact files. "
            "Use only while developing a candidate."
        ),
    )

    args = parser.parse_args()

    candidate_path = Path(
        args.candidate
    )

    if not candidate_path.is_absolute():
        candidate_path = (
            PROJECT_ROOT /
            candidate_path
        )

    candidate_path = candidate_path.resolve()

    try:
        report = validate_candidate_bundle(
            candidate_path,
            structural_only=False,
        )
    except Exception as error:
        print(
            f"Publish validation error: {error}",
            file=sys.stderr
        )

        return 2

    print_report(
        report
    )

    if not report.valid:
        print(
            "\nNOT PUBLISHED: candidate failed validation."
        )

        return 1

    if args.dry_run:
        print(
            "\nDRY RUN: candidate is valid and would be publishable."
        )

        return 0

    bundle = load_json(
        candidate_path
    )

    exercise = bundle[
        "exercise"
    ]

    exercise_id = exercise[
        "id"
    ]

    target_exercise = (
        PROJECT_ROOT /
        "exercises" /
        f"{exercise_id}.json"
    )

    targets: list[
        tuple[Path, str]
    ] = [
        (
            target_exercise,
            json.dumps(
                exercise,
                indent=2
            ) +
            "\n",
        )
    ]

    for relative_path, content in (
        bundle.get(
            "files",
            {}
        ).items()
    ):
        targets.append(
            (
                PROJECT_ROOT /
                relative_path,
                content,
            )
        )

    existing = [
        path
        for path, _ in targets
        if path.exists()
    ]

    if (
        existing and
        not args.force
    ):
        print(
            "\nNOT PUBLISHED: target files already exist:",
            file=sys.stderr
        )

        for path in existing:
            print(
                f"  {path.relative_to(PROJECT_ROOT)}",
                file=sys.stderr
            )

        print(
            "Use --force only when intentionally replacing this candidate.",
            file=sys.stderr
        )

        return 1

    for path, content in targets:
        path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        path.write_text(
            content,
            encoding="utf-8"
        )

    library = load_json(
        LIBRARY_PATH
    )

    entries = library.setdefault(
        "exercises",
        []
    )

    existing_entry = next(
        (
            item
            for item in entries
            if item.get(
                "exercise_id"
            ) == exercise_id
        ),
        None,
    )

    new_entry = {
        "exercise_id":
            exercise_id,
        "exercise_file":
            (
                "exercises/" +
                f"{exercise_id}.json"
            ),
        "published":
            True,
    }

    if existing_entry is None:
        entries.append(
            new_entry
        )
    else:
        existing_entry.update(
            new_entry
        )

    entries.sort(
        key=lambda item:
            item.get(
                "exercise_id",
                ""
            )
    )

    write_json(
        LIBRARY_PATH,
        library
    )

    print(
        (
            "\nPUBLISHED: "
            f"{exercise_id}"
        )
    )

    print(
        (
            "The exercise is now part of "
            "catalog/exercise_library.json."
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
