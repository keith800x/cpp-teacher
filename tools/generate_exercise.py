#!/usr/bin/env python3

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from exercise_validator import (
    CPP_TEACHER_PATH,
    PROJECT_ROOT,
    load_json,
    print_report,
    validate_candidate_bundle,
)

from env_loader import load_project_env

load_project_env(
    PROJECT_ROOT
)

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

DEFAULT_MODEL = (
    os.environ.get("OPENAI_MODEL")
    or "gpt-5.6-terra"
)

TOPICS_PATH = PROJECT_ROOT / "catalog" / "topics.json"
DIFFICULTY_PROFILES_PATH = PROJECT_ROOT / "catalog" / "difficulty_profiles.json"
LIBRARY_PATH = PROJECT_ROOT / "catalog" / "exercise_library.json"
OPENAI_DRAFT_SCHEMA_PATH = (
    PROJECT_ROOT /
    "schemas" /
    "openai_generation_draft.schema.json"
)
GENERATED_CANDIDATE_DIRECTORY = (
    PROJECT_ROOT /
    "candidates" /
    "generated"
)

PROMPT_VERSION = 18

SUPPORTED_CHECK_GUIDANCE = {
    "non_const_reference_parameter": "fields: function + parameter",
    "const_reference_parameter": "fields: function + parameter",
    "non_const_reference_variable": "fields: variable + argument",
    "const_reference_variable": "fields: variable + argument",
    "std_move_initializer": "fields: variable + argument",
    "virtual_destructor": "field: class",
    "copy_constructor": "field: class",
    "move_constructor": "field: class; detects a user-declared T(T&&) move constructor; noexcept is a separate difficulty invariant",
}

TRACE_EVENT_GUIDANCE = """
Hidden runtime instrumentation MUST write every machine-readable TRACE line to
stderr. Prefer direct `std::cerr << "TRACE|..."` statements. Never emit TRACE
lines through std::cout. The existing C++ Teacher event format is:

TRACE|ENTER_SCOPE|subject|detail
TRACE|EXIT_SCOPE|subject|detail
TRACE|CREATE_VALUE|name|type=...|value=...
TRACE|BIND_ALIAS|alias|target=name|type=...|const=true|false
TRACE|WRITE_VALUE|name|via=alias_or_operation|value=...
TRACE|CREATE_OBJECT|object|type=DomainType|pointer=field_name
TRACE|ALLOCATE_RESOURCE|resource#N|value=...
TRACE|BIND_POINTER|object.field_|resource#N
TRACE|SET_NULL|object.field_|pointer cleared
TRACE|WRITE_VALUE|resource#N|via=active_operation|through=object.field_|value=...
TRACE|MOVE_RESOURCE|resource#N|source.field_ -> destination.field_|transfer=exclusive
TRACE|DESTROY_BEGIN|object|detail
TRACE|FREE_RESOURCE|resource#N|detail
TRACE|DESTROY_END|object|detail
TRACE|WARNING|subject|detail

Never put TRACE calls, ScopeMarker, TrackedResource, or grader-specific types
in learner-visible starter/reference code. Runtime instrumentation belongs only
in hidden tests or hidden support implementations.

Trace-integrity rules:
- every BIND_ALIAS target must EXACTLY match the subject of an existing
  CREATE_VALUE event for the caller-owned value;
- every WRITE_VALUE subject must EXACTLY match an existing CREATE_VALUE,
  CREATE_OBJECT, or ALLOCATE_RESOURCE subject;
- WRITE_VALUE for a CREATE_OBJECT is allowed only as direct stack-object state
  metadata: use `TRACE|WRITE_VALUE|object|value=field=value` with NO through=
  or via_pointer=. This represents a real mutation that already occurred in the
  hidden C++ and gives the visualizer an observable object-state update;
- WRITE_VALUE via=... must name either the active function scope or a live alias;
- for pointer-mediated heap mutation, add through=object.field_ (or
  via_pointer=object.field_) and ensure that pointer is currently bound to the
  WRITE_VALUE resource;
- every function call represented in the visualization must have its own
  ENTER_SCOPE / EXIT_SCOPE pair;
- ENTER_SCOPE / EXIT_SCOPE events must be correctly nested and balanced;
- every BIND_POINTER target must already exist as either a CREATE_OBJECT stack
  object or an ALLOCATE_RESOURCE resource;
- every MOVE_RESOURCE source/destination object must exist;
- every FREE_RESOURCE must reference a previously allocated resource;
- use distinct names for caller values and function parameters when they are
  different objects;
- for multi-concept exercises, NEVER use one all-or-nothing signature boolean
  to decide how several parameters are visualized;
- classify and instrument EACH learner-fixable parameter independently so a
  partially correct submission shows the concepts the learner already fixed;
- if parameter A has the correct reference form but parameter B is still wrong,
  the trace must show A as an alias and B as a separate value;
- the deterministic validator may synthesize one-fix partial solutions and will
  reject hidden harnesses that hide partial progress;
- when several parameters belong to the same function, derive their types
  independently from decltype(&function). A small hidden function-pointer trait
  specialization such as Trait<R (*)(P0, P1, P2)> can expose P0/P1/P2 separately;
  do NOT use std::is_same_v<decltype(&function), WholeExpectedSignature> as the
  switch that controls all parameter visualization;
- the SUBJECT of BIND_ALIAS must EXACTLY equal the learner-visible parameter
  identifier in that function declaration. If the parameter is named galleryName,
  emit BIND_ALIAS|galleryName|..., never BIND_ALIAS|labelGalleryName|... or another
  invented trace-only name. The active scope already disambiguates identical
  parameter names used by different functions;
- the same rule applies to a copied parameter represented by CREATE_VALUE: use the
  real parameter identifier rather than a trace-only renamed version whenever the
  parameter itself is what the visualization is representing;
- for HARD References exercises, the validator will synthesize every pair of
  learner-fixable reference parameters. Any two correct declarations must be
  visualized correctly at the same time in one execution;
- do not write instrumentation that only works for the untouched starter, one
  isolated fix, or the perfect reference solution. Parameter classification must
  compose when several fixes are present simultaneously;
- when a still-by-value parameter receives an object whose state may already have
  changed earlier in the scenario, derive the copied parameter's trace value from
  the CURRENT caller state. Do not hard-code an old initial-state string such as
  start=800 if an earlier corrected operation may have changed it to start=815.
""".strip()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def slug_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def load_topics() -> dict:
    data = load_json(TOPICS_PATH)

    return {
        item["id"]: item
        for item in data.get("topics", [])
        if isinstance(item, dict)
        and isinstance(item.get("id"), str)
    }


def published_exercises() -> list[dict]:
    library = load_json(LIBRARY_PATH)
    result = []

    for item in library.get("exercises", []):
        if not item.get("published", False):
            continue

        exercise_file = item.get("exercise_file")
        if not isinstance(exercise_file, str):
            continue

        path = PROJECT_ROOT / exercise_file
        if not path.exists():
            continue

        result.append({
            "registry": item,
            "exercise": load_json(path),
        })

    return result


def artifact_contents(exercise: dict) -> dict[str, str]:
    result: dict[str, str] = {}

    for field in [
        "hidden_test_file",
        "support_file",
        "analysis_support_file",
    ]:
        raw = exercise.get(field)

        if not isinstance(raw, str):
            continue

        path = PROJECT_ROOT / raw

        if not path.exists():
            continue

        try:
            result[raw] = path.read_text(encoding="utf-8")
        except OSError:
            pass

    return result


def exemplar_for_topic(topic: str) -> dict | None:
    for item in published_exercises():
        exercise = item["exercise"]

        if exercise.get("topic") == topic:
            return {
                "exercise": copy.deepcopy(exercise),
                "files": artifact_contents(exercise),
            }

    return None


def existing_scenarios(topic: str) -> list[str]:
    result = []

    for item in published_exercises():
        exercise = item["exercise"]

        if exercise.get("topic") != topic:
            continue

        result.append(
            f"{exercise.get('title', '')}: "
            f"{exercise.get('scenario', '')}"
        )

    return result


def build_exercise_id(topic: str) -> str:
    short_uuid = uuid4().hex[:6]

    topic_slug = re.sub(
        r"[^a-z0-9_]+",
        "_",
        topic.lower()
    ).strip("_")

    return (
        f"ai_{topic_slug}_"
        f"{slug_timestamp()}_"
        f"{short_uuid}"
    )


def strict_schema_for_request(
    exercise_id: str,
    topic: str,
    difficulty: str
) -> dict:
    schema = load_json(
        OPENAI_DRAFT_SCHEMA_PATH
    )

    # Keep the file human-readable as JSON Schema documentation, but only
    # send the strict subset needed by Structured Outputs.
    schema.pop("$schema", None)
    schema.pop("$id", None)
    schema.pop("title", None)
    schema.pop("description", None)

    exercise_properties = (
        schema["properties"]["exercise"]["properties"]
    )

    exercise_properties["exercise_schema_version"] = {
        "type": "integer",
        "enum": [1],
    }

    exercise_properties["id"] = {
        "type": "string",
        "enum": [exercise_id],
    }

    exercise_properties["topic"] = {
        "type": "string",
        "enum": [topic],
    }

    exercise_properties["difficulty"] = {
        "type": "string",
        "enum": [difficulty],
    }

    return schema


def difficulty_profile_text(
    topic_id: str,
    difficulty: str
) -> str:
    if not DIFFICULTY_PROFILES_PATH.exists():
        return (
            "No deterministic difficulty profile file is available."
        )

    try:
        data = load_json(
            DIFFICULTY_PROFILES_PATH
        )
    except (
        OSError,
        ValueError,
        json.JSONDecodeError
    ):
        return (
            "Difficulty profile file could not be read."
        )

    topics = data.get(
        "topics",
        {}
    )

    topic_profile = (
        topics.get(
            topic_id,
            {}
        )
        if isinstance(
            topics,
            dict
        )
        else {}
    )

    selected = (
        topic_profile.get(
            difficulty,
            {}
        )
        if isinstance(
            topic_profile,
            dict
        )
        else {}
    )

    if not isinstance(
        selected,
        dict
    ):
        return (
            "No deterministic difficulty profile applies."
        )

    return json.dumps(
        selected,
        indent=2
    )


def compact_exemplar(exemplar: dict | None) -> str:
    if exemplar is None:
        return "No published exemplar exists for this topic."

    return json.dumps(exemplar, indent=2)


def system_prompt() -> str:
    return """
You are the exercise-authoring component of C++ Teacher.

Create ONE C++ coding exercise candidate for an educational application.

The learner experience must feel like LeetCode or an engineering interview:
- use a concrete domain with named actors/entities from the code, not an abstract
  description like "caller-owned state" by itself;
- the problem_statement must name at least one actual function/class identifier
  from starter_code;
- prefer realistic surrounding code: a small class/struct with a method/caller,
  or at least two interacting functions, instead of one isolated toy function;
- ordinary C++ starter code;
- starter code compiles but contains a behavioral/design problem;
- no TODO/FIXME scaffolding that names the answer;
- do not tell the learner the exact syntax needed;
- learner-visible code must never mention tracing, graders, hidden tests,
  ScopeMarker, TrackedResource, MemoryTimeline, or instrumentation;
- do not add `friend` declarations, public inspection methods, or other API
  solely to give hidden tests private-state access when public behavior can
  prove the requirement.

Two goal fields serve different audiences:
- learning_objective is INTERNAL teacher metadata and may name the exact C++ concept;
- learner_goal is PUBLIC. It must describe only the observable engineering goal.
  It MUST NOT say writable reference, reference parameter, const reference,
  lvalue reference, std::move, move constructor, copy constructor, RAII,
  unique_ptr, shared_ptr, or weak_ptr.

Bad learner_goal:
  "Use a writable reference parameter to update caller-owned state."
Good learner_goal:
  "Make the cooling adjustment persist in the greenhouse controller after the helper returns."

The hidden reference solution and hidden artifacts may contain instrumentation.

Correctness rules:
- starter code MUST compile;
- starter code MUST fail hidden behavioral tests;
- reference solution MUST compile and pass the same tests;
- use declared AST concept checks when the current validator supports the concept;
- hidden runtime must generate enough TRACE events for a useful visualization;
- do not generate undefined behavior;
- do not depend on network, filesystem, subprocesses, threads, wall-clock time,
  environment variables, random behavior, external libraries, or user input;
- keep tests deterministic and small;
- do not use manual resource leaks as the intended lesson;
- no dangerous OS/process/file/network APIs.

A supplied domain type is allowed when the concept needs hidden instrumentation.
The learner should see a normal domain type, not an instrumentation type.

Return only the object required by the JSON schema.
""".strip()


def initial_user_prompt(
    *,
    exercise_id: str,
    topic: dict,
    difficulty: str,
    exemplar: dict | None,
    scenarios: list[str],
) -> str:
    guidance = (
        topic.get(
            "generation_guidance",
            {}
        ).get(
            difficulty,
            ""
        )
    )

    checks = "\n".join(
        f"- {name}: {fields}"
        for name, fields in SUPPORTED_CHECK_GUIDANCE.items()
    )

    scenario_text = (
        "\n".join(f"- {item}" for item in scenarios)
        if scenarios
        else "- none yet"
    )

    return f"""
Generate a new candidate with this exact request:

exercise_id: {exercise_id}
topic: {topic["id"]} ({topic.get("display_name", topic["id"])})
difficulty: {difficulty}

Topic description:
{topic.get("description", "")}

Difficulty guidance:
{guidance}

Deterministic difficulty-quality rubric for THIS requested level:
{difficulty_profile_text(topic["id"], difficulty)}

The difficulty field is not merely a label. The validator will reject an
exercise that does not provide enough measurable complexity for the requested
level, or that is substantially more complex than the requested lower level.
Do not change the requested difficulty to make validation easier; change the
exercise design.

Do NOT repeat these already-used scenarios:
{scenario_text}

Supported AST semantic check types:
{checks}

If no supported AST check fits, use an empty concept_checks array and prove the
concept with deterministic hidden behavioral/lifetime tests.

{TRACE_EVENT_GUIDANCE}

Public wording rules:
- learner_goal must be behavioral and must not reveal the target C++ mechanism;
- scenario and problem_statement must be concrete about who owns/uses the state/resource;
- problem_statement must name at least one function or class exactly as it appears in starter_code;
- avoid vague phrases such as "fix the reference" or "use the right parameter type";
- make the starter feel like a slice of a real program (for example a domain class
  whose method calls the buggy helper), not a naked one-function syntax drill.


Pointer-topic rules (topic=pointers only):
- teach RAW, non-owning pointers (`T*` / `const T*`), not unique_ptr/shared_ptr;
- learner-visible code must remain ordinary domain C++ and must never contain TRACE calls;
- NEVER add a learner-visible `friend` declaration, private-inspection helper,
  test hook, or artificial API solely so the hidden test can inspect a raw
  pointer member. Hidden tests must prove the relationship through ordinary
  public/domain behavior;
- for a read-only non-owning pointer to a mutable caller-owned stack object,
  PREFER this deterministic identity probe when the domain permits it:
    1. select/bind the existing object;
    2. verify the holder reads its current public value;
    3. mutate that SAME original caller-owned object directly;
    4. verify the holder now reads the updated value.
  This proves the holder observes the original object rather than a copied
  value without exposing private pointer state. When that same caller-owned
  CREATE_OBJECT object really changes, emit one DIRECT object-state event after
  the C++ mutation:
    TRACE|WRITE_VALUE|springMint|value=label_=Lemon mint
  Do NOT add through= or via_pointer= to this direct stack-object update; it is
  not a write-through decision and must not count as pointer-mediated mutation.
  If the pointee is intentionally immutable, use an existing domain-appropriate
  public query instead; do not add a test-only accessor or friendship declaration;
- concept_checks MUST be [] for Pointers until a genuinely pointer-specific AST
  semantic check is supported. Do NOT use const_reference_parameter,
  non_const_reference_parameter, or another References-style semantic check as
  a substitute for pointer behavior;
- do NOT invent trace event names. In particular, NEVER emit CREATE_POINTER,
  POINTER_DECISION, READ_POINTER, POINTER_READ, POINTER_STATE, or similar
  pointer-only events. They are not understood by the runtime timeline or
  deterministic Pointers difficulty validator;
- pointer evidence must be expressed only through the existing semantic trace
  vocabulary: CREATE_OBJECT, ALLOCATE_RESOURCE, BIND_POINTER, SET_NULL,
  WRITE_VALUE, and FREE_RESOURCE when a pointee lifetime actually ends.
  For the pointer-holder object, use CREATE_OBJECT with pointer=field_ so the
  raw-pointer subject is measurable as object.field_. For an ordinary stack
  pointee, use CREATE_OBJECT with its domain object name and value=field=value.
  Pointer-mediated mutation uses WRITE_VALUE with through=object.field_;
  caller-side mutation of a CREATE_OBJECT stack pointee uses direct
  WRITE_VALUE|object|value=field=value with no through=;
- pointer TRACE PAYLOAD SHAPES are strict, but a raw pointer may point to
  either a stack object or a heap resource.

  STACK POINTEE example:
    TRACE|CREATE_OBJECT|springMint|type=Plant|value=label_=Spring mint
    TRACE|CREATE_OBJECT|display|type=GardenDisplay|pointer=focused_
    TRACE|SET_NULL|display.focused_|pointer cleared
    TRACE|BIND_POINTER|display.focused_|springMint
    // only after a real caller-side mutation such as springMint.rename(...)
    TRACE|WRITE_VALUE|springMint|value=label_=Lemon mint

  HEAP/RESOURCE POINTEE example:
    TRACE|CREATE_OBJECT|console|type=RangerConsole|pointer=highlighted_
    TRACE|ALLOCATE_RESOURCE|resource#1|value=animal=river otter
    TRACE|BIND_POINTER|console.highlighted_|resource#1

  Never shorten `console.highlighted_` to `highlighted_`.
  For an ordinary local/stack C++ object, BIND_POINTER should target the exact
  CREATE_OBJECT subject such as `riverSighting`.
  Use resource#N only when the visualized pointee is represented by
  ALLOCATE_RESOURCE.
  Never write `holder=highlighted_`; the recognized CREATE_OBJECT key is
  exactly `pointer=highlighted_`;
- hidden runtime visualization should represent each raw pointer as a field
  subject `object.field_`. The BIND_POINTER target must have a matching
  CREATE_OBJECT or ALLOCATE_RESOURCE declaration;
- pointer-mediated WRITE_VALUE currently requires a resource-backed pointee:
  WRITE_VALUE|resource#N|value=...|through=object.field_. For a read-only
  pointer to a stack object, never invent pointer-mediated WRITE_VALUE. A
  direct WRITE_VALUE|stackObject|value=field=value is allowed only when the
  caller really mutates that same object and the event is needed to visualize
  the public-behavior identity proof;
- use stable literal resource ids such as resource#1/resource#2 in hidden trace
  strings so deterministic difficulty analysis can reason about identity and aliasing;
- when a pointer writes its pointee, emit WRITE_VALUE for that resource with
  through=object.field_ while the operation's ENTER_SCOPE is active;
- WRITE_VALUE provenance must describe a SEMANTICALLY TRACED name, not merely a
  C++ identifier. Use through=object.field_ only when that traced holder field
  actually performed the mutation. Use via=<name> only when <name> is itself a
  TRACE ENTER_SCOPE subject or BIND_ALIAS subject that the timeline knows. If a
  heap/resource pointee is mutated directly through an ordinary local raw pointer
  variable such as `replacement->rename(...)`, emit
  WRITE_VALUE|resource#N|value=... with NO via= field. Never emit
  via=replacement/primary/etc. just because that local C++ variable exists;
- when a pointer becomes null, emit SET_NULL|object.field_|...;
- hidden instrumentation must describe the pointer state that actually occurred:
  emit BIND_POINTER only when the learner-visible pointer really holds that
  pointee; emit SET_NULL when it is null. Conditional hidden branches are fine.
  Do not print a successful binding merely because the reference solution would
  have one;
- TRACE CHRONOLOGY IS SEMANTIC: once an operation such as watch/highlight/select
  establishes a pointer relationship and public behavior confirms it, emit the
  BIND_POINTER/SET_NULL branch immediately for that operation. If the same
  caller-owned stack pointee is mutated later to prove identity, the
  BIND_POINTER must appear BEFORE that later direct
  WRITE_VALUE|stackObject|value=field=value event. Never delay BIND_POINTER until
  after the mutation merely because the final assertion proves the relationship;
- emit the observed pointer-state TRACE event BEFORE an assertion that may abort
  the starter run. Determine the actual state from observable learner behavior,
  branch to BIND_POINTER or SET_NULL, then assert. This preserves a meaningful
  starter visualization as well as a reference visualization;
- for an Easy Pointers exercise, make the hidden source contain at least one
  supported BIND_POINTER subject so the deterministic difficulty analyzer can
  identify the pointer relationship. Optional SET_NULL or one write-through
  operation may supply the second Easy decision;
- Hard Pointers must bind at least two distinct pointer subjects on at least
  two pointer-holder objects to the same resource at some point (aliasing);
  the current memory model visualizes one raw-pointer field per holder object;
  show at least one write-through mutation, end at least one bound pointee
  lifetime with FREE_RESOURCE, and then make the affected pointer state explicit
  with SET_NULL or a safe reseat;
- a Hard starter may visualize a dangling pointer as "pointer still targets a
  dead resource", but hidden tests must NEVER dereference a null or dead pointer;
- Medium Pointers may use null handling, reseating, aliasing, or mutation, but
  should keep pointees alive throughout so lifetime/dangling reasoning remains Hard.


RAII/scope-topic rules (topic=raii_scope only):
- grade the learner-visible lifetime requirements, NOT one exact reference
  implementation or one complete audit-vector sequence;
- when several lexical-scope arrangements satisfy all stated before/after
  cleanup boundaries, hidden tests must accept all of them;
- do not compare the entire runtime audit vector to one exact expected vector;
- assert required partial ordering: create before required use, remain alive
  through that use, destroy after final use, and destroy before the named later
  phase;
- preserve explicitly required operation order, but do not accidentally require
  unrelated resource acquisition to happen earlier than necessary;
- treat acquire-as-late-as-needed / release-as-early-as-allowed as valid when
  the learner-facing requirements permit it;
- keep learner-visible code ordinary automatic-storage C++ with lexical scopes.
  Never require explicit destructor calls or new/delete as the intended fix.

Move-semantics-topic rules (topic=move_semantics only):
- learner-visible starter_code and reference_solution may use ordinary standard
  headers such as <utility>, but must never include support/, analysis_support/,
  tests/, candidates/, or any other quoted project-local header;
- hidden support artifacts are concatenated around learner code by the grader;
- when support types are needed for AST concept checks, provide an
  analysis_support artifact containing declarations/definitions sufficient for
  semantic analysis rather than exposing the support header to the learner;
- Easy should stay at no more than two recognized advanced ownership invariants;
- Medium must contain 3-4 recognized advanced ownership invariants. Prefer a
  natural combination such as noexcept move construction + moved-from empty
  state + stable resource identity, optionally with one additional invariant;
- resource identity must be OBSERVABLE, not merely named in expected_concepts:
  public requirements and hidden tests should verify that a stable token/id
  from each moved resource is preserved in the destination while the source is
  cleared;
- Hard requires the complete five-invariant ownership set from the deterministic
  difficulty profile. Do not label a two-invariant exercise Medium.

Artifact rules:
- exactly one hidden_test artifact is required;
- use an empty string for support_file when support is unnecessary;
- use an empty string for analysis_support_file when analysis support is unnecessary;
- when either optional file field is non-empty, include exactly one matching artifact;
- hidden artifacts are concatenated around learner code by the existing grader,
  so do not use project-local quoted #include directives;
- use only ordinary standard-library headers.

The following published exercise is an ARCHITECTURAL exemplar for this topic.
Create a different scenario, different identifiers, and a genuinely new problem.
Do not clone its story.

EXEMPLAR:
{compact_exemplar(exemplar)}
""".strip()


def deterministic_repair_directives(
    report: dict
) -> list[str]:
    directives: list[str] = []

    for check in report.get(
        "checks",
        []
    ):
        if not isinstance(
            check,
            dict
        ):
            continue

        if check.get(
            "status"
        ) not in {
            "fail",
            "warn",
        }:
            continue

        check_id = str(
            check.get(
                "id",
                ""
            )
        )

        message = str(
            check.get(
                "message",
                ""
            )
        )

        prefix = (
            "runtime.partial_probe."
        )

        if check_id.startswith(
            prefix
        ):
            remainder = check_id[
                len(prefix):
            ]

            if "." in remainder:
                function_name, parameter_name = (
                    remainder.rsplit(
                        ".",
                        1
                    )
                )

                directives.append(
                    (
                        f"For partial probe {function_name}::{parameter_name}: "
                        f"while ENTER_SCOPE '{function_name}' is active, "
                        f"the hidden trace must use the exact parameter identifier "
                        f"as its alias subject: "
                        f"TRACE|BIND_ALIAS|{parameter_name}|target=<caller-value>|..."
                    )
                )

                directives.append(
                    (
                        f"Do not rename parameter '{parameter_name}' to a "
                        f"trace-only alias such as label{parameter_name[:1].upper() + parameter_name[1:]}, "
                        f"request{parameter_name[:1].upper() + parameter_name[1:]}, "
                        "or another invented name. Function scope is the disambiguator."
                    )
                )

        combined_prefix = (
            "runtime.combined_probe."
        )

        if check_id.startswith(
            combined_prefix
        ):
            remainder = check_id[
                len(
                    combined_prefix
                ):
            ]

            pair_names = [
                item
                for item in remainder.split(
                    "__"
                )
                if item
            ]

            directives.append(
                (
                    "A Hard References pairwise probe failed for: " +
                    " + ".join(
                        pair_names
                    ) +
                    ". The hidden harness must classify those "
                    "parameters independently and show BOTH corrected "
                    "reference bindings in the SAME execution. Do not "
                    "special-case only starter, one-fix, or final-solution "
                    "signatures."
                )
            )

            directives.append(
                (
                    "For any still-by-value parameter executed after an "
                    "earlier corrected mutation, build its traced copy from "
                    "the current caller state instead of a hard-coded initial "
                    "state. Combined probes deliberately change earlier state "
                    "before later helpers execute."
                )
            )

        if (
            "WRITE_VALUE" in message and
            "through='" in message
        ):
            directives.append(
                (
                    "For pointer-mediated WRITE_VALUE, through=object.field_ "
                    "must name a currently bound raw-pointer field whose "
                    "BIND_POINTER target is the same heap resource as the "
                    "WRITE_VALUE subject."
                )
            )

        if (
            "SET_NULL" in message and
            "did not clear pointer" in message
        ):
            directives.append(
                (
                    "Emit SET_NULL only for an existing pointer-holder "
                    "object.field_ and make sure it occurs after the pointer "
                    "has been represented by BIND_POINTER. The resulting "
                    "timeline field must have no points_to target."
                )
            )

        if (
            check_id == "safety.generated_cpp" and
            "quoted project/system include" in message
        ):
            directives.append(
                (
                    "Remove every quoted #include from learner-visible "
                    "starter_code/reference_solution. Hidden support is "
                    "already concatenated by the grader. If semantic analysis "
                    "needs support type declarations, use analysis_support "
                    "instead of a learner-visible project include."
                )
            )

        if check_id == "artifacts.trace_stream_contract":
            directives.append(
                (
                    "Emit every hidden runtime TRACE event to stderr. Use "
                    "std::cerr << \"TRACE|...\" (or an existing stderr "
                    "helper). Never emit TRACE events through std::cout."
                )
            )

        if check_id == "artifacts.raii_grading_equivalence":
            directives.append(
                (
                    "For topic=raii_scope, do not compare a complete audit "
                    "vector against one exact reference sequence. Rewrite the "
                    "hidden test to assert only required lifetime partial "
                    "ordering. Equivalent lexical-scope arrangements that "
                    "satisfy all stated constraints must pass."
                )
            )

        if check_id == "artifacts.pointer_trace_contract":
            directives.append(
                (
                    "For topic=pointers, remove invented pointer-only TRACE "
                    "events. Do not emit CREATE_POINTER, POINTER_DECISION, "
                    "READ_POINTER, POINTER_READ, POINTER_STATE, or similar "
                    "events. Use CREATE_OBJECT(pointer=field_), "
                    "ALLOCATE_RESOURCE, BIND_POINTER, SET_NULL, "
                    "WRITE_VALUE with through=object.field_, and "
                    "FREE_RESOURCE only when the pointee lifetime ends."
                )
            )

        if check_id == "artifacts.pointer_write_value_provenance":
            directives.append(
                (
                    "Repair WRITE_VALUE provenance without changing learner code. "
                    "For topic=pointers, via=<name> may only name a traced "
                    "ENTER_SCOPE subject or BIND_ALIAS subject. If the actual C++ "
                    "mutation uses an ordinary local raw pointer variable (for "
                    "example replacement->rename(...)), omit via= entirely. Use "
                    "through=object.field_ only when that traced holder pointer "
                    "field actually performed the mutation. Do not invent a scope "
                    "or alias merely to satisfy provenance validation."
                )
            )

        if check_id == "artifacts.pointer_trace_chronology":
            directives.append(
                (
                    "Repair pointer event order without changing the learner "
                    "exercise. After the learner-visible operation that "
                    "establishes the pointer relationship, evaluate enough "
                    "ordinary public behavior to determine the real state, "
                    "then emit the BIND_POINTER/SET_NULL branch immediately "
                    "and before any later caller-side mutation of that stack "
                    "pointee. If the original object changes later, emit its "
                    "direct WRITE_VALUE only after that real mutation. "
                    "Required teaching order: null/holder -> bind -> later "
                    "pointee WRITE_VALUE while the binding remains active."
                )
            )

        if check_id == "artifacts.pointer_trace_shape":
            directives.append(
                (
                    "Repair every pointer TRACE payload to the exact runtime "
                    "shape reported by the validator. Holder creation must be "
                    "CREATE_OBJECT|object|type=Type|pointer=field_. SET_NULL "
                    "and BIND_POINTER subjects must be fully qualified "
                    "object.field_. A BIND_POINTER target may be either a "
                    "stack object with a matching CREATE_OBJECT declaration "
                    "or a resource#N id with a matching ALLOCATE_RESOURCE "
                    "declaration. Example stack bind: "
                    "CREATE_OBJECT|riverSighting|type=Sighting|"
                    "value=animal=river otter; CREATE_OBJECT|console|"
                    "type=RangerConsole|pointer=highlighted_; "
                    "BIND_POINTER|console.highlighted_|riverSighting. "
                    "Example resource bind: ALLOCATE_RESOURCE|resource#1|"
                    "value=animal=river otter; "
                    "BIND_POINTER|console.highlighted_|resource#1. "
                    "Do not use holder=field_ or a bare pointer field name. "
                    "For read-only pointer exercises, do not invent a "
                    "WRITE_VALUE merely to create difficulty evidence. If a "
                    "public-behavior identity probe mutates a CREATE_OBJECT "
                    "stack pointee, keep the C++ mutation/assertion but omit "
                    "TRACE|WRITE_VALUE for that stack object."
                )
            )

            directives.append(
                (
                    "Emit the pointer-state TRACE event before any assertion "
                    "that can abort the starter run. Infer the actual state "
                    "from observable learner behavior, branch to BIND_POINTER "
                    "or SET_NULL, then assert."
                )
            )

        if check_id == "pedagogy.pointer_no_test_hooks":
            directives.append(
                (
                    "For topic=pointers, remove learner-visible friend "
                    "declarations and any helper/API that exists only to let "
                    "hidden tests inspect the private pointer. Keep the domain "
                    "exercise natural. Rewrite the hidden test to prove pointer "
                    "identity through public behavior. When the selected "
                    "caller-owned object has a mutable observable field, prefer "
                    "this probe: select the object, verify the current value, "
                    "mutate that SAME original object directly, then verify the "
                    "holder observes the updated value. Do not add another "
                    "test-only accessor to replace the friend declaration."
                )
            )

        if check_id == "schema.pointer_concept_checks":
            directives.append(
                (
                    "For topic=pointers, set concept_checks to an empty array. "
                    "Do not use const_reference_parameter or another "
                    "References-style AST check as a proxy for pointer "
                    "semantics. Hidden behavioral/runtime tests are "
                    "authoritative for Pointers until a pointer-specific AST "
                    "check exists."
                )
            )

        if check_id == "difficulty.quality":
            directives.append(
                (
                    "The requested difficulty is immutable. Adjust the EXERCISE "
                    "complexity to satisfy the deterministic difficulty rubric "
                    "instead of changing the difficulty field. Validator detail: " +
                    message
                )
            )

            if "Medium Move Semantics" in message:
                directives.append(
                    (
                        "For Medium Move Semantics, make 3-4 ownership "
                        "invariants genuinely observable. A stable resource "
                        "token/id preserved by the destination and cleared "
                        "from the source counts as resource identity only "
                        "when the public requirements and hidden behavior "
                        "actually verify it. Do not pad expected_concepts "
                        "without adding behavioral evidence."
                    )
                )

            if "Pointers" in message:
                directives.append(
                    (
                        "Pointers difficulty evidence counts supported "
                        "BIND_POINTER subjects plus SET_NULL, pointer-mediated "
                        "WRITE_VALUE, aliasing/reseating, and real "
                        "FREE_RESOURCE lifetime boundaries. Invented events "
                        "such as POINTER_DECISION and READ_POINTER do not "
                        "count. Make hidden instrumentation use the supported "
                        "trace contract."
                    )
                )

        if (
            "WRITE_VALUE uses via=" in
            message and
            "active scope" in
            message
        ):
            directives.append(
                (
                    "For every WRITE_VALUE via=..., the via value must exactly name "
                    "a currently active ENTER_SCOPE subject or a currently live alias. "
                    "Emit the WRITE_VALUE before EXIT_SCOPE for that operation."
                )
            )

        if (
            "did not produce a meaningful timeline" in
            message or
            "Timeline must contain at least two snapshots" in
            message
        ):
            directives.append(
                (
                    "Do not rely on TRACE|SNAPSHOT alone. Emit supported semantic "
                    "events such as ENTER_SCOPE, CREATE_VALUE/BIND_ALIAS, WRITE_VALUE "
                    "when appropriate, and EXIT_SCOPE so the memory timeline builder "
                    "can create multiple real snapshots."
                )
            )

    # Always reinforce the naming contract during repair, because a technically
    # valid final/reference trace can still hide bad partial-attempt semantics.
    directives.append(
        (
            "For every reference-parameter concept_check, BIND_ALIAS subject must "
            "exactly equal concept_check.parameter and must be emitted while the "
            "matching concept_check.function scope is active."
        )
    )

    result: list[str] = []

    for directive in directives:
        if directive not in result:
            result.append(
                directive
            )

    return result


POINTER_TRACE_REPAIR_CHECK_IDS = {
    "artifacts.trace_stream_contract",
    "artifacts.pointer_trace_contract",
    "artifacts.pointer_trace_shape",
    "artifacts.pointer_trace_chronology",
    "artifacts.pointer_write_value_provenance",
}


def is_pointer_trace_only_repair(
    topic_id: str,
    report: dict
) -> bool:
    if topic_id != "pointers":
        return False

    issues = [
        check
        for check in report.get(
            "checks",
            []
        )
        if isinstance(
            check,
            dict
        ) and
        check.get(
            "status"
        ) in {
            "fail",
            "warn",
        }
    ]

    if not issues:
        return False

    issue_ids = {
        str(
            check.get(
                "id",
                ""
            )
        )
        for check in issues
    }

    has_trace_failure = bool(
        issue_ids &
        POINTER_TRACE_REPAIR_CHECK_IDS
    )

    only_trace_related_categories = all(
        str(
            check.get(
                "category",
                ""
            )
        ) in {
            "artifacts",
            "difficulty",
            "visualization",
        }
        for check in issues
    )

    return (
        has_trace_failure and
        only_trace_related_categories
    )


def preserve_pointer_trace_repair_core(
    *,
    previous_candidate: dict,
    repaired_candidate: dict,
    report: dict
) -> dict:
    previous_exercise = previous_candidate.get(
        "exercise",
        {}
    )

    topic_id = str(
        previous_exercise.get(
            "topic",
            ""
        )
    )

    if not is_pointer_trace_only_repair(
        topic_id,
        report
    ):
        return repaired_candidate

    preserved = copy.deepcopy(
        previous_candidate
    )

    preserved[
        "generation_metadata"
    ] = copy.deepcopy(
        repaired_candidate.get(
            "generation_metadata",
            {}
        )
    )

    preserved_exercise = preserved.get(
        "exercise",
        {}
    )

    preserved_exercise[
        "concept_checks"
    ] = normalize_concept_checks(
        preserved_exercise,
        topic_id
    )

    previous_hidden_path = str(
        preserved_exercise.get(
            "hidden_test_file",
            ""
        )
    )

    repaired_exercise = repaired_candidate.get(
        "exercise",
        {}
    )

    repaired_hidden_path = str(
        repaired_exercise.get(
            "hidden_test_file",
            ""
        )
    )

    repaired_files = repaired_candidate.get(
        "files",
        {}
    )

    if (
        previous_hidden_path and
        repaired_hidden_path and
        isinstance(
            repaired_files,
            dict
        ) and
        repaired_hidden_path in repaired_files
    ):
        preserved.setdefault(
            "files",
            {}
        )[
            previous_hidden_path
        ] = repaired_files[
            repaired_hidden_path
        ]

    return preserved


def repair_user_prompt(
    *,
    exercise_id: str,
    topic: dict,
    difficulty: str,
    candidate: dict,
    report: dict,
    exemplar: dict | None,
) -> str:
    failures = [
        check
        for check in report.get("checks", [])
        if check.get("status") in {"fail", "warn"}
    ]

    directives = deterministic_repair_directives(
        report
    )

    trace_only_pointer_repair = (
        is_pointer_trace_only_repair(
            topic["id"],
            report
        )
    )

    repair_scope = (
        """
POINTER TRACE-ONLY REPAIR:
The learner exercise is IMMUTABLE for this repair. Copy the exercise object
exactly as supplied, including scenario, problem_statement, constraints,
starter_code, reference_solution, hints, explanation, learner_goal, and
difficulty complexity. Repair only the hidden_test artifact instrumentation.
The response schema still requires a complete draft, but deterministic
normalization will discard any attempted learner-exercise rewrite.
"""
        if trace_only_pointer_repair
        else ""
    )

    return f"""
Repair the COMPLETE C++ Teacher exercise draft below.

{repair_scope}

Keep these immutable:
exercise_id: {exercise_id}
topic: {topic["id"]}
difficulty: {difficulty}

The deterministic validator rejected or warned about this candidate.
Fix every reported issue while preserving a realistic learner-facing problem.

VALIDATOR ISSUES:
{json.dumps(failures, indent=2)}

DETERMINISTIC REPAIR DIRECTIVES:
{json.dumps(directives, indent=2)}

CURRENT CANDIDATE BUNDLE:
{json.dumps(candidate, indent=2)}

ARCHITECTURAL EXEMPLAR:
{compact_exemplar(exemplar)}

Return the complete replacement draft, not a patch.
Starter must compile but fail hidden tests; reference must pass; visualization
must remain meaningful; learner code must remain ordinary C++. Keep learner_goal
behavioral and answer-safe, and make problem_statement name a real code identifier.

When repairing hidden traces, do not preserve an old trace-only parameter alias
name merely because the final reference solution happens to validate. Every
partial-probe parameter must be represented under its exact C++ parameter name.
""".strip()


def api_key() -> str:
    value = os.environ.get(
        "OPENAI_API_KEY",
        ""
    ).strip()

    if not value:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. "
            'Run: export OPENAI_API_KEY="your_api_key_here"'
        )

    return value


def openai_response(
    *,
    model: str,
    schema: dict,
    system_text: str,
    user_text: str,
    timeout_seconds: int,
) -> tuple[dict, dict]:
    body = {
        "model": model,
        "input": [
            {
                "role": "system",
                "content": system_text,
            },
            {
                "role": "user",
                "content": user_text,
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "cpp_teacher_exercise_draft",
                "strict": True,
                "schema": schema,
            },
        },
        "max_output_tokens": 16000,
    }

    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": "Bearer " + api_key(),
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout_seconds
        ) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        detail = error.read().decode(
            "utf-8",
            errors="replace"
        )

        raise RuntimeError(
            f"OpenAI API HTTP {error.code}: "
            f"{detail[:4000]}"
        ) from error
    except urllib.error.URLError as error:
        raise RuntimeError(
            f"Could not reach the OpenAI API: {error}"
        ) from error

    payload = json.loads(raw)

    if payload.get("status") == "incomplete":
        raise RuntimeError(
            "OpenAI response was incomplete: " +
            json.dumps(
                payload.get("incomplete_details", {})
            )
        )

    output_text = None

    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue

        for content in item.get("content", []):
            content_type = content.get("type")

            if content_type == "refusal":
                raise RuntimeError(
                    "Model refused generation: " +
                    str(content.get("refusal", ""))
                )

            if content_type == "output_text":
                output_text = content.get("text")
                break

        if output_text is not None:
            break

    if not isinstance(output_text, str):
        raise RuntimeError(
            "OpenAI response contained no output_text."
        )

    return json.loads(output_text), payload


def normalize_concept_checks(
    exercise: dict,
    topic: str
) -> list[dict]:
    if topic == "pointers":
        return []

    normalized_checks: list[dict] = []

    for raw_check in exercise.get(
        "concept_checks",
        []
    ):
        if not isinstance(
            raw_check,
            dict
        ):
            continue

        normalized_checks.append({
            key: value
            for key, value in raw_check.items()
            if (
                key == "type"
                or (
                    isinstance(
                        value,
                        str
                    )
                    and value.strip()
                )
            )
        })

    return normalized_checks


def normalize_trace_transport(
    content: str
) -> str:
    if not isinstance(content, str):
        return content

    statements = content.split(";")
    normalized: list[str] = []

    for statement in statements:
        if "TRACE|" in statement:
            statement = statement.replace(
                "std::cout",
                "std::cerr"
            )

        normalized.append(statement)

    return ";".join(normalized)


POINTER_NORMALIZE_ENTER_SCOPE_PATTERN = re.compile(
    r"TRACE\|ENTER_SCOPE\|(?P<subject>[^|\\\n\"]+)"
)

POINTER_NORMALIZE_BIND_ALIAS_PATTERN = re.compile(
    r"TRACE\|BIND_ALIAS\|(?P<subject>[^|\\\n\"]+)"
)

POINTER_NORMALIZE_VIA_PATTERN = re.compile(
    r"\|via=(?P<name>[^|\\\n\"]+)"
)


def normalize_pointer_write_value_provenance(
    content: str,
    topic: str
) -> str:
    if topic != "pointers":
        return content

    known_via_names = {
        match.group("subject").strip()
        for match in POINTER_NORMALIZE_ENTER_SCOPE_PATTERN.finditer(content)
    }
    known_via_names.update(
        match.group("subject").strip()
        for match in POINTER_NORMALIZE_BIND_ALIAS_PATTERN.finditer(content)
    )

    normalized_lines: list[str] = []
    for line in content.splitlines(keepends=True):
        if "TRACE|WRITE_VALUE|" not in line or "|via=" not in line:
            normalized_lines.append(line)
            continue

        def replace_via(match: re.Match[str]) -> str:
            via_name = match.group("name").strip()
            return match.group(0) if via_name in known_via_names else ""

        normalized_lines.append(
            POINTER_NORMALIZE_VIA_PATTERN.sub(replace_via, line)
        )

    return "".join(normalized_lines)


def normalize_pointer_stack_write_traces(
    content: str,
    topic: str
) -> str:
    # Step 30.6: direct WRITE_VALUE events for CREATE_OBJECT stack pointees
    # are valid visualization metadata when they describe a real caller-side
    # mutation. Shape validation decides whether the payload is usable.
    return content


def normalize_hidden_runtime_artifact(
    content: str,
    topic: str
) -> str:
    content = normalize_trace_transport(content)
    content = normalize_pointer_stack_write_traces(
        content,
        topic
    )
    content = normalize_pointer_write_value_provenance(
        content,
        topic
    )
    return content


GENERATED_QUOTED_INCLUDE_LINE_PATTERN = re.compile(
    r'(?m)^[ \t]*#[ \t]*include[ \t]*"[^"]+"[ \t]*(?:\r?\n|$)'
)


def strip_generated_quoted_includes(
    source: str
) -> str:
    """
    Generated learner code is intentionally self-contained apart from allowed
    standard-library angle includes. Hidden support is assembled by the grader,
    so a model-emitted quoted project include is always authoring leakage.
    """
    if not isinstance(
        source,
        str
    ):
        return source

    return GENERATED_QUOTED_INCLUDE_LINE_PATTERN.sub(
        "",
        source,
    )


def normalize_draft(
    *,
    draft: dict,
    exercise_id: str,
    topic: str,
    difficulty: str,
    model: str,
    response_id: str | None,
    generation_attempt: int,
) -> dict:
    exercise = copy.deepcopy(
        draft.get("exercise", {})
    )

    if not isinstance(exercise, dict):
        raise RuntimeError(
            "Draft exercise is not an object."
        )

    exercise["exercise_schema_version"] = 1
    exercise["id"] = exercise_id
    exercise["topic"] = topic
    exercise["difficulty"] = difficulty

    for learner_source_field in [
        "starter_code",
        "reference_solution",
    ]:
        if isinstance(
            exercise.get(
                learner_source_field
            ),
            str,
        ):
            exercise[
                learner_source_field
            ] = strip_generated_quoted_includes(
                exercise[
                    learner_source_field
                ]
            )

    exercise["concept_checks"] = (
        normalize_concept_checks(
            exercise,
            topic
        )
    )

    artifacts = draft.get("artifacts", [])

    if not isinstance(artifacts, list):
        raise RuntimeError(
            "Draft artifacts must be an array."
        )

    by_kind = {
        "hidden_test": [],
        "support": [],
        "analysis_support": [],
    }

    for artifact in artifacts:
        if not isinstance(artifact, dict):
            continue

        kind = artifact.get("kind")

        if kind in by_kind:
            by_kind[kind].append(artifact)

    if len(by_kind["hidden_test"]) != 1:
        raise RuntimeError(
            "Draft must contain exactly one hidden_test artifact."
        )

    if len(by_kind["support"]) > 1:
        raise RuntimeError(
            "Draft may contain at most one support artifact."
        )

    if len(by_kind["analysis_support"]) > 1:
        raise RuntimeError(
            "Draft may contain at most one analysis_support artifact."
        )

    files: dict[str, str] = {}

    hidden_test_path = (
        f"tests/{exercise_id}_tests.cpp"
    )
    files[hidden_test_path] = (
        normalize_hidden_runtime_artifact(
            by_kind["hidden_test"][0].get(
                "content",
                ""
            ),
            topic
        )
    )
    exercise["hidden_test_file"] = hidden_test_path

    if by_kind["support"]:
        support_path = (
            f"support/{exercise_id}_support.hpp"
        )
        files[support_path] = (
            by_kind["support"][0].get(
                "content",
                ""
            )
        )
        exercise["support_file"] = support_path
    else:
        exercise.pop("support_file", None)

    if by_kind["analysis_support"]:
        analysis_path = (
            "analysis_support/" +
            f"{exercise_id}_analysis_stub.hpp"
        )
        files[analysis_path] = (
            by_kind["analysis_support"][0].get(
                "content",
                ""
            )
        )
        exercise["analysis_support_file"] = analysis_path
    elif (
        topic == "move_semantics" and
        by_kind["support"] and
        exercise.get(
            "concept_checks"
        )
    ):
        # A support artifact may define the domain resource types needed to
        # parse the learner's move constructor. Reuse it only for hidden AST
        # analysis rather than exposing a project-local #include to learners.
        analysis_path = (
            "analysis_support/" +
            f"{exercise_id}_analysis_stub.hpp"
        )
        files[analysis_path] = (
            by_kind["support"][0].get(
                "content",
                ""
            )
        )
        exercise["analysis_support_file"] = analysis_path
    else:
        exercise.pop("analysis_support_file", None)

    return {
        "candidate_schema_version": 1,
        "generation_metadata": {
            "generator": "openai_responses_step28",
            "prompt_version": PROMPT_VERSION,
            "model": model,
            "requested_topic": topic,
            "requested_difficulty": difficulty,
            "generated_at": utc_now(),
            "generation_attempt": generation_attempt,
            "openai_response_id": response_id,
        },
        "exercise": exercise,
        "files": files,
    }


def save_json(path: Path, data: Any):
    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        json.dumps(
            data,
            indent=2
        ) + "\n",
        encoding="utf-8"
    )


def publish_candidate(
    candidate_path: Path
) -> int:
    completed = subprocess.run(
        [
            sys.executable,
            str(
                PROJECT_ROOT /
                "tools" /
                "publish_candidate.py"
            ),
            str(candidate_path),
        ],
        cwd=str(PROJECT_ROOT),
        check=False,
    )

    return completed.returncode


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate one C++ Teacher exercise with the "
            "OpenAI Responses API and validate it."
        )
    )

    parser.add_argument(
        "--topic",
        help=(
            "Topic id from catalog/topics.json. Required for a new candidate; "
            "in repair mode it is read from the existing candidate."
        ),
    )

    parser.add_argument(
        "--difficulty",
        choices=[
            "easy",
            "medium",
            "hard",
        ],
        help=(
            "Difficulty for a new candidate. In repair mode it is read from "
            "the existing candidate."
        ),
    )

    parser.add_argument(
        "--repair-candidate",
        help=(
            "Resume AI repair of an existing candidates/generated/<id>.json "
            "instead of creating a new candidate id."
        ),
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model id. Default: {DEFAULT_MODEL}",
    )

    parser.add_argument(
        "--max-repairs",
        type=int,
        default=2,
        help=(
            "Maximum validator-driven repair calls after "
            "initial generation. Default: 2."
        ),
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=180,
        help="OpenAI HTTP timeout in seconds.",
    )

    parser.add_argument(
        "--publish",
        action="store_true",
        help=(
            "Publish only if the final candidate passes "
            "the deterministic validator."
        ),
    )

    parser.add_argument(
        "--dry-prompt",
        action="store_true",
        help=(
            "Print generation context without an API call."
        ),
    )

    args = parser.parse_args()

    if args.max_repairs < 0:
        parser.error(
            "--max-repairs must be >= 0"
        )

    topics = load_topics()

    repair_mode = bool(
        args.repair_candidate
    )

    if repair_mode:
        repair_candidate_id = str(
            args.repair_candidate
        ).strip()

        if not re.fullmatch(
            r"[a-z0-9][a-z0-9_]*",
            repair_candidate_id
        ):
            print(
                "Invalid --repair-candidate id.",
                file=sys.stderr
            )
            return 2

        candidate_path = (
            GENERATED_CANDIDATE_DIRECTORY /
            f"{repair_candidate_id}.json"
        )

        if not candidate_path.exists():
            print(
                (
                    "Repair candidate does not exist: " +
                    str(
                        candidate_path.relative_to(
                            PROJECT_ROOT
                        )
                    )
                ),
                file=sys.stderr
            )
            return 2

        try:
            existing_candidate = load_json(
                candidate_path
            )
        except (
            OSError,
            ValueError,
            json.JSONDecodeError
        ) as error:
            print(
                f"Could not read repair candidate: {error}",
                file=sys.stderr
            )
            return 2

        existing_exercise = (
            existing_candidate.get(
                "exercise",
                {}
            )
        )

        if not isinstance(
            existing_exercise,
            dict
        ):
            print(
                "Repair candidate has no exercise object.",
                file=sys.stderr
            )
            return 2

        requested_topic = str(
            existing_exercise.get(
                "topic",
                ""
            )
        )

        requested_difficulty = str(
            existing_exercise.get(
                "difficulty",
                ""
            )
        )

        if (
            args.topic and
            args.topic != requested_topic
        ):
            print(
                "--topic does not match the existing candidate.",
                file=sys.stderr
            )
            return 2

        if (
            args.difficulty and
            args.difficulty != requested_difficulty
        ):
            print(
                "--difficulty does not match the existing candidate.",
                file=sys.stderr
            )
            return 2

        args.topic = requested_topic
        args.difficulty = requested_difficulty
        exercise_id = repair_candidate_id
    else:
        if not args.topic:
            parser.error(
                "--topic is required unless --repair-candidate is used."
            )

        if not args.difficulty:
            parser.error(
                "--difficulty is required unless --repair-candidate is used."
            )

        exercise_id = build_exercise_id(
            args.topic
        )

    topic = topics.get(
        args.topic
    )

    if topic is None:
        print(
            "Unknown topic. Available: " +
            ", ".join(sorted(topics.keys())),
            file=sys.stderr
        )
        return 2

    if not CPP_TEACHER_PATH.exists():
        print(
            "build/cpp_teacher is missing. Build the project "
            "before AI generation.",
            file=sys.stderr
        )
        return 2

    exemplar = exemplar_for_topic(
        args.topic
    )
    scenarios = existing_scenarios(
        args.topic
    )

    schema = strict_schema_for_request(
        exercise_id,
        args.topic,
        args.difficulty
    )

    first_prompt = (
        None
        if repair_mode
        else initial_user_prompt(
            exercise_id=exercise_id,
            topic=topic,
            difficulty=args.difficulty,
            exemplar=exemplar,
            scenarios=scenarios,
        )
    )

    print(
        (
            "\nC++ Teacher AI candidate repair"
            if repair_mode
            else "\nC++ Teacher AI exercise generation"
        )
    )
    print(
        "Topic: "
        f"{topic.get('display_name', topic['id'])} "
        f"({topic['id']})"
    )
    print(f"Difficulty: {args.difficulty}")
    print(f"Model: {args.model}")
    print(f"Candidate id: {exercise_id}")

    if args.dry_prompt:
        if repair_mode:
            print(
                "--dry-prompt is only supported for new generation.",
                file=sys.stderr
            )
            return 2

        print("\n--- SYSTEM PROMPT ---\n")
        print(system_prompt())
        print("\n--- USER PROMPT ---\n")
        print(first_prompt)
        return 0

    try:
        api_key()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        return 2

    GENERATED_CANDIDATE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True
    )

    candidate_path = (
        GENERATED_CANDIDATE_DIRECTORY /
        f"{exercise_id}.json"
    )
    validation_path = (
        GENERATED_CANDIDATE_DIRECTORY /
        f"{exercise_id}.validation.json"
    )

    if repair_mode:
        candidate = existing_candidate

        try:
            report = validate_candidate_bundle(
                candidate_path,
                structural_only=False,
            )
        except Exception as error:
            print(
                f"Validator crashed before repair: {error}",
                file=sys.stderr
            )
            return 2

        save_json(
            validation_path,
            report.to_dict()
        )

        if report.valid:
            print(
                "\nCandidate is already VALID; no AI repair is needed."
            )
            return 0

        previous_attempt = int(
            candidate.get(
                "generation_metadata",
                {}
            ).get(
                "generation_attempt",
                1
            )
            or 1
        )

        total_calls = args.max_repairs

        if total_calls <= 0:
            print(
                "--max-repairs must be at least 1 in repair mode.",
                file=sys.stderr
            )
            return 2
    else:
        candidate = None
        report = None
        previous_attempt = 0
        total_calls = 1 + args.max_repairs

    for call_index in range(total_calls):
        generation_attempt = (
            previous_attempt +
            call_index +
            1
        )

        if repair_mode:
            print(
                "\nOpenAI repair call "
                f"{call_index + 1}/{total_calls} "
                f"(generation attempt {generation_attempt})..."
            )

            prompt = repair_user_prompt(
                exercise_id=exercise_id,
                topic=topic,
                difficulty=args.difficulty,
                candidate=candidate,
                report=report.to_dict(),
                exemplar=exemplar,
            )
        else:
            print(
                "\nOpenAI generation call "
                f"{call_index + 1}/{total_calls}..."
            )

            if call_index == 0:
                prompt = first_prompt
            else:
                prompt = repair_user_prompt(
                    exercise_id=exercise_id,
                    topic=topic,
                    difficulty=args.difficulty,
                    candidate=candidate,
                    report=report.to_dict(),
                    exemplar=exemplar,
                )

        try:
            draft, raw_response = openai_response(
                model=args.model,
                schema=schema,
                system_text=system_prompt(),
                user_text=prompt,
                timeout_seconds=args.timeout,
            )

            previous_candidate = candidate
            previous_report = report

            repaired_candidate = normalize_draft(
                draft=draft,
                exercise_id=exercise_id,
                topic=args.topic,
                difficulty=args.difficulty,
                model=args.model,
                response_id=raw_response.get("id"),
                generation_attempt=generation_attempt,
            )

            if (
                previous_candidate is not None and
                previous_report is not None
            ):
                candidate = (
                    preserve_pointer_trace_repair_core(
                        previous_candidate=previous_candidate,
                        repaired_candidate=repaired_candidate,
                        report=previous_report.to_dict(),
                    )
                )
            else:
                candidate = repaired_candidate
        except (
            RuntimeError,
            OSError,
            json.JSONDecodeError
        ) as error:
            print(
                f"Generation failed: {error}",
                file=sys.stderr
            )
            return 2

        save_json(
            candidate_path,
            candidate
        )

        print(
            "Candidate saved: " +
            str(
                candidate_path.relative_to(
                    PROJECT_ROOT
                )
            )
        )

        try:
            report = validate_candidate_bundle(
                candidate_path,
                structural_only=False,
            )
        except Exception as error:
            print(
                f"Validator crashed: {error}",
                file=sys.stderr
            )
            return 2

        save_json(
            validation_path,
            report.to_dict()
        )
        print_report(report)

        if report.valid:
            print("\nAI CANDIDATE VALIDATED.")

            if args.publish:
                print(
                    "\nPublishing validated candidate..."
                )
                return publish_candidate(
                    candidate_path
                )

            print(
                "\nCandidate was NOT published automatically."
            )
            print(
                "Inspect it, then publish with:"
            )
            print(
                "python3 tools/publish_candidate.py " +
                str(
                    candidate_path.relative_to(
                        PROJECT_ROOT
                    )
                )
            )
            return 0

        if call_index < total_calls - 1:
            print(
                "\nCandidate rejected. Sending deterministic "
                "validator feedback to the model for another repair."
            )

    print(
        "\nAI candidate remains INVALID after "
        f"{total_calls} generation call(s).",
        file=sys.stderr
    )
    print(
        "Rejected candidate: " +
        str(
            candidate_path.relative_to(
                PROJECT_ROOT
            )
        ),
        file=sys.stderr
    )
    print(
        "Validation report: " +
        str(
            validation_path.relative_to(
                PROJECT_ROOT
            )
        ),
        file=sys.stderr
    )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
