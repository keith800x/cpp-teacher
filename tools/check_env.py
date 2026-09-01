#!/usr/bin/env python3

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(
        PROJECT_ROOT /
        "tools"
    )
)

from env_loader import load_project_env

load_project_env(
    PROJECT_ROOT
)

api_key = os.environ.get(
    "OPENAI_API_KEY",
    ""
).strip()

model = (
    os.environ.get(
        "OPENAI_MODEL",
        ""
    ).strip()
    or
    "gpt-5.6-terra"
)

if not api_key:
    print(
        "OPENAI_API_KEY is not configured."
    )
    print(
        "Copy .env.example to .env and set your real key."
    )
    raise SystemExit(1)

print(
    "OPENAI_API_KEY is configured."
)
print(
    f"OPENAI_MODEL={model}"
)
