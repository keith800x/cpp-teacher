#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(
    0,
    str(PROJECT_ROOT / "tools")
)

from exercise_validator import (
    parameter_declaration_span,
    synthesize_single_reference_probe,
    timeline_has_reference_binding,
)

STARTER = r'''#include <string>

void dispatchUnits(
    int availableUnits,
    std::string activityLog,
    const std::string incidentId,
    int requestedUnits)
{
    availableUnits -= requestedUnits;
    activityLog += incidentId;
}
'''

REFERENCE = r'''#include <string>

void dispatchUnits(
    int& availableUnits,
    std::string& activityLog,
    const std::string& incidentId,
    int requestedUnits)
{
    availableUnits -= requestedUnits;
    activityLog += incidentId;
}
'''

CHECKS = [
    {
        "type": "non_const_reference_parameter",
        "function": "dispatchUnits",
        "parameter": "availableUnits",
    },
    {
        "type": "non_const_reference_parameter",
        "function": "dispatchUnits",
        "parameter": "activityLog",
    },
    {
        "type": "const_reference_parameter",
        "function": "dispatchUnits",
        "parameter": "incidentId",
    },
]

expected_declarations = {
    "availableUnits": "int& availableUnits",
    "activityLog": "std::string& activityLog",
    "incidentId": "const std::string& incidentId",
}

for check in CHECKS:
    probe, detail = synthesize_single_reference_probe(
        STARTER,
        REFERENCE,
        check,
    )

    assert probe is not None, detail

    span = parameter_declaration_span(
        probe,
        check["function"],
        check["parameter"],
    )

    assert span is not None
    assert (
        span[2].strip()
        == expected_declarations[
            check["parameter"]
        ]
    )

    # Only one declaration should have changed from the starter.
    other_checks = [
        other
        for other in CHECKS
        if other["parameter"] != check["parameter"]
    ]

    for other in other_checks:
        other_probe_span = parameter_declaration_span(
            probe,
            other["function"],
            other["parameter"],
        )
        other_starter_span = parameter_declaration_span(
            STARTER,
            other["function"],
            other["parameter"],
        )

        assert other_probe_span is not None
        assert other_starter_span is not None
        assert (
            other_probe_span[2].strip()
            == other_starter_span[2].strip()
        )


def frame(
    step: int,
    event_type: str,
    subject: str,
    detail: str,
    scopes: list[str],
) -> dict:
    return {
        "step": step,
        "cause": {
            "type": event_type,
            "subject": subject,
            "detail": detail,
        },
        "active_scopes": scopes,
        "stack": [],
        "stack_values": [],
        "aliases": [],
        "heap": [],
    }


bad_all_or_nothing = {
    "timeline": [
        frame(
            1,
            "ENTER_SCOPE",
            "dispatchUnits",
            "function call",
            ["dispatchUnits"],
        ),
        frame(
            2,
            "CREATE_VALUE",
            "availableUnitsParameter",
            "type=int|value=9",
            ["dispatchUnits"],
        ),
        frame(
            3,
            "EXIT_SCOPE",
            "dispatchUnits",
            "function returned",
            [],
        ),
    ]
}

represented, detail = timeline_has_reference_binding(
    bad_all_or_nothing,
    function_name="dispatchUnits",
    parameter_name="availableUnits",
    expected_const=False,
)

assert not represented
assert "no BIND_ALIAS" in detail

alias_but_missing_write = {
    "timeline": [
        frame(
            1,
            "ENTER_SCOPE",
            "dispatchUnits",
            "function call",
            ["dispatchUnits"],
        ),
        frame(
            2,
            "BIND_ALIAS",
            "availableUnits",
            "target=consoleUnits|type=int&|const=false",
            ["dispatchUnits"],
        ),
        frame(
            3,
            "EXIT_SCOPE",
            "dispatchUnits",
            "function returned",
            [],
        ),
    ]
}

represented, detail = timeline_has_reference_binding(
    alias_but_missing_write,
    function_name="dispatchUnits",
    parameter_name="availableUnits",
    expected_const=False,
)

assert not represented
assert "never showed" in detail

correct_partial = {
    "timeline": [
        frame(
            1,
            "ENTER_SCOPE",
            "dispatchUnits",
            "function call",
            ["dispatchUnits"],
        ),
        frame(
            2,
            "BIND_ALIAS",
            "availableUnits",
            "target=consoleUnits|type=int&|const=false",
            ["dispatchUnits"],
        ),
        frame(
            3,
            "WRITE_VALUE",
            "consoleUnits",
            "via=availableUnits|value=5",
            ["dispatchUnits"],
        ),
        frame(
            4,
            "EXIT_SCOPE",
            "dispatchUnits",
            "function returned",
            [],
        ),
    ]
}

represented, detail = timeline_has_reference_binding(
    correct_partial,
    function_name="dispatchUnits",
    parameter_name="availableUnits",
    expected_const=False,
)

assert represented, detail

correct_const_partial = {
    "timeline": [
        frame(
            1,
            "ENTER_SCOPE",
            "dispatchUnits",
            "function call",
            ["dispatchUnits"],
        ),
        frame(
            2,
            "BIND_ALIAS",
            "incidentId",
            "target=incident|type=const std::string&|const=true",
            ["dispatchUnits"],
        ),
        frame(
            3,
            "EXIT_SCOPE",
            "dispatchUnits",
            "function returned",
            [],
        ),
    ]
}

represented, detail = timeline_has_reference_binding(
    correct_const_partial,
    function_name="dispatchUnits",
    parameter_name="incidentId",
    expected_const=True,
)

assert represented, detail

print("Step 29.1 partial-reference probe test: PASS")
print("- one parameter can be fixed without changing the others")
print("- all-or-nothing visualization is rejected")
print("- writable references must show the caller-value write")
print("- const-reference partial progress is recognized")
