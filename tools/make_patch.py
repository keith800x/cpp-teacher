#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Create a C++ Teacher patch in the safe patch format."
        )
    )

    parser.add_argument(
        "--patch-id",
        required=True,
    )

    parser.add_argument(
        "--requires-version",
        required=True,
    )

    parser.add_argument(
        "--target-version",
        required=True,
    )

    parser.add_argument(
        "--output",
        required=True,
    )

    parser.add_argument(
        "files",
        nargs="+",
    )

    args = parser.parse_args()

    normalized = []

    for raw in args.files:
        relative = Path(raw)

        if (
            relative.is_absolute()
            or ".." in relative.parts
        ):
            parser.error(
                f"Unsafe path: {raw}"
            )

        source = PROJECT_ROOT / relative

        if not source.is_file():
            parser.error(
                f"Missing file: {raw}"
            )

        normalized.append(
            relative.as_posix()
        )

    manifest = {
        "patch_format_version": 1,
        "patch_id": args.patch_id,
        "requires_version":
            args.requires_version,
        "target_version":
            args.target_version,
        "files":
            normalized,
        "test_command": [
            "python3",
            "tools/test_project.py",
            "--fast",
        ],
    }

    output = Path(
        args.output
    ).expanduser().resolve()

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with zipfile.ZipFile(
        output,
        "w",
        zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "patch.json",
            json.dumps(
                manifest,
                indent=2,
            )
            + "\n",
        )

        for relative in normalized:
            archive.write(
                PROJECT_ROOT /
                relative,
                "files/" +
                relative,
            )

    print(
        "Created:",
        output,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
