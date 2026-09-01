#!/usr/bin/env python3

from __future__ import annotations

import errno
import importlib.util
import sys
import tempfile
import types
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

env_loader = types.ModuleType(
    "env_loader"
)

def load_project_env(_project_root):
    return None

env_loader.load_project_env = load_project_env
sys.modules["env_loader"] = env_loader

spec = importlib.util.spec_from_file_location(
    "cpp_teacher_dev_server_for_test",
    PROJECT_ROOT / "dev_server.py"
)

assert spec is not None
assert spec.loader is not None

server = importlib.util.module_from_spec(
    spec
)

spec.loader.exec_module(
    server
)


with tempfile.TemporaryDirectory() as temp:
    temp = Path(temp)

    elf = temp / "cpp_teacher_elf"
    elf.write_bytes(
        b"\x7fELF" + b"\0" * 32
    )

    pe = temp / "cpp_teacher.exe"
    pe.write_bytes(
        b"MZ" + b"\0" * 32
    )

    unknown = temp / "unknown"
    unknown.write_bytes(
        b"TEXT"
    )

    assert server.native_binary_format(
        elf
    ) == "elf"

    assert server.native_binary_format(
        pe
    ) == "pe"

    assert server.native_binary_format(
        unknown
    ) == "unknown"

    assert server.grader_platform_mismatch_message(
        elf,
        platform_name="linux"
    ) is None

    assert server.grader_platform_mismatch_message(
        pe,
        platform_name="win32"
    ) is None

    windows_vs_wsl = (
        server.grader_platform_mismatch_message(
            elf,
            platform_name="win32"
        )
    )

    assert windows_vs_wsl is not None
    assert "Windows Python" in windows_vs_wsl
    assert "WSL terminal" in windows_vs_wsl
    assert "python3 dev_server.py" in windows_vs_wsl

    linux_vs_windows = (
        server.grader_platform_mismatch_message(
            pe,
            platform_name="linux"
        )
    )

    assert linux_vs_windows is not None
    assert "Windows grader" in linux_vs_windows
    assert "--rebuild" in linux_vs_windows

    try:
        server.ensure_grader_platform_compatible(
            elf,
            platform_name="win32"
        )
    except server.DevelopmentEnvironmentError as error:
        assert "platform mismatch" in str(
            error
        )
    else:
        raise AssertionError(
            "Windows Python must reject a Linux ELF grader."
        )


address_in_use = OSError(
    errno.EADDRINUSE,
    "Address already in use"
)

bind_message = (
    server.server_bind_error_message(
        address_in_use,
        8000
    )
)

assert bind_message is not None
assert "Port 8000 is already in use." in bind_message
assert "ss -ltnp" in bind_message
assert "pkill -f dev_server.py" in bind_message

other_error = OSError(
    errno.EACCES,
    "Permission denied"
)

assert (
    server.server_bind_error_message(
        other_error,
        8000
    ) is None
)

exec_format_error = OSError(
    errno.ENOEXEC,
    "Exec format error"
)

launch_message = (
    server.grader_launch_error_message(
        exec_format_error
    )
)

assert launch_message is not None
assert (
    "could not be executed" in launch_message or
    "platform mismatch" in launch_message
)

source = (
    PROJECT_ROOT /
    "dev_server.py"
).read_text(
    encoding="utf-8"
)

assert "except DevelopmentEnvironmentError as error:" in source
assert "server_bind_error_message(" in source
assert "grader_launch_error_message(" in source

print(
    "Step 29.2.10 development-server guard regression test: PASS"
)
