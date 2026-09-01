#!/usr/bin/env python3

from __future__ import annotations

import errno
import json
import os
import re
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent

TOOLS_DIRECTORY = (
    PROJECT_ROOT /
    "tools"
)

if str(TOOLS_DIRECTORY) not in sys.path:
    sys.path.insert(
        0,
        str(TOOLS_DIRECTORY)
    )

from env_loader import load_project_env

load_project_env(
    PROJECT_ROOT
)

EXERCISE_LIBRARY_PATH = (
    PROJECT_ROOT /
    "catalog" /
    "exercise_library.json"
)

CPP_TEACHER_PATH = (
    PROJECT_ROOT /
    "build" /
    "cpp_teacher"
)

OUTPUT_DIRECTORY = (
    PROJECT_ROOT /
    "output"
)

DATA_DIRECTORY = (
    PROJECT_ROOT /
    "data"
)

PROGRESS_PATH = (
    DATA_DIRECTORY /
    "progress.json"
)

ATTEMPT_TIMELINE_DIRECTORY = (
    DATA_DIRECTORY /
    "attempt_timelines"
)

SOLUTION_TIMELINE_DIRECTORY = (
    DATA_DIRECTORY /
    "solution_timelines"
)

CANDIDATE_REFERENCE_TIMELINE_DIRECTORY = (
    DATA_DIRECTORY /
    "authoring_reference_timelines"
)

GENERATED_CANDIDATE_DIRECTORY = (
    PROJECT_ROOT /
    "candidates" /
    "generated"
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

BUILD_DIRECTORY = (
    PROJECT_ROOT /
    "build"
)

AUTHORING_TIMEOUT_SECONDS = 600

SAFE_FALLBACK_GOALS = {
    "references": (
        "Make the program operate on the intended live values without creating behaviorally incorrect or unnecessary copies."
    ),
    "raii_scope": (
        "Keep temporary resources alive only for the work that needs them and release them before later processing begins."
    ),
    "move_semantics": (
        "Transfer exclusive payload ownership without duplicating the underlying allocation or leaving two live owners."
    ),
}

MAX_REQUEST_BYTES = 256 * 1024
GRADE_TIMEOUT_SECONDS = 20

PROGRESS_LOCK = threading.Lock()
GRADER_LOCK = threading.Lock()
AUTHORING_LOCK = threading.Lock()


class DevelopmentEnvironmentError(RuntimeError):
    """A local development setup problem with a concise user-facing message."""


def native_binary_format(
    path: Path
) -> str:
    if not path.exists():
        return "missing"

    try:
        with path.open(
            "rb"
        ) as file:
            header = file.read(
                4
            )
    except OSError:
        return "unknown"

    if header.startswith(
        b"\x7fELF"
    ):
        return "elf"

    if header.startswith(
        b"MZ"
    ):
        return "pe"

    if header in {
        b"\xfe\xed\xfa\xce",
        b"\xce\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xcf\xfa\xed\xfe",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
    }:
        return "macho"

    return "unknown"


def expected_native_binary_format(
    platform_name: str | None = None
) -> str | None:
    platform_name = (
        platform_name
        if platform_name is not None
        else sys.platform
    )

    if platform_name.startswith(
        "linux"
    ):
        return "elf"

    if (
        platform_name == "win32" or
        platform_name.startswith(
            "cygwin"
        )
    ):
        return "pe"

    if platform_name == "darwin":
        return "macho"

    return None


def grader_platform_mismatch_message(
    grader_path: Path = CPP_TEACHER_PATH,
    *,
    platform_name: str | None = None
) -> str | None:
    actual = native_binary_format(
        grader_path
    )

    expected = expected_native_binary_format(
        platform_name
    )

    if (
        actual in {
            "missing",
            "unknown",
        } or
        expected is None or
        actual == expected
    ):
        return None

    resolved_platform = (
        platform_name
        if platform_name is not None
        else sys.platform
    )

    if (
        expected == "pe" and
        actual == "elf"
    ):
        return (
            "C++ grader platform mismatch.\n"
            f"Detected a Linux/WSL grader at: {grader_path}\n"
            "but dev_server.py is running with Windows Python.\n\n"
            "Start C++ Teacher from a WSL terminal instead:\n"
            "  cd \"/mnt/c/Users/Keith Lua/Desktop/Job Resume Portfoilio Info/cpp-teacher\"\n"
            "  python3 dev_server.py\n\n"
            "Do not use Windows `python` or `py` with the WSL build."
        )

    if (
        expected == "elf" and
        actual == "pe"
    ):
        return (
            "C++ grader platform mismatch.\n"
            f"Detected a Windows grader at: {grader_path}\n"
            "but dev_server.py is running in Linux/WSL.\n\n"
            "Rebuild the grader from this WSL terminal:\n"
            "  python3 dev_server.py --rebuild"
        )

    return (
        "C++ grader platform mismatch.\n"
        f"Host platform: {resolved_platform}\n"
        f"Grader format: {actual}\n"
        f"Expected format: {expected}\n"
        f"Grader: {grader_path}"
    )


def ensure_grader_platform_compatible(
    grader_path: Path = CPP_TEACHER_PATH,
    *,
    platform_name: str | None = None
):
    message = grader_platform_mismatch_message(
        grader_path,
        platform_name=platform_name
    )

    if message is not None:
        raise DevelopmentEnvironmentError(
            message
        )


def grader_launch_error_message(
    error: OSError,
    grader_path: Path = CPP_TEACHER_PATH
) -> str | None:
    winerror = getattr(
        error,
        "winerror",
        None
    )

    if (
        winerror == 193 or
        error.errno == errno.ENOEXEC
    ):
        mismatch = grader_platform_mismatch_message(
            grader_path
        )

        if mismatch is not None:
            return mismatch

        return (
            "The C++ grader could not be executed by this operating system.\n"
            f"Grader: {grader_path}\n"
            "Rebuild it from the same environment that runs dev_server.py."
        )

    return None


def server_bind_error_message(
    error: OSError,
    port: int
) -> str | None:
    winerror = getattr(
        error,
        "winerror",
        None
    )

    if not (
        error.errno == errno.EADDRINUSE or
        winerror == 10048
    ):
        return None

    return (
        f"Port {port} is already in use.\n"
        "Another C++ Teacher development server may already be running.\n\n"
        "Check from WSL:\n"
        f"  ss -ltnp | grep ':{port}'\n\n"
        "To restart the WSL development server:\n"
        "  pkill -f dev_server.py 2>/dev/null || true\n"
        "  python3 dev_server.py"
    )


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def load_exercise_library() -> dict:
    with EXERCISE_LIBRARY_PATH.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def exercise_map() -> dict[str, dict]:
    library = load_exercise_library()

    result: dict[str, dict] = {}

    for item in library.get(
        "exercises",
        []
    ):
        if not item.get(
            "published",
            False
        ):
            continue

        exercise_id = item.get(
            "exercise_id"
        )

        exercise_file = item.get(
            "exercise_file"
        )

        if (
            not exercise_id or
            not exercise_file
        ):
            continue

        result[exercise_id] = item

    return result


def read_exercise_document(
    library_item: dict
) -> dict:
    path = (
        PROJECT_ROOT /
        library_item["exercise_file"]
    ).resolve()

    with path.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def default_progress_store() -> dict:
    return {
        "progress_version": 1,
        "exercises": {},
    }


def load_progress_store() -> dict:
    if not PROGRESS_PATH.exists():
        return default_progress_store()

    try:
        with PROGRESS_PATH.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(file)
    except (
        OSError,
        json.JSONDecodeError
    ):
        return default_progress_store()

    if not isinstance(
        data,
        dict
    ):
        return default_progress_store()

    if not isinstance(
        data.get("exercises"),
        dict
    ):
        data["exercises"] = {}

    data["progress_version"] = 1

    return data


def save_progress_store(
    store: dict
):
    DATA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    temp_path = (
        PROGRESS_PATH.parent /
        (
            PROGRESS_PATH.name +
            ".tmp"
        )
    )

    with temp_path.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            store,
            file,
            indent=2
        )

        file.write("\n")

    os.replace(
        temp_path,
        PROGRESS_PATH
    )


def exercise_progress_record(
    store: dict,
    exercise_id: str
) -> dict:
    exercises = store.setdefault(
        "exercises",
        {}
    )

    record = exercises.setdefault(
        exercise_id,
        {
            "attempt_count": 0,
            "failed_attempt_count": 0,
            "solved": False,
            "solution_revealed": False,
            "last_passed": None,
            "updated_at": None,
            "attempts": [],
        }
    )

    record.setdefault(
        "attempt_count",
        0
    )

    record.setdefault(
        "failed_attempt_count",
        0
    )

    record.setdefault(
        "solved",
        False
    )

    record.setdefault(
        "solution_revealed",
        False
    )

    record.setdefault(
        "last_passed",
        None
    )

    record.setdefault(
        "updated_at",
        None
    )

    record.setdefault(
        "attempts",
        []
    )

    return record


def public_progress(
    exercise_id: str
) -> dict:
    with PROGRESS_LOCK:
        store = load_progress_store()

        record = exercise_progress_record(
            store,
            exercise_id
        )

        attempts = record.get(
            "attempts",
            []
        )

        latest_attempt = (
            attempts[-1]
            if attempts
            else None
        )

        solved = bool(
            record.get(
                "solved",
                False
            )
        )

        attempt_count = int(
            record.get(
                "attempt_count",
                0
            )
        )

        if solved:
            status = "solved"
        elif attempt_count > 0:
            status = "attempted"
        else:
            status = "unsolved"

        return {
            "attempt_count":
                attempt_count,
            "failed_attempt_count":
                int(
                    record.get(
                        "failed_attempt_count",
                        0
                    )
                ),
            "solved":
                solved,
            "status":
                status,
            "last_passed":
                record.get(
                    "last_passed"
                ),
            "solution_available":
                int(
                    record.get(
                        "failed_attempt_count",
                        0
                    )
                ) > 0,
            "solution_revealed":
                bool(
                    record.get(
                        "solution_revealed",
                        False
                    )
                ),
            "has_saved_submission":
                latest_attempt is not None,
            "has_visualization":
                bool(
                    latest_attempt and
                    latest_attempt.get(
                        "timeline_file"
                    )
                ),
            "updated_at":
                record.get(
                    "updated_at"
                ),
        }


def latest_submission(
    exercise_id: str
):
    with PROGRESS_LOCK:
        store = load_progress_store()

        record = exercise_progress_record(
            store,
            exercise_id
        )

        attempts = record.get(
            "attempts",
            []
        )

        if not attempts:
            return None

        return attempts[-1].get(
            "source"
        )


def latest_attempt_timeline(
    exercise_id: str
):
    with PROGRESS_LOCK:
        store = load_progress_store()

        record = exercise_progress_record(
            store,
            exercise_id
        )

        attempts = record.get(
            "attempts",
            []
        )

        if not attempts:
            return None

        timeline_file = attempts[-1].get(
            "timeline_file"
        )

    if not timeline_file:
        return None

    path = (
        PROJECT_ROOT /
        timeline_file
    ).resolve()

    try:
        path.relative_to(
            DATA_DIRECTORY.resolve()
        )
    except ValueError:
        return None

    if not path.exists():
        return None

    try:
        with path.open(
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)
    except (
        OSError,
        json.JSONDecodeError
    ):
        return None


def latest_solution_timeline(
    exercise_id: str
):
    path = (
        SOLUTION_TIMELINE_DIRECTORY /
        f"{exercise_id}.json"
    )

    if not path.exists():
        return None

    try:
        with path.open(
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)
    except (
        OSError,
        json.JSONDecodeError
    ):
        return None


def read_generated_timeline(
    exercise_id: str
):
    path = (
        OUTPUT_DIRECTORY /
        (
            f"{exercise_id}"
            "_memory_timeline.json"
        )
    )

    if not path.exists():
        return None

    try:
        with path.open(
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(file)
    except (
        OSError,
        json.JSONDecodeError
    ):
        return None


def candidate_reference_timeline_path(
    candidate_id: str
) -> Path:
    return (
        CANDIDATE_REFERENCE_TIMELINE_DIRECTORY /
        f"{candidate_id}.json"
    )


def clear_candidate_reference_timeline(
    candidate_id: str
):
    path = candidate_reference_timeline_path(
        candidate_id
    )

    try:
        path.unlink(
            missing_ok=True
        )
    except OSError:
        pass


def archive_candidate_reference_timeline(
    candidate_id: str,
    timeline,
):
    if not isinstance(
        timeline,
        dict
    ):
        return None

    CANDIDATE_REFERENCE_TIMELINE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = candidate_reference_timeline_path(
        candidate_id
    )

    temporary = path.with_suffix(
        ".json.tmp"
    )

    with temporary.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            timeline,
            file,
            indent=2,
        )

        file.write(
            "\n"
        )

    temporary.replace(
        path
    )

    return path


def timeline_snapshot_count(
    timeline,
) -> int:
    if not isinstance(
        timeline,
        dict
    ):
        return 0

    frames = timeline.get(
        "timeline"
    )

    if not isinstance(
        frames,
        list
    ):
        return 0

    return len(
        frames
    )


def validation_visualization_snapshot_count(
    report,
    check_id: str,
):
    if not isinstance(
        report,
        dict
    ):
        return None

    checks = report.get(
        "checks"
    )

    if not isinstance(
        checks,
        list
    ):
        return None

    for check in checks:
        if (
            not isinstance(
                check,
                dict
            ) or
            check.get(
                "id"
            ) != check_id
        ):
            continue

        message = check.get(
            "message"
        )

        if not isinstance(
            message,
            str
        ):
            return None

        match = re.search(
            r"Visualization contains (\d+) snapshots\.",
            message,
        )

        if match is None:
            return None

        return int(
            match.group(
                1
            )
        )

    return None


def read_candidate_reference_timeline(
    candidate_id: str
):
    path = candidate_reference_timeline_path(
        candidate_id
    )

    try:
        candidate_path, validation_path = (
            authoring_candidate_paths(
                candidate_id
            )
        )
    except ValueError:
        return None

    if (
        not path.exists() or
        not candidate_path.exists() or
        not validation_path.exists()
    ):
        return None

    try:
        archive_mtime = (
            path.stat().st_mtime
        )

        if (
            archive_mtime <
                candidate_path.stat().st_mtime or
            archive_mtime <
                validation_path.stat().st_mtime
        ):
            return None

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(
                file
            )
    except (
        OSError,
        json.JSONDecodeError,
    ):
        return None


def reference_timeline_for_solution_view(
    exercise_id: str
):
    """
    Resolve the timeline shown by the ordinary Reference Solution viewer.

    Generated authoring candidates must use the same validated reference
    archive as the authoring reference/export endpoint. Falling back to an
    older data/solution_timelines/<id>.json file would reintroduce the exact
    14-vs-11 mismatch Step 30.8.2 was designed to prevent.

    Non-authoring exercises keep the existing saved-solution behavior.
    """
    if authoring_candidate_id_is_safe(
        exercise_id
    ):
        try:
            candidate_path, _ = (
                authoring_candidate_paths(
                    exercise_id
                )
            )
        except ValueError:
            candidate_path = None

        if (
            candidate_path is not None and
            candidate_path.exists()
        ):
            # Do NOT fall back to an old solution timeline when this is a
            # generated candidate. If its validated archive is absent/stale,
            # the caller should surface that the reference must be
            # revalidated rather than silently show old frames.
            return read_candidate_reference_timeline(
                exercise_id
            )

    return latest_solution_timeline(
        exercise_id
    )


def public_exercise_document(
    library_item: dict
) -> dict:
    exercise = read_exercise_document(
        library_item
    )

    allowed_fields = [
        "id",
        "topic",
        "title",
        "difficulty",
        "type",
        "scenario",
        "problem_statement",
        "constraints",
        "instructions",
        "starter_code",
        "hints",
    ]

    document = {
        field: exercise[field]
        for field in allowed_fields
        if field in exercise
    }

    # learning_objective and expected_concepts are intentionally internal.
    # They can reveal the target mechanism before the learner has reasoned
    # about the problem.
    document["learner_goal"] = (
        learner_goal_for_exercise(
            exercise
        )
    )

    return document


def public_exercise_metadata(
    library_item: dict
) -> dict:
    exercise = read_exercise_document(
        library_item
    )

    progress = public_progress(
        exercise["id"]
    )

    return {
        "id":
            exercise["id"],
        "topic":
            exercise["topic"],
        "title":
            exercise["title"],
        "difficulty":
            exercise["difficulty"],
        "type":
            exercise["type"],
        "scenario":
            exercise.get(
                "scenario",
                ""
            ),
        "problem_statement":
            exercise.get(
                "problem_statement",
                ""
            ),
        "learner_goal":
            learner_goal_for_exercise(
                exercise
            ),
        "progress":
            progress,
    }

def archive_attempt_timeline(
    exercise_id: str,
    attempt_id: str,
    timeline
):
    if timeline is None:
        return None

    directory = (
        ATTEMPT_TIMELINE_DIRECTORY /
        exercise_id
    )

    directory.mkdir(
        parents=True,
        exist_ok=True
    )

    path = (
        directory /
        (
            f"{attempt_id}.json"
        )
    )

    with path.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            timeline,
            file,
            indent=2
        )

        file.write("\n")

    return str(
        path.relative_to(
            PROJECT_ROOT
        )
    )


def archive_solution_timeline(
    exercise_id: str,
    timeline
):
    if timeline is None:
        return None

    SOLUTION_TIMELINE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    path = (
        SOLUTION_TIMELINE_DIRECTORY /
        (
            f"{exercise_id}.json"
        )
    )

    with path.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            timeline,
            file,
            indent=2
        )

        file.write("\n")

    return path


def record_attempt(
    exercise_id: str,
    source: str,
    passed: bool,
    timeline
):
    attempt_id = uuid4().hex

    timeline_file = archive_attempt_timeline(
        exercise_id,
        attempt_id,
        timeline
    )

    attempt = {
        "attempt_id":
            attempt_id,
        "submitted_at":
            utc_now(),
        "passed":
            bool(passed),
        "source":
            source,
        "timeline_file":
            timeline_file,
    }

    with PROGRESS_LOCK:
        store = load_progress_store()

        record = exercise_progress_record(
            store,
            exercise_id
        )

        record["attempt_count"] = (
            int(
                record.get(
                    "attempt_count",
                    0
                )
            ) +
            1
        )

        if not passed:
            record[
                "failed_attempt_count"
            ] = (
                int(
                    record.get(
                        "failed_attempt_count",
                        0
                    )
                ) +
                1
            )

        record["solved"] = (
            bool(
                record.get(
                    "solved",
                    False
                )
            ) or
            bool(passed)
        )

        record["last_passed"] = (
            bool(passed)
        )

        record["updated_at"] = (
            attempt["submitted_at"]
        )

        record.setdefault(
            "attempts",
            []
        ).append(
            attempt
        )

        save_progress_store(
            store
        )

    return {
        "attempt":
            attempt,
        "progress":
            public_progress(
                exercise_id
            ),
    }


def mark_solution_revealed(
    exercise_id: str
):
    with PROGRESS_LOCK:
        store = load_progress_store()

        record = exercise_progress_record(
            store,
            exercise_id
        )

        if int(
            record.get(
                "failed_attempt_count",
                0
            )
        ) <= 0:
            return False

        record[
            "solution_revealed"
        ] = True

        record["updated_at"] = (
            utc_now()
        )

        save_progress_store(
            store
        )

    return True


def solution_is_available(
    exercise_id: str
) -> bool:
    return bool(
        public_progress(
            exercise_id
        )["solution_available"]
    )


def solution_is_revealed(
    exercise_id: str
) -> bool:
    return bool(
        public_progress(
            exercise_id
        )["solution_revealed"]
    )


def validate_exercise_file(
    library_item: dict
) -> Path:
    exercise_file = (
        PROJECT_ROOT /
        library_item["exercise_file"]
    ).resolve()

    exercises_root = (
        PROJECT_ROOT /
        "exercises"
    ).resolve()

    exercise_file.relative_to(
        exercises_root
    )

    if not exercise_file.exists():
        raise FileNotFoundError(
            exercise_file
        )

    return exercise_file


def run_grader(
    exercise_file: Path,
    source: str
) -> dict:
    if not CPP_TEACHER_PATH.exists():
        raise RuntimeError(
            "C++ grader is not built. "
            "Run cmake -S . -B build && "
            "cmake --build build first."
        )

    submission = source

    if not submission.endswith("\n"):
        submission += "\n"

    relative_exercise_path = str(
        exercise_file.relative_to(
            PROJECT_ROOT
        )
    )

    with GRADER_LOCK:
        try:
            completed = subprocess.run(
                [
                    str(CPP_TEACHER_PATH),
                    "--grade-json",
                    relative_exercise_path,
                ],
                cwd=str(PROJECT_ROOT),
                input=submission,
                text=True,
                capture_output=True,
                timeout=GRADE_TIMEOUT_SECONDS,
                check=False,
            )
        except OSError as error:
            message = grader_launch_error_message(
                error
            )

            if message is not None:
                raise RuntimeError(
                    message
                ) from error

            raise

        if completed.returncode != 0:
            raise RuntimeError(
                "The C++ grading process failed.\n" +
                completed.stderr
            )

        try:
            grade = json.loads(
                completed.stdout
            )
        except json.JSONDecodeError as error:
            raise RuntimeError(
                "The C++ grader did not return "
                "valid structured JSON."
            ) from error

        timeline = read_generated_timeline(
            grade.get(
                "exercise_id",
                ""
            )
        )

    return {
        "grade":
            grade,
        "stderr":
            completed.stderr,
        "timeline":
            timeline,
    }



def learner_goal_for_exercise(
    exercise: dict
) -> str:
    explicit = exercise.get(
        "learner_goal"
    )

    if isinstance(
        explicit,
        str
    ) and explicit.strip():
        return explicit.strip()

    problem = exercise.get(
        "problem_statement"
    )

    if isinstance(
        problem,
        str
    ) and problem.strip():
        return problem.strip()

    topic = exercise.get(
        "topic",
        ""
    )

    if topic in SAFE_FALLBACK_GOALS:
        return SAFE_FALLBACK_GOALS[
            topic
        ]

    return (
        "Make the program satisfy the stated behavior while preserving the required interface and constraints."
    )


def build_input_paths() -> list[Path]:
    result = [
        PROJECT_ROOT /
        "CMakeLists.txt"
    ]

    for directory_name in [
        "src",
        "include",
    ]:
        directory = (
            PROJECT_ROOT /
            directory_name
        )

        if not directory.exists():
            continue

        result.extend(
            path
            for path in directory.rglob(
                "*"
            )
            if path.is_file()
        )

    return result


def grader_needs_build() -> bool:
    if not CPP_TEACHER_PATH.exists():
        return True

    try:
        executable_mtime = (
            CPP_TEACHER_PATH.stat().st_mtime
        )
    except OSError:
        return True

    for path in build_input_paths():
        try:
            if (
                path.exists() and
                path.stat().st_mtime >
                    executable_mtime
            ):
                return True
        except OSError:
            return True

    return False


def run_cmake_build() -> bool:
    print(
        "[build] Configuring C++ Teacher..."
    )

    configure = subprocess.run(
        [
            "cmake",
            "-S",
            ".",
            "-B",
            "build",
        ],
        cwd=str(
            PROJECT_ROOT
        ),
        check=False,
    )

    if configure.returncode != 0:
        return False

    print(
        "[build] Building C++ Teacher..."
    )

    build = subprocess.run(
        [
            "cmake",
            "--build",
            "build",
            "--parallel",
        ],
        cwd=str(
            PROJECT_ROOT
        ),
        check=False,
    )

    return (
        build.returncode == 0 and
        CPP_TEACHER_PATH.exists()
    )


def ensure_cpp_teacher_built(
    *,
    force_clean: bool = False
):
    if CPP_TEACHER_PATH.exists():
        ensure_grader_platform_compatible()

    if (
        not force_clean and
        not grader_needs_build()
    ):
        print(
            "[build] C++ grader is up to date."
        )

        return

    if force_clean and BUILD_DIRECTORY.exists():
        print(
            "[build] Removing build directory for a clean rebuild..."
        )

        shutil.rmtree(
            BUILD_DIRECTORY
        )

    if run_cmake_build():
        ensure_grader_platform_compatible()

        print(
            "[build] C++ grader ready."
        )

        return

    # A stale/corrupt CMake cache should not force the developer to remember
    # rm -rf build. Retry once from a clean build directory automatically.
    if BUILD_DIRECTORY.exists():
        print(
            "[build] Build failed; retrying once with a clean build directory..."
        )

        shutil.rmtree(
            BUILD_DIRECTORY
        )

        if run_cmake_build():
            ensure_grader_platform_compatible()

            print(
                "[build] C++ grader ready after clean rebuild."
            )

            return

    raise RuntimeError(
        "Automatic C++ grader build failed. See the CMake/compiler output above."
    )


def load_topics_catalog() -> list[dict]:
    try:
        with TOPICS_PATH.open(
            "r",
            encoding="utf-8"
        ) as file:
            data = json.load(
                file
            )
    except (
        OSError,
        json.JSONDecodeError
    ):
        return []

    topics = data.get(
        "topics",
        []
    )

    return (
        topics
        if isinstance(
            topics,
            list
        )
        else []
    )


def authoring_candidate_id_is_safe(
    candidate_id: str
) -> bool:
    return bool(
        re.fullmatch(
            r"[a-z0-9][a-z0-9_]*",
            candidate_id or ""
        )
    )


def authoring_candidate_paths(
    candidate_id: str
) -> tuple[Path, Path]:
    if not authoring_candidate_id_is_safe(
        candidate_id
    ):
        raise ValueError(
            "Invalid candidate id."
        )

    candidate_path = (
        GENERATED_CANDIDATE_DIRECTORY /
        f"{candidate_id}.json"
    )

    validation_path = (
        GENERATED_CANDIDATE_DIRECTORY /
        f"{candidate_id}.validation.json"
    )

    return (
        candidate_path,
        validation_path,
    )


def read_optional_json(
    path: Path
):
    if not path.exists():
        return None

    try:
        with path.open(
            "r",
            encoding="utf-8"
        ) as file:
            return json.load(
                file
            )
    except (
        OSError,
        json.JSONDecodeError
    ):
        return None


def exercise_document_for_visualization(
    exercise_id: str
):
    if authoring_candidate_id_is_safe(
        exercise_id
    ):
        try:
            candidate_path, _ = authoring_candidate_paths(
                exercise_id
            )
            candidate = read_optional_json(
                candidate_path
            )
        except ValueError:
            candidate = None

        if isinstance(
            candidate,
            dict
        ):
            exercise = candidate.get(
                "exercise",
                {}
            )

            if isinstance(
                exercise,
                dict
            ):
                return exercise

    item = exercise_map().get(
        exercise_id
    )

    if item is not None:
        try:
            exercise = read_exercise_document(
                item
            )
        except (
            OSError,
            json.JSONDecodeError,
            KeyError,
        ):
            exercise = None

        if isinstance(
            exercise,
            dict
        ):
            return exercise

    return {}


def exercise_topic_for_visualization(
    exercise_id: str
) -> str:
    exercise = exercise_document_for_visualization(
        exercise_id
    )

    topic = exercise.get(
        "topic"
    )

    return (
        topic
        if isinstance(
            topic,
            str
        )
        else ""
    )


def raii_target_function_from_code(
    source,
) -> str:
    if not isinstance(
        source,
        str
    ):
        return ""

    # Learner exercise snippets contain the function/method being repaired.
    # Resolve that declaration from the exercise itself rather than guessing
    # from runtime helper ENTER_SCOPE events such as chillCargo.
    pattern = re.compile(
        r"\b(?:void|bool|int|long|short|double|float|auto|"
        r"[A-Za-z_][A-Za-z0-9_:<>]*)\s+"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
        r"\s*\([^;{}]*\)"
        r"\s*(?:const\s*)?(?:noexcept\s*)?\{"
    )

    match = pattern.search(
        source
    )

    if match is None:
        return ""

    name = match.group(
        "name"
    )

    if name in {
        "if",
        "for",
        "while",
        "switch",
        "catch",
    }:
        return ""

    return name


def raii_learner_operation_for_visualization(
    exercise_id: str
) -> str:
    exercise = exercise_document_for_visualization(
        exercise_id
    )

    if exercise.get(
        "topic"
    ) != "raii_scope":
        return ""

    for field in (
        "starter_code",
        "reference_solution",
    ):
        name = raii_target_function_from_code(
            exercise.get(
                field
            )
        )

        if name:
            return name

    return ""


def raii_internal_lifecycle_scope(
    scope_name,
) -> bool:
    if not isinstance(
        scope_name,
        str
    ):
        return False

    parts = scope_name.split(
        "::"
    )

    if len(parts) < 2:
        return False

    owner = parts[-2]
    function = parts[-1]

    return function in {
        owner,
        f"~{owner}",
    }


def raii_cause_for_client(
    cause,
):
    if not isinstance(
        cause,
        dict
    ):
        return cause

    copied = dict(
        cause
    )

    if copied.get(
        "type"
    ) == "CREATE_OBJECT":
        detail = copied.get(
            "detail"
        )

        if isinstance(
            detail,
            str
        ):
            copied[
                "detail"
            ] = "|".join(
                part
                for part in detail.split(
                    "|"
                )
                if not part.startswith(
                    "pointer="
                )
            )

    return copied


def raii_object_for_client(
    object_state,
    learner_scope="",
):
    if not isinstance(
        object_state,
        dict
    ):
        return object_state

    copied = dict(
        object_state
    )

    fields = copied.get(
        "fields"
    )

    if isinstance(
        fields,
        dict
    ):
        # RAII teaching is about automatic-object lifetime and managed
        # resources. A null raw-pointer row emitted by constructor
        # instrumentation is not a meaningful learner state here.
        copied[
            "fields"
        ] = {
            field_name:
                field
            for field_name, field
            in fields.items()
            if not (
                isinstance(
                    field,
                    dict
                ) and
                field.get(
                    "kind"
                ) == "pointer" and
                field.get(
                    "points_to"
                ) is None
            )
        }

    object_scope = copied.get(
        "scope"
    )

    if (
        learner_scope and
        (
            object_scope == "processVideoFrame" or
            raii_internal_lifecycle_scope(
                object_scope
            )
        )
    ):
        copied[
            "scope"
        ] = learner_scope

    return copied



def visualization_detail_value(
    detail,
    key: str,
) -> str:
    if not isinstance(
        detail,
        str
    ):
        return ""

    prefix = f"{key}="
    start = detail.find(
        prefix
    )

    if start < 0:
        return ""

    value_start = (
        start +
        len(prefix)
    )

    end = detail.find(
        "|",
        value_start,
    )

    if end < 0:
        return detail[
            value_start:
        ].strip()

    return detail[
        value_start:
        end
    ].strip()


def move_semantics_cause_for_client(
    cause,
):
    if not isinstance(
        cause,
        dict
    ):
        return cause

    copied = dict(
        cause
    )

    event_type = copied.get(
        "type"
    )

    subject = copied.get(
        "subject"
    )

    detail = copied.get(
        "detail"
    )

    if not isinstance(
        detail,
        str
    ):
        detail = ""

    value = visualization_detail_value(
        detail,
        "value",
    )

    moved_from = visualization_detail_value(
        detail,
        "moved_from",
    )

    copied_from = visualization_detail_value(
        detail,
        "copied_from",
    )

    moved_to = visualization_detail_value(
        detail,
        "moved_to",
    )

    retained_after = visualization_detail_value(
        detail,
        "retained_after",
    )

    role = visualization_detail_value(
        detail,
        "role",
    )

    if (
        event_type == "CREATE_VALUE" and
        role == "move_source"
    ):
        copied[
            "type"
        ] = "INITIALIZE_VALUE"

        copied[
            "detail"
        ] = (
            f"packages={value}"
            if value
            else "source member initialized"
        )

        return copied

    if (
        event_type == "CREATE_VALUE" and
        moved_from
    ):
        copied[
            "type"
        ] = "TRANSFER_VALUE"

        copied[
            "detail"
        ] = (
            f"from={moved_from}"
            f"|to={subject}"
            f"|packages={value}"
        )

        return copied

    if (
        event_type == "CREATE_VALUE" and
        copied_from
    ):
        copied[
            "type"
        ] = "COPY_VALUE"

        copied[
            "detail"
        ] = (
            f"from={copied_from}"
            f"|to={subject}"
            f"|packages={value}"
        )

        return copied

    if (
        event_type == "WRITE_VALUE" and
        moved_to
    ):
        copied[
            "type"
        ] = "CLEAR_VALUE"

        copied[
            "detail"
        ] = (
            f"moved_to={moved_to}"
            f"|packages={value}"
        )

        return copied

    if (
        event_type == "WRITE_VALUE" and
        retained_after
    ):
        copied[
            "type"
        ] = "SOURCE_RETAINED"

        copied[
            "detail"
        ] = (
            f"copied_to={retained_after}"
            f"|packages={value}"
        )

        return copied

    return copied


def move_semantics_object_for_client(
    object_state,
):
    if not isinstance(
        object_state,
        dict
    ):
        return object_state

    copied = dict(
        object_state
    )

    fields = copied.get(
        "fields"
    )

    # The generic object fallback invents data_ -> nullptr when no pointer
    # member was traced. FieldKit has a SupplyLoad load_ member, not data_.
    if (
        isinstance(
            fields,
            dict
        ) and
        set(
            fields.keys()
        ) == {
            "data_"
        }
    ):
        field = fields.get(
            "data_"
        )

        if (
            isinstance(
                field,
                dict
            ) and
            field.get(
                "kind"
            ) == "pointer" and
            field.get(
                "points_to"
            ) is None
        ):
            copied[
                "fields"
            ] = {}

    return copied


def move_semantics_timeline_for_client(
    timeline,
):
    if (
        not isinstance(
            timeline,
            dict
        ) or
        not isinstance(
            timeline.get(
                "timeline"
            ),
            list,
        )
    ):
        return timeline

    result = dict(
        timeline
    )

    result[
        "move_semantics_model"
    ] = "member_state_transfer"

    cleaned = []

    for frame in timeline[
        "timeline"
    ]:
        if not isinstance(
            frame,
            dict
        ):
            continue

        copied = dict(
            frame
        )

        copied[
            "cause"
        ] = move_semantics_cause_for_client(
            copied.get(
                "cause",
                {},
            )
        )

        stack = copied.get(
            "stack"
        )

        if isinstance(
            stack,
            list
        ):
            copied[
                "stack"
            ] = [
                move_semantics_object_for_client(
                    object_state
                )
                for object_state in stack
            ]

        aliases = copied.get(
            "aliases"
        )

        if isinstance(
            aliases,
            list
        ):
            # Once a constructor parameter leaves its scope, it should not
            # remain visually presented as an active reference.
            copied[
                "aliases"
            ] = [
                alias
                for alias in aliases
                if (
                    isinstance(
                        alias,
                        dict
                    ) and
                    alias.get(
                        "alive",
                        True
                    )
                )
            ]

        cleaned.append(
            copied
        )

    result[
        "timeline"
    ] = cleaned

    return result


def visualization_timeline_for_client(
    exercise_id: str,
    timeline,
):
    topic = exercise_topic_for_visualization(
        exercise_id
    )

    if topic == "move_semantics":
        return move_semantics_timeline_for_client(
            timeline
        )

    if (
        topic != "raii_scope" or
        not isinstance(
            timeline,
            dict
        ) or
        not isinstance(
            timeline.get(
                "timeline"
            ),
            list,
        )
    ):
        return timeline

    result = dict(
        timeline
    )

    raw_frames = timeline[
        "timeline"
    ]

    learner_scope = (
        raii_learner_operation_for_visualization(
            exercise_id
        )
    )

    if learner_scope:
        result[
            "raii_learner_operation"
        ] = learner_scope

    cleaned = []

    for frame in raw_frames:
        if not isinstance(
            frame,
            dict
        ):
            continue

        cause = frame.get(
            "cause",
            {}
        )

        if isinstance(
            cause,
            dict
        ):
            cause_type = cause.get(
                "type"
            )
            cause_subject = cause.get(
                "subject"
            )

            if (
                cause_type in {
                    "ENTER_SCOPE",
                    "EXIT_SCOPE",
                } and
                (
                    cause_subject == "processVideoFrame" or
                    raii_internal_lifecycle_scope(
                        cause_subject
                    )
                )
            ):
                continue

        copied = dict(
            frame
        )

        copied[
            "cause"
        ] = raii_cause_for_client(
            cause
        )

        scopes = copied.get(
            "active_scopes"
        )

        if isinstance(
            scopes,
            list
        ):
            copied[
                "active_scopes"
            ] = [
                scope
                for scope in scopes
                if (
                    scope != "processVideoFrame" and
                    not raii_internal_lifecycle_scope(
                        scope
                    )
                )
            ]

        stack = copied.get(
            "stack"
        )

        if isinstance(
            stack,
            list
        ):
            copied[
                "stack"
            ] = [
                raii_object_for_client(
                    object_state,
                    learner_scope,
                )
                for object_state in stack
            ]

        cleaned.append(
            copied
        )

    for index, frame in enumerate(
        cleaned,
        start=1,
    ):
        frame[
            "step"
        ] = index

    result[
        "timeline"
    ] = cleaned

    return result



def authoring_candidate_summary(
    candidate_id: str
) -> dict:
    candidate_path, validation_path = (
        authoring_candidate_paths(
            candidate_id
        )
    )

    candidate = read_optional_json(
        candidate_path
    )

    if not isinstance(
        candidate,
        dict
    ):
        raise FileNotFoundError(
            candidate_path
        )

    exercise = candidate.get(
        "exercise",
        {}
    )

    validation = read_optional_json(
        validation_path
    )

    validator_path = (
        TOOLS_DIRECTORY /
        "exercise_validator.py"
    )

    validation_stale = False

    validation_dependencies = [
        validator_path,
        DIFFICULTY_PROFILES_PATH,
    ]

    if (
        isinstance(
            validation,
            dict
        ) and
        validation_path.exists() and
        all(
            path.exists()
            for path in validation_dependencies
        )
    ):
        try:
            newest_dependency_mtime = max(
                path.stat().st_mtime
                for path in validation_dependencies
            )

            validation_stale = (
                validation_path.stat().st_mtime <
                newest_dependency_mtime
            )
        except OSError:
            validation_stale = True

    published = (
        candidate_id in
        exercise_map()
    )

    return {
        "id":
            candidate_id,
        "title":
            exercise.get(
                "title",
                candidate_id
            ),
        "topic":
            exercise.get(
                "topic",
                ""
            ),
        "difficulty":
            exercise.get(
                "difficulty",
                ""
            ),
        "scenario":
            exercise.get(
                "scenario",
                ""
            ),
        "problem_statement":
            exercise.get(
                "problem_statement",
                ""
            ),
        "learner_goal":
            learner_goal_for_exercise(
                exercise
            ),
        "generation_metadata":
            candidate.get(
                "generation_metadata",
                {}
            ),
        "validation":
            validation,
        "validation_stale":
            validation_stale,
        "valid":
            bool(
                isinstance(
                    validation,
                    dict
                ) and
                validation.get(
                    "valid"
                ) and
                not validation_stale
            ),
        "published":
            published,
    }


def list_authoring_candidates() -> list[dict]:
    GENERATED_CANDIDATE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    result = []

    for path in sorted(
        GENERATED_CANDIDATE_DIRECTORY.glob(
            "*.json"
        ),
        key=lambda item:
            item.stat().st_mtime,
        reverse=True,
    ):
        if path.name.endswith(
            ".validation.json"
        ):
            continue

        candidate_id = path.stem

        if not authoring_candidate_id_is_safe(
            candidate_id
        ):
            continue

        try:
            result.append(
                authoring_candidate_summary(
                    candidate_id
                )
            )
        except (
            OSError,
            ValueError,
            FileNotFoundError
        ):
            continue

    return result


def authoring_candidate_document(
    candidate_id: str
) -> dict:
    candidate_path, validation_path = (
        authoring_candidate_paths(
            candidate_id
        )
    )

    candidate = read_optional_json(
        candidate_path
    )

    if not isinstance(
        candidate,
        dict
    ):
        raise FileNotFoundError(
            candidate_path
        )

    return {
        "candidate":
            candidate,
        "validation":
            read_optional_json(
                validation_path
            ),
        "published":
            candidate_id in
            exercise_map(),
    }


def published_authoring_summaries() -> list[dict]:
    result = []

    for exercise_id, item in (
        exercise_map().items()
    ):
        try:
            exercise = read_exercise_document(
                item
            )
        except (
            OSError,
            json.JSONDecodeError,
            KeyError
        ):
            continue

        result.append({
            "id":
                exercise_id,
            "title":
                exercise.get(
                    "title",
                    exercise_id
                ),
            "topic":
                exercise.get(
                    "topic",
                    ""
                ),
            "difficulty":
                exercise.get(
                    "difficulty",
                    ""
                ),
            "ai_generated":
                exercise_id.startswith(
                    "ai_"
                ),
        })

    result.sort(
        key=lambda item: (
            item["topic"],
            item["title"],
        )
    )

    return result


def run_authoring_command(
    command: list[str],
    *,
    timeout: int = AUTHORING_TIMEOUT_SECONDS
) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=str(
            PROJECT_ROOT
        ),
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
        env=os.environ.copy(),
    )


def validate_authoring_candidate(
    candidate_id: str
) -> dict:
    candidate_path, validation_path = (
        authoring_candidate_paths(
            candidate_id
        )
    )

    if not candidate_path.exists():
        raise FileNotFoundError(
            candidate_path
        )

    clear_candidate_reference_timeline(
        candidate_id
    )

    completed = run_authoring_command(
        [
            sys.executable,
            str(
                TOOLS_DIRECTORY /
                "exercise_validator.py"
            ),
            str(
                candidate_path.relative_to(
                    PROJECT_ROOT
                )
            ),
            "--json",
        ]
    )

    try:
        payload = json.loads(
            completed.stdout
        )
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "Validator did not return machine-readable JSON.\n" +
            completed.stdout +
            completed.stderr
        ) from error

    report = (
        payload.get(
            "reports",
            [{}]
        )[0]
    )

    validation_path.write_text(
        json.dumps(
            report,
            indent=2
        ) +
        "\n",
        encoding="utf-8"
    )

    if bool(
        report.get(
            "valid"
        )
    ):
        reference_timeline = (
            read_generated_timeline(
                candidate_id
            )
        )

        if reference_timeline is None:
            raise RuntimeError(
                "Validation passed, but its final reference timeline "
                "could not be read for authoring delivery."
            )

        expected_count = (
            validation_visualization_snapshot_count(
                report,
                "runtime.reference_visualization",
            )
        )

        actual_count = (
            timeline_snapshot_count(
                reference_timeline
            )
        )

        if (
            expected_count is not None and
            actual_count != expected_count
        ):
            raise RuntimeError(
                "Validation/reference timeline delivery mismatch: "
                f"validator reported {expected_count} snapshot(s), "
                f"but the final generated reference timeline contains "
                f"{actual_count}."
            )

        archive_candidate_reference_timeline(
            candidate_id,
            reference_timeline,
        )

    return {
        "ok":
            completed.returncode == 0,
        "valid":
            bool(
                report.get(
                    "valid"
                )
            ),
        "report":
            report,
        "stdout":
            completed.stdout,
        "stderr":
            completed.stderr,
    }


class CppTeacherHandler(
    SimpleHTTPRequestHandler
):
    def __init__(
        self,
        *args,
        **kwargs
    ):
        super().__init__(
            *args,
            directory=str(
                PROJECT_ROOT
            ),
            **kwargs
        )

    def end_headers(
        self
    ):
        path = urlparse(
            self.path
        ).path

        if (
            path == "/visualizer" or
            path.startswith(
                "/visualizer/"
            )
        ):
            self.send_header(
                "Cache-Control",
                (
                    "no-store, no-cache, "
                    "must-revalidate, max-age=0"
                )
            )
            self.send_header(
                "Pragma",
                "no-cache"
            )
            self.send_header(
                "Expires",
                "0"
            )

        super().end_headers()

    def log_message(
        self,
        format,
        *args
    ):
        sys.stdout.write(
            "[cpp-teacher] " +
            (format % args) +
            "\n"
        )

    def send_json(
        self,
        payload: dict,
        status: HTTPStatus =
            HTTPStatus.OK
    ):
        body = json.dumps(
            payload
        ).encode(
            "utf-8"
        )

        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(
                len(body)
            )
        )

        self.send_header(
            "Cache-Control",
            "no-store"
        )

        self.end_headers()

        self.wfile.write(
            body
        )

    def read_json_body(self):
        content_length = int(
            self.headers.get(
                "Content-Length",
                "0"
            )
        )

        if content_length == 0:
            return {}

        if (
            content_length < 0 or
            content_length >
                MAX_REQUEST_BYTES
        ):
            raise ValueError(
                "Request body is too large."
            )

        raw_body = self.rfile.read(
            content_length
        )

        return json.loads(
            raw_body.decode(
                "utf-8"
            )
        )

    def handle_authoring_generate(self):
        try:
            request_data = self.read_json_body()
        except (
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError
        ):
            self.send_json(
                {
                    "ok": False,
                    "error": "Request body must be valid JSON.",
                },
                HTTPStatus.BAD_REQUEST
            )
            return

        if not os.environ.get(
            "OPENAI_API_KEY",
            ""
        ).strip():
            self.send_json(
                {
                    "ok": False,
                    "error": (
                        "OPENAI_API_KEY is not configured. "
                        "Copy .env.example to .env and set the key."
                    ),
                },
                HTTPStatus.BAD_REQUEST
            )
            return

        topic = str(
            request_data.get(
                "topic",
                ""
            )
        ).strip()

        difficulty = str(
            request_data.get(
                "difficulty",
                ""
            )
        ).strip()

        topic_ids = {
            item.get("id")
            for item in load_topics_catalog()
            if isinstance(
                item,
                dict
            )
        }

        if topic not in topic_ids:
            self.send_json(
                {
                    "ok": False,
                    "error": "Unknown topic.",
                },
                HTTPStatus.BAD_REQUEST
            )
            return

        if difficulty not in {
            "easy",
            "medium",
            "hard",
        }:
            self.send_json(
                {
                    "ok": False,
                    "error": "Difficulty must be easy, medium, or hard.",
                },
                HTTPStatus.BAD_REQUEST
            )
            return

        try:
            max_repairs = int(
                request_data.get(
                    "max_repairs",
                    2
                )
            )
        except (
            TypeError,
            ValueError
        ):
            max_repairs = 2

        max_repairs = max(
            0,
            min(
                max_repairs,
                5
            )
        )

        model = str(
            request_data.get(
                "model",
                ""
            )
        ).strip()

        command = [
            sys.executable,
            str(
                TOOLS_DIRECTORY /
                "generate_exercise.py"
            ),
            "--topic",
            topic,
            "--difficulty",
            difficulty,
            "--max-repairs",
            str(
                max_repairs
            ),
        ]

        if model:
            if not re.fullmatch(
                r"[A-Za-z0-9._-]+",
                model
            ):
                self.send_json(
                    {
                        "ok": False,
                        "error": "Model id contains unsupported characters.",
                    },
                    HTTPStatus.BAD_REQUEST
                )
                return

            command.extend(
                [
                    "--model",
                    model,
                ]
            )

        try:
            with AUTHORING_LOCK:
                completed = run_authoring_command(
                    command
                )
        except subprocess.TimeoutExpired:
            self.send_json(
                {
                    "ok": False,
                    "error": "AI generation exceeded the authoring timeout.",
                },
                HTTPStatus.REQUEST_TIMEOUT
            )
            return

        combined_log = (
            completed.stdout +
            (
                "\n" +
                completed.stderr
                if completed.stderr
                else ""
            )
        ).strip()

        match = re.search(
            r"Candidate id:\s*([a-z0-9_]+)",
            completed.stdout
        )

        candidate = None

        if match:
            candidate_id = match.group(1)

            try:
                candidate = authoring_candidate_summary(
                    candidate_id
                )
            except (
                OSError,
                ValueError,
                FileNotFoundError
            ):
                candidate = None

        if completed.returncode == 2:
            self.send_json(
                {
                    "ok": False,
                    "error": "AI generation could not run.",
                    "log": combined_log,
                    "candidate": candidate,
                },
                HTTPStatus.BAD_REQUEST
            )
            return

        self.send_json({
            "ok": True,
            "valid": bool(
                candidate and
                candidate.get(
                    "valid"
                )
            ),
            "candidate": candidate,
            "log": combined_log,
            "process_returncode": completed.returncode,
        })

    def handle_authoring_repair(self):
        try:
            request_data = self.read_json_body()
        except (
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError
        ):
            self.send_json(
                {
                    "ok": False,
                    "error": "Request body must be valid JSON.",
                },
                HTTPStatus.BAD_REQUEST
            )
            return

        if not os.environ.get(
            "OPENAI_API_KEY",
            ""
        ).strip():
            self.send_json(
                {
                    "ok": False,
                    "error": "OPENAI_API_KEY is not configured.",
                },
                HTTPStatus.BAD_REQUEST
            )
            return

        candidate_id = str(
            request_data.get(
                "candidate_id",
                ""
            )
        ).strip()

        try:
            candidate_path, _ = (
                authoring_candidate_paths(
                    candidate_id
                )
            )
        except ValueError as error:
            self.send_json(
                {
                    "ok": False,
                    "error": str(error),
                },
                HTTPStatus.BAD_REQUEST
            )
            return

        if not candidate_path.exists():
            self.send_json(
                {
                    "ok": False,
                    "error": "Candidate does not exist.",
                },
                HTTPStatus.NOT_FOUND
            )
            return

        try:
            max_repairs = int(
                request_data.get(
                    "max_repairs",
                    2
                )
            )
        except (
            TypeError,
            ValueError
        ):
            max_repairs = 2

        max_repairs = max(
            1,
            min(
                max_repairs,
                5
            )
        )

        model = str(
            request_data.get(
                "model",
                ""
            )
        ).strip()

        command = [
            sys.executable,
            str(
                TOOLS_DIRECTORY /
                "generate_exercise.py"
            ),
            "--repair-candidate",
            candidate_id,
            "--max-repairs",
            str(
                max_repairs
            ),
        ]

        if model:
            if not re.fullmatch(
                r"[A-Za-z0-9._-]+",
                model
            ):
                self.send_json(
                    {
                        "ok": False,
                        "error": "Model id contains unsupported characters.",
                    },
                    HTTPStatus.BAD_REQUEST
                )
                return

            command.extend(
                [
                    "--model",
                    model,
                ]
            )

        try:
            with AUTHORING_LOCK:
                completed = run_authoring_command(
                    command
                )
        except subprocess.TimeoutExpired:
            self.send_json(
                {
                    "ok": False,
                    "error": "AI repair exceeded the authoring timeout.",
                },
                HTTPStatus.REQUEST_TIMEOUT
            )
            return

        combined_log = (
            completed.stdout +
            (
                "\n" +
                completed.stderr
                if completed.stderr
                else ""
            )
        ).strip()

        try:
            candidate = authoring_candidate_summary(
                candidate_id
            )
        except (
            OSError,
            ValueError,
            FileNotFoundError
        ):
            candidate = None

        if completed.returncode == 2:
            self.send_json(
                {
                    "ok": False,
                    "error": "AI repair could not run.",
                    "log": combined_log,
                    "candidate": candidate,
                },
                HTTPStatus.BAD_REQUEST
            )
            return

        self.send_json({
            "ok": True,
            "valid": bool(
                candidate and
                candidate.get(
                    "valid"
                )
            ),
            "candidate": candidate,
            "log": combined_log,
            "process_returncode": completed.returncode,
        })

    def handle_authoring_validate(self):
        try:
            request_data = self.read_json_body()
            candidate_id = str(
                request_data.get(
                    "candidate_id",
                    ""
                )
            ).strip()

            with AUTHORING_LOCK:
                result = validate_authoring_candidate(
                    candidate_id
                )

            self.send_json({
                "ok": True,
                "valid": result["valid"],
                "report": result["report"],
                "candidate": authoring_candidate_summary(
                    candidate_id
                ),
                "log": (
                    result["stdout"] +
                    result["stderr"]
                ),
            })
        except FileNotFoundError:
            self.send_json(
                {
                    "ok": False,
                    "error": "Candidate does not exist.",
                },
                HTTPStatus.NOT_FOUND
            )
        except (
            ValueError,
            RuntimeError
        ) as error:
            self.send_json(
                {
                    "ok": False,
                    "error": str(error),
                },
                HTTPStatus.BAD_REQUEST
            )
        except subprocess.TimeoutExpired:
            self.send_json(
                {
                    "ok": False,
                    "error": "Validation timed out.",
                },
                HTTPStatus.REQUEST_TIMEOUT
            )

    def handle_authoring_publish(self):
        try:
            request_data = self.read_json_body()
            candidate_id = str(
                request_data.get(
                    "candidate_id",
                    ""
                )
            ).strip()

            candidate_path, _ = authoring_candidate_paths(
                candidate_id
            )

            if not candidate_path.exists():
                raise FileNotFoundError(
                    candidate_path
                )

            with AUTHORING_LOCK:
                validation = validate_authoring_candidate(
                    candidate_id
                )

                if not validation["valid"]:
                    self.send_json(
                        {
                            "ok": False,
                            "error": "Candidate is invalid and cannot be published.",
                            "report": validation["report"],
                        },
                        HTTPStatus.CONFLICT
                    )
                    return

                completed = run_authoring_command(
                    [
                        sys.executable,
                        str(
                            TOOLS_DIRECTORY /
                            "publish_candidate.py"
                        ),
                        str(
                            candidate_path.relative_to(
                                PROJECT_ROOT
                            )
                        ),
                        "--force",
                    ]
                )

            log = (
                completed.stdout +
                completed.stderr
            )

            if completed.returncode != 0:
                self.send_json(
                    {
                        "ok": False,
                        "error": "Publisher rejected the candidate.",
                        "log": log,
                    },
                    HTTPStatus.CONFLICT
                )
                return

            self.send_json({
                "ok": True,
                "candidate": authoring_candidate_summary(
                    candidate_id
                ),
                "log": log,
            })
        except FileNotFoundError:
            self.send_json(
                {
                    "ok": False,
                    "error": "Candidate does not exist.",
                },
                HTTPStatus.NOT_FOUND
            )
        except (
            ValueError,
            RuntimeError
        ) as error:
            self.send_json(
                {
                    "ok": False,
                    "error": str(error),
                },
                HTTPStatus.BAD_REQUEST
            )
        except subprocess.TimeoutExpired:
            self.send_json(
                {
                    "ok": False,
                    "error": "Publishing timed out.",
                },
                HTTPStatus.REQUEST_TIMEOUT
            )

    def handle_authoring_unpublish(self):
        try:
            request_data = self.read_json_body()
        except (
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError
        ):
            self.send_json(
                {
                    "ok": False,
                    "error": "Request body must be valid JSON.",
                },
                HTTPStatus.BAD_REQUEST
            )
            return

        exercise_id = str(
            request_data.get(
                "exercise_id",
                ""
            )
        ).strip()

        if not authoring_candidate_id_is_safe(
            exercise_id
        ):
            self.send_json(
                {
                    "ok": False,
                    "error": "Invalid exercise id.",
                },
                HTTPStatus.BAD_REQUEST
            )
            return

        if exercise_id not in exercise_map():
            self.send_json(
                {
                    "ok": False,
                    "error": "Exercise is not currently published.",
                },
                HTTPStatus.NOT_FOUND
            )
            return

        command = [
            sys.executable,
            str(
                TOOLS_DIRECTORY /
                "unpublish_exercise.py"
            ),
            exercise_id,
        ]

        if bool(
            request_data.get(
                "delete_progress",
                False
            )
        ):
            command.append(
                "--delete-progress"
            )

        try:
            with AUTHORING_LOCK:
                completed = run_authoring_command(
                    command
                )
        except subprocess.TimeoutExpired:
            self.send_json(
                {
                    "ok": False,
                    "error": "Unpublish timed out.",
                },
                HTTPStatus.REQUEST_TIMEOUT
            )
            return

        log = (
            completed.stdout +
            completed.stderr
        )

        if completed.returncode != 0:
            self.send_json(
                {
                    "ok": False,
                    "error": "Exercise could not be unpublished.",
                    "log": log,
                },
                HTTPStatus.CONFLICT
            )
            return

        self.send_json({
            "ok": True,
            "exercise_id": exercise_id,
            "log": log,
        })

    def do_GET(self):
        parsed = urlparse(
            self.path
        )

        path = parsed.path

        if path == "/api/health":
            self.send_json({
                "ok":
                    True,
                "grader_built":
                    CPP_TEACHER_PATH.exists(),
                "ai_generation_configured":
                    bool(
                        os.environ.get(
                            "OPENAI_API_KEY",
                            ""
                        ).strip()
                    ),
            })

            return

        if path == "/api/authoring/status":
            self.send_json({
                "ok": True,
                "api_key_configured": bool(
                    os.environ.get(
                        "OPENAI_API_KEY",
                        ""
                    ).strip()
                ),
                "model": (
                    os.environ.get(
                        "OPENAI_MODEL",
                        ""
                    ).strip()
                    or
                    "gpt-5.6-terra"
                ),
                "grader_built": CPP_TEACHER_PATH.exists(),
                "topics": load_topics_catalog(),
                "candidates": list_authoring_candidates(),
                "published_exercises": published_authoring_summaries(),
            })
            return

        if path == "/api/authoring/candidates":
            self.send_json({
                "ok": True,
                "candidates": list_authoring_candidates(),
            })
            return

        if (
            path.startswith(
                "/api/authoring/candidates/"
            ) and
            path.endswith(
                "/reference-visualization"
            )
        ):
            candidate_id = (
                path.removeprefix(
                    "/api/authoring/candidates/"
                )
                .removesuffix(
                    "/reference-visualization"
                )
                .strip("/")
            )

            if (
                not candidate_id or
                not authoring_candidate_id_is_safe(
                    candidate_id
                )
            ):
                self.send_json(
                    {
                        "ok": False,
                        "error": "Invalid candidate id.",
                    },
                    HTTPStatus.BAD_REQUEST
                )
                return

            candidate_path, _ = (
                authoring_candidate_paths(
                    candidate_id
                )
            )

            if not candidate_path.exists():
                self.send_json(
                    {
                        "ok": False,
                        "error": "Candidate does not exist.",
                    },
                    HTTPStatus.NOT_FOUND
                )
                return

            timeline = read_candidate_reference_timeline(
                candidate_id
            )

            if timeline is None:
                self.send_json(
                    {
                        "ok": False,
                        "error": (
                            "No current validated reference visualization "
                            "exists yet. Revalidate this candidate, then "
                            "reopen Reference Solution."
                        ),
                    },
                    HTTPStatus.NOT_FOUND
                )
                return

            self.send_json({
                "ok": True,
                "exercise_id": candidate_id,
                "timeline": visualization_timeline_for_client(
                    candidate_id,
                    timeline,
                ),
            })

            return

        if path.startswith(
            "/api/authoring/candidates/"
        ):
            candidate_id = (
                path.removeprefix(
                    "/api/authoring/candidates/"
                )
                .strip("/")
            )

            if (
                not candidate_id or
                "/" in candidate_id
            ):
                self.send_json(
                    {
                        "ok": False,
                        "error": "Invalid candidate id.",
                    },
                    HTTPStatus.BAD_REQUEST
                )
                return

            try:
                document = authoring_candidate_document(
                    candidate_id
                )
            except (
                FileNotFoundError,
                ValueError
            ):
                self.send_json(
                    {
                        "ok": False,
                        "error": "Candidate does not exist.",
                    },
                    HTTPStatus.NOT_FOUND
                )
                return

            self.send_json({
                "ok": True,
                **document,
            })
            return

        if path == "/api/exercises":
            try:
                metadata = [
                    public_exercise_metadata(
                        item
                    )
                    for item in
                    exercise_map().values()
                ]
            except (
                OSError,
                json.JSONDecodeError,
                KeyError
            ) as error:
                self.send_json(
                    {
                        "ok":
                            False,
                        "error":
                            str(error),
                    },
                    HTTPStatus.INTERNAL_SERVER_ERROR
                )

                return

            metadata.sort(
                key=lambda item: (
                    item["topic"].lower(),
                    item["title"].lower(),
                )
            )

            self.send_json({
                "ok":
                    True,
                "library_version":
                    1,
                "exercises":
                    metadata,
            })

            return

        if path.startswith(
            "/api/exercises/"
        ):
            remainder = (
                path.removeprefix(
                    "/api/exercises/"
                )
                .strip("/")
            )

            parts = [
                part
                for part in
                remainder.split("/")
                if part
            ]

            if not parts:
                self.send_json(
                    {
                        "ok":
                            False,
                        "error":
                            "Exercise id is required.",
                    },
                    HTTPStatus.NOT_FOUND
                )

                return

            exercise_id = parts[0]

            library_item = (
                exercise_map().get(
                    exercise_id
                )
            )

            if library_item is None:
                self.send_json(
                    {
                        "ok":
                            False,
                        "error":
                            "Unknown exercise.",
                    },
                    HTTPStatus.NOT_FOUND
                )

                return

            if (
                len(parts) == 3 and
                parts[1] == "solution" and
                parts[2] == "visualization"
            ):
                if not solution_is_revealed(
                    exercise_id
                ):
                    self.send_json(
                        {
                            "ok": False,
                            "error": (
                                "The solution visualization "
                                "is not revealed yet."
                            ),
                        },
                        HTTPStatus.FORBIDDEN
                    )

                    return

                timeline = (
                    reference_timeline_for_solution_view(
                        exercise_id
                    )
                )

                if timeline is None:
                    self.send_json(
                        {
                            "ok": False,
                            "error": (
                                "No current reference visualization "
                                "exists yet. Generated candidates must "
                                "be revalidated before reopening "
                                "Reference Solution."
                            ),
                        },
                        HTTPStatus.NOT_FOUND
                    )

                    return

                self.send_json({
                    "ok": True,
                    "exercise_id": exercise_id,
                    "timeline": visualization_timeline_for_client(
                        exercise_id,
                        timeline,
                    ),
                })

                return

            if (
                len(parts) == 4 and
                parts[1] == "attempts" and
                parts[2] == "latest" and
                parts[3] ==
                    "visualization"
            ):
                timeline = (
                    latest_attempt_timeline(
                        exercise_id
                    )
                )

                if timeline is None:
                    self.send_json(
                        {
                            "ok":
                                False,
                            "error":
                                (
                                    "No saved attempt "
                                    "visualization exists yet."
                                ),
                        },
                        HTTPStatus.NOT_FOUND
                    )

                    return

                self.send_json({
                    "ok":
                        True,
                    "exercise_id":
                        exercise_id,
                    "timeline":
                        visualization_timeline_for_client(
                            exercise_id,
                            timeline,
                        ),
                })

                return

            if len(parts) != 1:
                self.send_json(
                    {
                        "ok":
                            False,
                        "error":
                            "Unknown exercise endpoint.",
                    },
                    HTTPStatus.NOT_FOUND
                )

                return

            try:
                document = (
                    public_exercise_document(
                        library_item
                    )
                )

                progress = (
                    public_progress(
                        exercise_id
                    )
                )

                saved_submission = (
                    latest_submission(
                        exercise_id
                    )
                )
            except (
                OSError,
                json.JSONDecodeError,
                KeyError
            ) as error:
                self.send_json(
                    {
                        "ok":
                            False,
                        "error":
                            str(error),
                    },
                    HTTPStatus.INTERNAL_SERVER_ERROR
                )

                return

            self.send_json({
                "ok":
                    True,
                "exercise":
                    document,
                "progress":
                    progress,
                "saved_submission":
                    saved_submission,
            })

            return

        private_prefixes = (
            "/catalog/",
            "/candidates/",
            "/schemas/",
            "/tools/",
            "/data/",
            "/exercises/",
            "/tests/",
            "/support/",
            "/analysis_support/",
            "/src/",
            "/include/",
            "/build/",
            "/output/",
        )

        private_exact = {
            "/CMakeLists.txt",
            "/dev_server.py",
        }

        if (
            path.startswith(
                private_prefixes
            ) or
            path in private_exact
        ):
            self.send_error(
                HTTPStatus.NOT_FOUND,
                (
                    "Not available from "
                    "the learner interface."
                )
            )

            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(
            self.path
        )

        path = parsed.path

        if path == "/api/authoring/generate":
            self.handle_authoring_generate()

            return

        if path == "/api/authoring/repair":
            self.handle_authoring_repair()

            return

        if path == "/api/authoring/validate":
            self.handle_authoring_validate()

            return

        if path == "/api/authoring/publish":
            self.handle_authoring_publish()

            return

        if path == "/api/authoring/unpublish":
            self.handle_authoring_unpublish()

            return

        if path == "/api/grade":
            self.handle_grade()

            return

        if path.startswith(
            "/api/exercises/"
        ):
            remainder = (
                path.removeprefix(
                    "/api/exercises/"
                )
                .strip("/")
            )

            parts = [
                part
                for part in
                remainder.split("/")
                if part
            ]

            if (
                len(parts) == 3 and
                parts[1] == "solution" and
                parts[2] == "reveal"
            ):
                self.handle_solution_reveal(
                    parts[0]
                )

                return

            if (
                len(parts) == 3 and
                parts[1] == "solution" and
                parts[2] == "visualize"
            ):
                self.handle_solution_visualize(
                    parts[0]
                )

                return

        self.send_json(
            {
                "ok":
                    False,
                "error":
                    "Unknown API endpoint.",
            },
            HTTPStatus.NOT_FOUND
        )

    def handle_grade(self):
        try:
            request_data = (
                self.read_json_body()
            )
        except (
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError
        ):
            self.send_json(
                {
                    "ok":
                        False,
                    "error":
                        "Request body must be valid JSON.",
                },
                HTTPStatus.BAD_REQUEST
            )

            return

        exercise_id = (
            request_data.get(
                "exercise_id",
                ""
            )
        )

        source = request_data.get(
            "source",
            ""
        )

        if not isinstance(
            source,
            str
        ):
            self.send_json(
                {
                    "ok":
                        False,
                    "error":
                        "source must be a string.",
                },
                HTTPStatus.BAD_REQUEST
            )

            return

        library_item = (
            exercise_map().get(
                exercise_id
            )
        )

        if library_item is None:
            self.send_json(
                {
                    "ok":
                        False,
                    "error":
                        "Unknown exercise_id.",
                },
                HTTPStatus.BAD_REQUEST
            )

            return

        try:
            exercise_file = (
                validate_exercise_file(
                    library_item
                )
            )

            grader_result = (
                run_grader(
                    exercise_file,
                    source
                )
            )
        except (
            RuntimeError,
            OSError,
            ValueError
        ) as error:
            self.send_json(
                {
                    "ok":
                        False,
                    "error":
                        str(error),
                },
                HTTPStatus.INTERNAL_SERVER_ERROR
            )

            return
        except subprocess.TimeoutExpired:
            self.send_json(
                {
                    "ok":
                        False,
                    "error":
                        (
                            "The grading process exceeded "
                            f"{GRADE_TIMEOUT_SECONDS} seconds."
                        ),
                },
                HTTPStatus.REQUEST_TIMEOUT
            )

            return

        grade = grader_result[
            "grade"
        ]

        passed = bool(
            grade.get(
                "passed",
                False
            )
        )

        attempt_result = record_attempt(
            exercise_id,
            source,
            passed,
            grader_result[
                "timeline"
            ]
        )

        self.send_json({
            "ok":
                True,
            "exercise_id":
                exercise_id,
            "passed":
                passed,
            "grade":
                grade,
            "server_stderr":
                grader_result[
                    "stderr"
                ],
            "timeline":
                visualization_timeline_for_client(
                    exercise_id,
                    grader_result[
                        "timeline"
                    ],
                ),
            "attempt":
                attempt_result[
                    "attempt"
                ],
            "progress":
                attempt_result[
                    "progress"
                ],
        })

    def handle_solution_reveal(
        self,
        exercise_id: str
    ):
        library_item = (
            exercise_map().get(
                exercise_id
            )
        )

        if library_item is None:
            self.send_json(
                {
                    "ok":
                        False,
                    "error":
                        "Unknown exercise.",
                },
                HTTPStatus.NOT_FOUND
            )

            return

        if not solution_is_available(
            exercise_id
        ):
            self.send_json(
                {
                    "ok":
                        False,
                    "available":
                        False,
                    "error":
                        (
                            "The solution unlocks "
                            "after at least one failed attempt."
                        ),
                },
                HTTPStatus.FORBIDDEN
            )

            return

        exercise = read_exercise_document(
            library_item
        )

        reference_solution = (
            exercise.get(
                "reference_solution"
            )
        )

        if not reference_solution:
            self.send_json(
                {
                    "ok":
                        False,
                    "error":
                        "This exercise has no reference solution.",
                },
                HTTPStatus.NOT_FOUND
            )

            return

        mark_solution_revealed(
            exercise_id
        )

        self.send_json({
            "ok":
                True,
            "available":
                True,
            "solution":
                reference_solution,
            "explanation":
                exercise.get(
                    "explanation",
                    ""
                ),
            "progress":
                public_progress(
                    exercise_id
                ),
        })

    def handle_solution_visualize(
        self,
        exercise_id: str
    ):
        library_item = (
            exercise_map().get(
                exercise_id
            )
        )

        if library_item is None:
            self.send_json(
                {
                    "ok":
                        False,
                    "error":
                        "Unknown exercise.",
                },
                HTTPStatus.NOT_FOUND
            )

            return

        if not solution_is_available(
            exercise_id
        ):
            self.send_json(
                {
                    "ok":
                        False,
                    "error":
                        (
                            "The solution unlocks "
                            "after at least one failed attempt."
                        ),
                },
                HTTPStatus.FORBIDDEN
            )

            return

        if not solution_is_revealed(
            exercise_id
        ):
            self.send_json(
                {
                    "ok":
                        False,
                    "error":
                        (
                            "Reveal the solution before "
                            "visualizing it."
                        ),
                },
                HTTPStatus.FORBIDDEN
            )

            return

        # Generated authoring candidates already have an authoritative
        # validated reference timeline. Do not rerun the ordinary exercise
        # grader here: that can use older published/solution artifacts and
        # recreate a stale timeline that differs from validation.
        if authoring_candidate_id_is_safe(
            exercise_id
        ):
            try:
                candidate_path, _ = (
                    authoring_candidate_paths(
                        exercise_id
                    )
                )
            except ValueError:
                candidate_path = None

            if (
                candidate_path is not None and
                candidate_path.exists()
            ):
                timeline = (
                    read_candidate_reference_timeline(
                        exercise_id
                    )
                )

                if timeline is None:
                    self.send_json(
                        {
                            "ok":
                                False,
                            "error":
                                (
                                    "No current validated reference "
                                    "visualization exists for this generated "
                                    "candidate. Revalidate it before opening "
                                    "Reference Solution."
                                ),
                        },
                        HTTPStatus.NOT_FOUND
                    )

                    return

                self.send_json({
                    "ok":
                        True,
                    "exercise_id":
                        exercise_id,
                    "timeline":
                        visualization_timeline_for_client(
                            exercise_id,
                            timeline,
                        ),
                })

                return

        exercise = read_exercise_document(
            library_item
        )

        reference_solution = (
            exercise.get(
                "reference_solution"
            )
        )

        if not reference_solution:
            self.send_json(
                {
                    "ok":
                        False,
                    "error":
                        "This exercise has no reference solution.",
                },
                HTTPStatus.NOT_FOUND
            )

            return

        try:
            exercise_file = (
                validate_exercise_file(
                    library_item
                )
            )

            grader_result = (
                run_grader(
                    exercise_file,
                    reference_solution
                )
            )
        except (
            RuntimeError,
            OSError,
            ValueError
        ) as error:
            self.send_json(
                {
                    "ok":
                        False,
                    "error":
                        str(error),
                },
                HTTPStatus.INTERNAL_SERVER_ERROR
            )

            return
        except subprocess.TimeoutExpired:
            self.send_json(
                {
                    "ok":
                        False,
                    "error":
                        (
                            "The reference solution "
                            "timed out unexpectedly."
                        ),
                },
                HTTPStatus.REQUEST_TIMEOUT
            )

            return

        grade = grader_result[
            "grade"
        ]

        if not grade.get(
            "passed",
            False
        ):
            self.send_json(
                {
                    "ok":
                        False,
                    "error":
                        (
                            "The hidden reference solution "
                            "did not pass validation."
                        ),
                    "grade":
                        grade,
                },
                HTTPStatus.INTERNAL_SERVER_ERROR
            )

            return

        timeline = grader_result[
            "timeline"
        ]

        archive_solution_timeline(
            exercise_id,
            timeline
        )

        self.send_json({
            "ok":
                True,
            "exercise_id":
                exercise_id,
            "timeline":
                visualization_timeline_for_client(
                    exercise_id,
                    timeline,
                ),
        })


def main():
    port = 8000
    force_rebuild = False

    for argument in sys.argv[1:]:
        if argument == "--rebuild":
            force_rebuild = True
            continue

        try:
            port = int(
                argument
            )
        except ValueError:
            raise SystemExit(
                (
                    "Unknown argument: " +
                    argument +
                    "\nUsage: python3 dev_server.py [port] [--rebuild]"
                )
            )

    os.chdir(
        PROJECT_ROOT
    )

    DATA_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    GENERATED_CANDIDATE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    print(
        "C++ Teacher development server"
    )

    print(
        f"Project root: {PROJECT_ROOT}"
    )

    # Step 29: starting the app is also the build command. In normal use this
    # returns immediately when the grader executable is already current.
    try:
        ensure_cpp_teacher_built(
            force_clean=force_rebuild
        )
    except DevelopmentEnvironmentError as error:
        print(
            "\n[environment] " +
            str(error),
            file=sys.stderr
        )

        raise SystemExit(
            2
        )

    try:
        server = ThreadingHTTPServer(
            (
                "127.0.0.1",
                port
            ),
            CppTeacherHandler
        )
    except OSError as error:
        message = server_bind_error_message(
            error,
            port
        )

        if message is None:
            raise

        print(
            "\n[startup] " +
            message,
            file=sys.stderr
        )

        raise SystemExit(
            2
        )

    print(
        (
            "Progress store: "
            f"{PROGRESS_PATH}"
        )
    )

    print(
        (
            "AI authoring: " +
            (
                "configured"
                if os.environ.get(
                    "OPENAI_API_KEY",
                    ""
                ).strip()
                else "not configured"
            )
        )
    )

    print(
        (
            "Open: "
            f"http://localhost:{port}/visualizer/"
        )
    )

    print(
        "Press Ctrl+C to stop."
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(
            "\nStopping server."
        )
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
