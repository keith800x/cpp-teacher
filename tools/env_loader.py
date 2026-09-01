from __future__ import annotations

import os
from pathlib import Path


def load_project_env(
    project_root: Path,
    filename: str = ".env"
) -> None:
    """
    Load simple KEY=VALUE pairs from a local project .env file.

    Existing environment variables always win, so shell exports can
    override .env values.

    This intentionally supports only the small subset C++ Teacher needs:
    - blank lines
    - comments beginning with #
    - KEY=VALUE
    - optional single/double quotes around the complete value
    """

    path = project_root / filename

    if not path.exists():
        return

    try:
        lines = path.read_text(
            encoding="utf-8"
        ).splitlines()
    except OSError:
        return

    for raw_line in lines:
        line = raw_line.strip()

        if (
            not line or
            line.startswith("#") or
            "=" not in line
        ):
            continue

        key, value = line.split(
            "=",
            1
        )

        key = key.strip()
        value = value.strip()

        if not key:
            continue

        if (
            len(value) >= 2 and
            value[0] == value[-1] and
            value[0] in {"'", '"'}
        ):
            value = value[1:-1]

        os.environ.setdefault(
            key,
            value
        )
