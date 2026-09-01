#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath

PROJECT_ROOT = Path(__file__).resolve().parents[1]

VERSION_PATH = (
    PROJECT_ROOT /
    "config" /
    "project_version.json"
)

BACKUP_ROOT = (
    PROJECT_ROOT /
    ".patch_backups"
)

PATCH_MANIFEST = "patch.json"


class PatchError(RuntimeError):
    pass


def current_version() -> str | None:
    if not VERSION_PATH.exists():
        return None

    try:
        payload = json.loads(
            VERSION_PATH.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None

    value = payload.get("version")

    return (
        value
        if isinstance(value, str)
        else None
    )


def ensure_gitignore_entry(
    entry: str
) -> None:
    path = (
        PROJECT_ROOT /
        ".gitignore"
    )

    existing = ""

    if path.exists():
        try:
            existing = path.read_text(
                encoding="utf-8"
            )
        except OSError:
            existing = ""

    lines = existing.splitlines()

    if entry in lines:
        return

    with path.open(
        "a",
        encoding="utf-8"
    ) as file:
        if (
            existing and
            not existing.endswith(
                "\n"
            )
        ):
            file.write(
                "\n"
            )

        file.write(
            entry +
            "\n"
        )


def write_version(
    version: str,
    patch_id: str,
) -> None:
    VERSION_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    VERSION_PATH.write_text(
        json.dumps(
            {
                "version": version,
                "last_patch": patch_id,
                "installed_at": (
                    datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat()
                ),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def safe_relative(raw: str) -> Path:
    path = PurePosixPath(raw)

    if (
        path.is_absolute()
        or ".." in path.parts
        or not path.parts
    ):
        raise PatchError(
            f"Unsafe patch path: {raw}"
        )

    return Path(*path.parts)


def read_manifest(
    archive: zipfile.ZipFile
) -> dict:
    try:
        payload = json.loads(
            archive.read(
                PATCH_MANIFEST
            ).decode(
                "utf-8"
            )
        )
    except KeyError as error:
        raise PatchError(
            "Patch has no patch.json."
        ) from error
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ) as error:
        raise PatchError(
            "patch.json is invalid."
        ) from error

    if not isinstance(payload, dict):
        raise PatchError(
            "patch.json must contain an object."
        )

    for field in [
        "patch_id",
        "target_version",
        "files",
    ]:
        if field not in payload:
            raise PatchError(
                f"patch.json is missing '{field}'."
            )

    if not isinstance(
        payload["files"],
        list
    ):
        raise PatchError(
            "patch.json files must be an array."
        )

    return payload


def verify_required_version(
    manifest: dict,
    *,
    force: bool,
) -> None:
    required = manifest.get(
        "requires_version"
    )

    if required is None or force:
        return

    installed = current_version()

    if installed != required:
        raise PatchError(
            (
                f"Patch requires version {required}, "
                f"but current version is {installed!r}. "
                "Use --force only after confirming compatibility."
            )
        )


def backup(
    files: list[Path],
    patch_id: str,
) -> tuple[Path, dict[str, bool]]:
    stamp = datetime.datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    directory = (
        BACKUP_ROOT /
        f"{stamp}_{patch_id}"
    )

    directory.mkdir(
        parents=True,
        exist_ok=False,
    )

    existed = {}

    for relative in files:
        destination = PROJECT_ROOT / relative
        key = relative.as_posix()
        existed[key] = destination.exists()

        if not destination.exists():
            continue

        backup_path = directory / relative
        backup_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            destination,
            backup_path,
        )

    (
        directory /
        "backup_manifest.json"
    ).write_text(
        json.dumps(
            {
                "existed": existed,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return directory, existed


def apply(
    archive: zipfile.ZipFile,
    files: list[Path],
) -> None:
    for relative in files:
        member = (
            "files/" +
            relative.as_posix()
        )

        try:
            data = archive.read(member)
        except KeyError as error:
            raise PatchError(
                (
                    f"Manifest lists {relative}, "
                    f"but {member} is missing."
                )
            ) from error

        destination = PROJECT_ROOT / relative
        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = destination.with_name(
            destination.name +
            ".patch_tmp"
        )

        temporary.write_bytes(data)

        os.replace(
            temporary,
            destination,
        )


def rollback(
    files: list[Path],
    backup_directory: Path,
    existed: dict[str, bool],
) -> None:
    print("\nRolling back...")

    for relative in files:
        destination = PROJECT_ROOT / relative
        key = relative.as_posix()

        if existed.get(key, False):
            source = (
                backup_directory /
                relative
            )

            destination.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            shutil.copy2(
                source,
                destination,
            )
        elif destination.exists():
            destination.unlink()

    print("Rollback complete.")


def run_verification(
    command: list[str],
) -> None:
    print("\nRunning patch verification:")
    print("$ " + " ".join(command))

    completed = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        check=False,
    )

    if completed.returncode != 0:
        raise PatchError(
            (
                "Patch verification failed with "
                f"exit code {completed.returncode}."
            )
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Safely install a C++ Teacher patch ZIP."
        )
    )

    parser.add_argument(
        "patch_zip",
    )

    parser.add_argument(
        "--force",
        action="store_true",
    )

    parser.add_argument(
        "--no-test",
        action="store_true",
    )

    args = parser.parse_args()

    patch_path = Path(
        args.patch_zip
    ).expanduser().resolve()

    if not patch_path.exists():
        print(
            f"Patch not found: {patch_path}",
            file=sys.stderr,
        )
        return 2

    backup_directory = None
    files = []
    existed = {}

    try:
        with zipfile.ZipFile(
            patch_path
        ) as archive:
            manifest = read_manifest(
                archive
            )

            verify_required_version(
                manifest,
                force=args.force,
            )

            files = [
                safe_relative(item)
                for item in manifest[
                    "files"
                ]
            ]

            patch_id = str(
                manifest["patch_id"]
            )

            target = str(
                manifest["target_version"]
            )

            print("Patch:", patch_id)
            print(
                "Current version:",
                current_version(),
            )
            print(
                "Target version:",
                target,
            )

            (
                backup_directory,
                existed,
            ) = backup(
                files,
                patch_id,
            )

            print(
                "Backup:",
                backup_directory.relative_to(
                    PROJECT_ROOT
                ),
            )

            apply(
                archive,
                files,
            )

            if not args.no_test:
                command = manifest.get(
                    "test_command"
                )

                if command is None:
                    command = [
                        sys.executable,
                        "tools/test_project.py",
                        "--fast",
                    ]

                if not (
                    isinstance(command, list)
                    and all(
                        isinstance(item, str)
                        for item in command
                    )
                ):
                    raise PatchError(
                        "test_command must be a string array."
                    )

                run_verification(command)

            write_version(
                target,
                patch_id,
            )

            ensure_gitignore_entry(
                ".patch_backups/"
            )

    except (
        PatchError,
        zipfile.BadZipFile,
        OSError,
    ) as error:
        print(
            f"\nPATCH INSTALL FAILED: {error}",
            file=sys.stderr,
        )

        if backup_directory is not None:
            try:
                rollback(
                    files,
                    backup_directory,
                    existed,
                )
            except OSError as rollback_error:
                print(
                    (
                        "Rollback also failed: "
                        f"{rollback_error}"
                    ),
                    file=sys.stderr,
                )

        return 1

    print("\n========================================")
    print("PATCH INSTALLED SUCCESSFULLY")
    print("========================================")
    print(
        "Current version:",
        current_version(),
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
