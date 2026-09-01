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

from exercise_validator import (
    validate_timeline_integrity,
)


def frame(
    step,
    event_type,
    subject,
    detail,
    scopes,
    values=None,
    aliases=None,
):
    return {
        "step": step,
        "cause": {
            "type": event_type,
            "subject": subject,
            "detail": detail,
        },
        "active_scopes": scopes,
        "stack": [],
        "stack_values": values or [],
        "aliases": aliases or [],
        "heap": [],
    }


good = {
    "schema_version": 4,
    "exercise_id": "good",
    "timeline": [
        frame(
            1,
            "ENTER_SCOPE",
            "caller",
            "",
            ["caller"],
        ),
        frame(
            2,
            "CREATE_VALUE",
            "dashboardWaitingPatients",
            "type=int|value=4",
            ["caller"],
            values=[
                {
                    "name": "dashboardWaitingPatients",
                    "type": "int",
                    "scope": "caller",
                    "value": "4",
                    "alive": True,
                }
            ],
        ),
        frame(
            3,
            "ENTER_SCOPE",
            "admitNextPatient",
            "",
            [
                "caller",
                "admitNextPatient",
            ],
            values=[
                {
                    "name": "dashboardWaitingPatients",
                    "type": "int",
                    "scope": "caller",
                    "value": "4",
                    "alive": True,
                }
            ],
        ),
        frame(
            4,
            "BIND_ALIAS",
            "waitingPatients",
            (
                "target=dashboardWaitingPatients|"
                "type=int&|const=false"
            ),
            [
                "caller",
                "admitNextPatient",
            ],
            values=[
                {
                    "name": "dashboardWaitingPatients",
                    "type": "int",
                    "scope": "caller",
                    "value": "4",
                    "alive": True,
                }
            ],
            aliases=[
                {
                    "name": "waitingPatients",
                    "type": "int&",
                    "scope": "admitNextPatient",
                    "target": "dashboardWaitingPatients",
                    "const": False,
                    "alive": True,
                }
            ],
        ),
        frame(
            5,
            "WRITE_VALUE",
            "dashboardWaitingPatients",
            "via=waitingPatients|value=3",
            [
                "caller",
                "admitNextPatient",
            ],
            values=[
                {
                    "name": "dashboardWaitingPatients",
                    "type": "int",
                    "scope": "caller",
                    "value": "3",
                    "alive": True,
                }
            ],
            aliases=[
                {
                    "name": "waitingPatients",
                    "type": "int&",
                    "scope": "admitNextPatient",
                    "target": "dashboardWaitingPatients",
                    "const": False,
                    "alive": True,
                }
            ],
        ),
        frame(
            6,
            "EXIT_SCOPE",
            "admitNextPatient",
            "",
            ["caller"],
            values=[
                {
                    "name": "dashboardWaitingPatients",
                    "type": "int",
                    "scope": "caller",
                    "value": "3",
                    "alive": True,
                }
            ],
            aliases=[
                {
                    "name": "waitingPatients",
                    "type": "int&",
                    "scope": "admitNextPatient",
                    "target": "dashboardWaitingPatients",
                    "const": False,
                    "alive": False,
                }
            ],
        ),
        frame(
            7,
            "EXIT_SCOPE",
            "caller",
            "",
            [],
            values=[
                {
                    "name": "dashboardWaitingPatients",
                    "type": "int",
                    "scope": "caller",
                    "value": "3",
                    "alive": False,
                }
            ],
            aliases=[
                {
                    "name": "waitingPatients",
                    "type": "int&",
                    "scope": "admitNextPatient",
                    "target": "dashboardWaitingPatients",
                    "const": False,
                    "alive": False,
                }
            ],
        ),
    ],
}

bad = {
    "schema_version": 4,
    "exercise_id": "bad",
    "timeline": [
        frame(
            1,
            "ENTER_SCOPE",
            "clinicDashboard",
            "",
            ["clinicDashboard"],
        ),
        frame(
            2,
            "CREATE_VALUE",
            "waitingPatients",
            "type=int|value=4",
            ["clinicDashboard"],
            values=[
                {
                    "name": "waitingPatients",
                    "type": "int",
                    "scope": "clinicDashboard",
                    "value": "4",
                    "alive": True,
                }
            ],
        ),
        frame(
            3,
            "ENTER_SCOPE",
            "admitNextPatient",
            "",
            [
                "clinicDashboard",
                "admitNextPatient",
            ],
            values=[
                {
                    "name": "waitingPatients",
                    "type": "int",
                    "scope": "clinicDashboard",
                    "value": "4",
                    "alive": True,
                }
            ],
        ),
        frame(
            4,
            "BIND_ALIAS",
            "waitingPatients",
            (
                "target=clinicDashboard.waitingPatients|"
                "type=int&|const=false"
            ),
            [
                "clinicDashboard",
                "admitNextPatient",
            ],
            values=[
                {
                    "name": "waitingPatients",
                    "type": "int",
                    "scope": "clinicDashboard",
                    "value": "4",
                    "alive": True,
                }
            ],
            aliases=[
                {
                    "name": "waitingPatients",
                    "type": "int&",
                    "scope": "admitNextPatient",
                    "target": "clinicDashboard.waitingPatients",
                    "const": False,
                    "alive": True,
                }
            ],
        ),
        frame(
            5,
            "WRITE_VALUE",
            "clinicDashboard.waitingPatients",
            "via=admitNextPatient|value=3",
            [
                "clinicDashboard",
                "admitNextPatient",
            ],
            values=[
                {
                    "name": "waitingPatients",
                    "type": "int",
                    "scope": "clinicDashboard",
                    "value": "4",
                    "alive": True,
                }
            ],
            aliases=[
                {
                    "name": "waitingPatients",
                    "type": "int&",
                    "scope": "admitNextPatient",
                    "target": "clinicDashboard.waitingPatients",
                    "const": False,
                    "alive": True,
                }
            ],
        ),
    ],
}

good_issues = validate_timeline_integrity(
    good
)

assert not good_issues, good_issues

bad_issues = validate_timeline_integrity(
    bad
)

assert any(
    "targets unknown stack value" in issue
    for issue in bad_issues
), bad_issues

assert any(
    "WRITE_VALUE targets unknown stack value" in issue
    for issue in bad_issues
), bad_issues

assert any(
    "unclosed active scopes" in issue
    for issue in bad_issues
), bad_issues

print(
    "Step 28.1 timeline-integrity test: PASS"
)

print(
    "Bad fixture correctly rejected for:"
)

for issue in bad_issues:
    print(
        " -",
        issue
    )
