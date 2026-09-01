#!/usr/bin/env python3

from __future__ import annotations

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

from generate_exercise import (
    deterministic_repair_directives,
)

report = {
    "checks": [
        {
            "id": (
                "runtime.partial_probe."
                "formatVentilationLabel.galleryName"
            ),
            "status": "fail",
            "message": (
                "no BIND_ALIAS for parameter 'galleryName' "
                "was recorded while scope "
                "'formatVentilationLabel' was active"
            ),
        },
        {
            "id": (
                "runtime.partial_probe."
                "formatVentilationLabel.technicianName"
            ),
            "status": "fail",
            "message": (
                "no BIND_ALIAS for parameter 'technicianName' "
                "was recorded while scope "
                "'formatVentilationLabel' was active"
            ),
        },
    ]
}

directives = deterministic_repair_directives(
    report
)

joined = "\n".join(
    directives
)

assert (
    "BIND_ALIAS|galleryName|" in
    joined
)

assert (
    "BIND_ALIAS|technicianName|" in
    joined
)

assert (
    "labelGalleryName" in
    joined
)

assert (
    "concept_check.parameter" in
    joined
)

print(
    "Step 29.2 repair-directive test: PASS"
)
