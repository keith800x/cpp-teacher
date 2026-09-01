# LeetCode-style exercise rules

## Learner-visible starter code

Starter code must look like ordinary C++ from an interview problem or real
codebase.

Allowed:
- standard-library types
- ordinary functions/classes
- realistic domain types supplied by the environment
- broken logic/signatures/lifetimes the learner must diagnose

Not allowed:
- trace* calls
- ScopeMarker
- instrumentation macros
- grader callbacks
- hidden-test helpers
- comments that directly reveal the target syntax
- reference solutions

## Instrumentation boundary

Instrumentation belongs behind the exercise boundary:

student source
  -> hidden support / hidden test harness
  -> compiler + AST
  -> runtime observations
  -> semantic trace
  -> visualization

A supplied domain type may be instrumented internally, but its public learner
surface should remain a normal domain API (for example FrameBuffer), similar to
LeetCode supplying ListNode or TreeNode.

## Starter quality

A starter should normally:
- compile
- exhibit the stated bug or inefficiency
- fail at least one hidden behavioral or semantic requirement
- contain enough real context to understand the problem
- not contain TODO text that names the exact language feature required

## AI-generated exercises

AI generation must follow these same rules. Generated candidates are not
published until deterministic validation proves:
- starter exhibits intended problem
- reference solution passes
- hidden tests differentiate starter from solution
- AST checks prove the intended C++ concept
- learner-visible source contains no instrumentation hooks
