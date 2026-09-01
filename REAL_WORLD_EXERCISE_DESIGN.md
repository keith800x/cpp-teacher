# C++ Teacher exercise design rules

## What the learner sees

A learner should receive:

1. A realistic scenario.
2. A concrete problem or incorrect behavior.
3. Starter code that contains that problem.
4. Requirements phrased in terms of desired behavior.
5. Compiler / semantic / test feedback after attempting a solution.

They should NOT receive:

- TODO comments that effectively reveal the syntax.
- The reference solution.
- Hidden tests.
- The validator implementation.
- A problem whose starter code already passes.

## Example: References

Scenario:
A warehouse dashboard has a live stock count.

Bug:
inventoryEditor and dashboardView are copies, so changes do not stay synchronized.

The learner decides how to make both names observe the same storage.

## Example: RAII

Scenario:
A video-processing job needs scratch buffers only while processing one frame.

Bug:
the scratch buffers are created in the outer job scope and therefore live too long.

The learner must reorganize object lifetimes using lexical scope.

## Hidden-solution architecture

The browser no longer fetches raw exercises/*.json.

Instead it requests:

  GET /api/exercises/<exercise_id>

The server returns only public fields:

- id
- topic
- title
- difficulty
- type
- learning_objective
- instructions
- starter_code
- expected_concepts
- hints

Private fields remain server-side:

- reference_solution
- hidden_test_file
- support_file
- analysis_support_file
- concept_checks
- expected_output
- validator details

The development server also blocks direct HTTP access to:

- /exercises/
- /tests/
- /support/
- /analysis_support/
- /src/
- /include/
- /build/

This is still a local development application, not a production security boundary.

## AI generation rule

AI-generated exercises should follow the same pattern:

realistic scenario
    ->
broken/incomplete starter code
    ->
hidden reference solution
    ->
hidden deterministic validators
    ->
automatic validation
    ->
publish only if valid
