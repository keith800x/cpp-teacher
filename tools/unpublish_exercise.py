#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

LIBRARY_PATH = (
    PROJECT_ROOT /
    "catalog" /
    "exercise_library.json"
)

DATA_DIRECTORY = (
    PROJECT_ROOT /
    "data"
)

PROGRESS_PATH = (
    DATA_DIRECTORY /
    "progress.json"
)

ALLOWED_ARTIFACT_PREFIXES = {
    "tests",
    "support",
    "analysis_support",
}


def load_json(
    path: Path
) -> dict:
    with path.open(
        "r",
        encoding="utf-8"
    ) as file:
        data = json.load(
            file
        )

    if not isinstance(
        data,
        dict
    ):
        raise ValueError(
            f"{path} must contain a JSON object."
        )

    return data


def write_json(
    path: Path,
    data: dict
):
    path.write_text(
        json.dumps(
            data,
            indent=2
        ) +
        "\n",
        encoding="utf-8"
    )


def safe_project_path(
    relative: str
) -> Path | None:
    if not isinstance(
        relative,
        str
    ):
        return None

    path = Path(
        relative
    )

    if (
        path.is_absolute() or
        ".." in path.parts
    ):
        return None

    resolved = (
        PROJECT_ROOT /
        path
    ).resolve()

    try:
        resolved.relative_to(
            PROJECT_ROOT.resolve()
        )
    except ValueError:
        return None

    return resolved


def remove_progress(
    exercise_id: str,
    dry_run: bool
):
    if PROGRESS_PATH.exists():
        progress = load_json(
            PROGRESS_PATH
        )

        exercises = progress.get(
            "exercises",
            {}
        )

        if (
            isinstance(
                exercises,
                dict
            ) and
            exercise_id in exercises
        ):
            print(
                (
                    "  progress record: "
                    f"{PROGRESS_PATH.relative_to(PROJECT_ROOT)}"
                )
            )

            if not dry_run:
                del exercises[
                    exercise_id
                ]

                write_json(
                    PROGRESS_PATH,
                    progress
                )

    attempt_dir = (
        DATA_DIRECTORY /
        "attempt_timelines" /
        exercise_id
    )

    if attempt_dir.exists():
        print(
            (
                "  attempt timelines: "
                f"{attempt_dir.relative_to(PROJECT_ROOT)}"
            )
        )

        if not dry_run:
            shutil.rmtree(
                attempt_dir
            )

    solution_timeline = (
        DATA_DIRECTORY /
        "solution_timelines" /
        f"{exercise_id}.json"
    )

    if solution_timeline.exists():
        print(
            (
                "  solution timeline: "
                f"{solution_timeline.relative_to(PROJECT_ROOT)}"
            )
        )

        if not dry_run:
            solution_timeline.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Remove a published exercise from the local "
            "C++ Teacher development library."
        )
    )

    parser.add_argument(
        "exercise_id",
        help=(
            "Exact exercise id from catalog/exercise_library.json."
        ),
    )

    parser.add_argument(
        "--delete-files",
        action="store_true",
        help=(
            "Also delete the published exercise JSON and "
            "exercise-specific hidden test/support files."
        ),
    )

    parser.add_argument(
        "--delete-progress",
        action="store_true",
        help=(
            "Also delete local attempts, saved submissions, "
            "and archived timelines for this exercise."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Print what would be removed without changing files."
        ),
    )

    args = parser.parse_args()

    if not LIBRARY_PATH.exists():
        print(
            "Exercise library does not exist.",
            file=sys.stderr
        )

        return 2

    library = load_json(
        LIBRARY_PATH
    )

    entries = library.get(
        "exercises",
        []
    )

    if not isinstance(
        entries,
        list
    ):
        print(
            "Exercise library is malformed.",
            file=sys.stderr
        )

        return 2

    match = next(
        (
            item
            for item in entries
            if (
                isinstance(
                    item,
                    dict
                ) and
                item.get(
                    "exercise_id"
                ) ==
                args.exercise_id
            )
        ),
        None,
    )

    if match is None:
        print(
            (
                "Exercise is not published: "
                f"{args.exercise_id}"
            )
        )

        return 1

    exercise_file_relative = (
        match.get(
            "exercise_file"
        )
    )

    exercise_file = (
        safe_project_path(
            exercise_file_relative
        )
        if isinstance(
            exercise_file_relative,
            str
        )
        else None
    )

    exercise = None

    if (
        exercise_file is not None and
        exercise_file.exists()
    ):
        try:
            exercise = load_json(
                exercise_file
            )
        except (
            OSError,
            ValueError,
            json.JSONDecodeError
        ):
            exercise = None

    print(
        (
            "Unpublishing: "
            f"{args.exercise_id}"
        )
    )

    print(
        (
            "  catalog entry: "
            f"{LIBRARY_PATH.relative_to(PROJECT_ROOT)}"
        )
    )

    if args.delete_files:
        if (
            exercise_file is not None and
            exercise_file.exists()
        ):
            print(
                (
                    "  exercise file: "
                    f"{exercise_file.relative_to(PROJECT_ROOT)}"
                )
            )

        if isinstance(
            exercise,
            dict
        ):
            for field in [
                "hidden_test_file",
                "support_file",
                "analysis_support_file",
            ]:
                relative = exercise.get(
                    field
                )

                if not isinstance(
                    relative,
                    str
                ):
                    continue

                artifact_path = (
                    safe_project_path(
                        relative
                    )
                )

                if artifact_path is None:
                    continue

                relative_path = (
                    artifact_path.relative_to(
                        PROJECT_ROOT
                    )
                )

                if (
                    not relative_path.parts or
                    relative_path.parts[0] not in
                        ALLOWED_ARTIFACT_PREFIXES
                ):
                    continue

                # Do not delete a shared hand-authored support file by mistake.
                # AI-generated artifact filenames include the exercise id.
                if (
                    args.exercise_id not in
                    artifact_path.name
                ):
                    print(
                        (
                            "  keeping possibly shared artifact: "
                            f"{relative_path}"
                        )
                    )

                    continue

                if artifact_path.exists():
                    print(
                        (
                            "  hidden artifact: "
                            f"{relative_path}"
                        )
                    )

    if args.delete_progress:
        print(
            "Local learner data to remove:"
        )

        remove_progress(
            args.exercise_id,
            dry_run=True
        )

    if args.dry_run:
        print(
            "\nDRY RUN: no files changed."
        )

        return 0

    library["exercises"] = [
        item
        for item in entries
        if not (
            isinstance(
                item,
                dict
            ) and
            item.get(
                "exercise_id"
            ) ==
            args.exercise_id
        )
    ]

    write_json(
        LIBRARY_PATH,
        library
    )

    if args.delete_files:
        if isinstance(
            exercise,
            dict
        ):
            for field in [
                "hidden_test_file",
                "support_file",
                "analysis_support_file",
            ]:
                relative = exercise.get(
                    field
                )

                if not isinstance(
                    relative,
                    str
                ):
                    continue

                artifact_path = (
                    safe_project_path(
                        relative
                    )
                )

                if artifact_path is None:
                    continue

                relative_path = (
                    artifact_path.relative_to(
                        PROJECT_ROOT
                    )
                )

                if (
                    relative_path.parts and
                    relative_path.parts[0] in
                        ALLOWED_ARTIFACT_PREFIXES and
                    args.exercise_id in
                        artifact_path.name and
                    artifact_path.exists()
                ):
                    artifact_path.unlink()

        if (
            exercise_file is not None and
            exercise_file.exists()
        ):
            exercise_file.unlink()

    if args.delete_progress:
        remove_progress(
            args.exercise_id,
            dry_run=False
        )

    print(
        "\nUNPUBLISHED."
    )

    print(
        (
            "The source candidate under candidates/generated/ "
            "was intentionally kept."
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
