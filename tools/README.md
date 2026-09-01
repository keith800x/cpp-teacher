# Step 27 authoring tools

## Validate all published exercises

```bash
python3 tools/exercise_validator.py --all-published
```

## Validate an AI-style candidate bundle

```bash
python3 tools/exercise_validator.py   candidates/example_references_candidate.json
```

## Machine-readable report

```bash
python3 tools/exercise_validator.py   candidates/example_references_candidate.json   --json
```

## Schema/pedagogy checks without a built C++ grader

```bash
python3 tools/exercise_validator.py   candidates/example_references_candidate.json   --structural-only
```

## Publish only after full validation

```bash
python3 tools/publish_candidate.py   candidates/example_references_candidate.json   --dry-run
```

Remove `--dry-run` only when you intentionally want to add the candidate to the
exercise library.

The publisher runs the validator first and refuses invalid candidates.


## Step 28: OpenAI exercise generation

Set the API key in your WSL shell:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

The generator intentionally reads the key from the environment. Never put the
key in browser JavaScript or exercise JSON.

Preview the generation prompt without making an API request:

```bash
python3 tools/generate_exercise.py \
  --topic references \
  --difficulty easy \
  --dry-prompt
```

Generate and run the full deterministic validator:

```bash
python3 tools/generate_exercise.py \
  --topic references \
  --difficulty easy
```

Default model:

```text
gpt-5.6-terra
```

Override it with either:

```bash
export OPENAI_MODEL="gpt-5.6-sol"
```

or:

```bash
python3 tools/generate_exercise.py \
  --topic references \
  --difficulty easy \
  --model gpt-5.6-sol
```

The generator does not publish by default. Validated candidates are saved under:

```text
candidates/generated/
```

Publish only after inspection:

```bash
python3 tools/publish_candidate.py \
  candidates/generated/<candidate>.json
```

You can explicitly request publish-after-validation with `--publish`, but that
flag cannot bypass the Step 27 validator.


## Step 29: browser authoring workflow

The command-line tools remain available, but normal local development no longer
requires them for generation/publishing.

Start the application:

```bash
python3 dev_server.py
```

`dev_server.py` now:
- loads `.env`;
- checks whether `build/cpp_teacher` is missing/stale;
- runs CMake configure/build automatically when needed;
- retries once with a clean `build/` if the cached build fails;
- starts the local web server only after the grader is ready.

Force a clean rebuild only when desired:

```bash
python3 dev_server.py --rebuild
```

In the Exercise Library choose **AI Authoring** to:
- generate + validate;
- inspect candidate starter/reference/hidden artifacts;
- revalidate;
- publish valid candidates;
- unpublish exercises.

The browser calls local `/api/authoring/*` endpoints. The OpenAI key stays on the
server and is never returned to the browser.

## Step 29.1: partial-solution visualization probes

Multi-concept reference exercises are now validated against one-fix partial
solutions. The validator starts from `starter_code`, applies exactly one
reference-parameter correction from `reference_solution`, grades that partial
attempt, and checks that the timeline visibly represents the corrected
parameter even while the remaining concepts are still wrong.

Example checks:

```text
runtime.partial_probe.dispatchUnits.availableUnits
runtime.partial_probe.dispatchUnits.activityLog
runtime.partial_probe.dispatchUnits.incidentId
runtime.partial_probe.briefingLength.briefing
```

A writable-reference probe must show:

```text
BIND_ALIAS <parameter> -> <caller value>
WRITE_VALUE <caller value>
```

while the function scope is active.

A const-reference probe must show the corresponding `BIND_ALIAS` with
`const=true`.

This rejects hidden harnesses that use one whole-signature boolean to render all
parameters as either aliases or copies.

Offline test:

```bash
python3 tools/test_partial_reference_probes.py
```


## Step 29.2: resume repair of an invalid candidate

The UI now exposes `Repair with AI`.

CLI equivalent:

```bash
python3 tools/generate_exercise.py \
  --repair-candidate ai_references_YYYYMMDD_HHMMSS_xxxxxx \
  --max-repairs 2
```

This keeps the same candidate id and sends the current deterministic validation
failures back to the model for additional repair calls.

Partial-probe trace aliases must use the exact learner-visible parameter name.


## Step 29.2.5: difficulty-quality validation

Run:

```bash
python3 tools/test_difficulty_quality.py
```

The validator now emits:

```text
difficulty/difficulty.quality
```

for References, RAII/Scope, and Move Semantics.

The rubric is stored in:

```text
catalog/difficulty_profiles.json
```

AI generation receives the same rubric and is instructed to change exercise
complexity rather than relabel an invalid candidate.


## Step 29.2.6: Hard References pairwise probes

For `topic=references` and `difficulty=hard`, the validator now synthesizes all
two-fix combinations after the existing one-fix probes.

For four reference decisions this adds six checks:

```text
runtime.combined_probe.functionA.parameter__functionB.parameter
```

Run the offline test:

```bash
python3 tools/test_combined_reference_probes.py
```
