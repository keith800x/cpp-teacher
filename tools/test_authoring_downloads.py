#!/usr/bin/env python3

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

authoring = (
    PROJECT_ROOT /
    "visualizer" /
    "authoring.js"
).read_text(
    encoding="utf-8"
)

styles = (
    PROJECT_ROOT /
    "visualizer" /
    "styles.css"
).read_text(
    encoding="utf-8"
)

required_javascript = [
    "function authoringDownloadBlob(",
    "function buildValidationDownloadDocument(",
    "function validationReportAsText(",
    "async function downloadValidationReport(",
    "async function downloadCandidateBundle(",
    'data-authoring-action="download-report-txt"',
    'data-authoring-action="download-report-json"',
    'data-authoring-action="download-candidate-json"',
    '`validation-${safeId}.txt`',
    '`validation-${safeId}.json`',
    '`candidate-${safeId}.json`',
    '"text/plain;charset=utf-8"',
    '"application/json;charset=utf-8"',
    "payload.candidate",
    "payload.validation",
]

for fragment in required_javascript:
    assert fragment in authoring, (
        "Missing authoring download regression fragment: "
        + fragment
    )

assert (
    "URL.createObjectURL" in authoring
), "Downloads must remain browser-side."

assert (
    "URL.revokeObjectURL" in authoring
), "Blob URLs must be released after download."

assert (
    ".authoring-download-actions" in styles
), "Download action styling is missing."

assert (
    ".authoring-download-label" in styles
), "Download label styling is missing."

print(
    "Step 29.2.8 authoring-download regression test: PASS"
)
