# Duplication - detail

## Decide: merge or keep separate?
Ask: **"If one copy changes for a business reason, must the other change too?"**
- **Yes** → it is duplicated *knowledge*. Merge into one source now (even at 2 copies). Divergent copies of
  shared knowledge are a known bug source (inconsistent clone changes; Juergens et al., Wagner et al.).
- **No / not sure** → coincidental similarity. Keep separate. Revisit at the third occurrence (Rule of Three).

## Extend an existing function vs. write a new one
Extend (add a parameter) when:
- the new case satisfies the function's existing contract and name, and
- the parameter is *data* (a value, a key, a callback), not a *mode switch*.

Write a separate function (optionally sharing a smaller core) when:
- merging needs a boolean/enum flag that forks most of the body,
- callers would pass flags they don't understand,
- the shared function's name would become vaguer to cover both.

## Undoing a wrong abstraction (Metz)
Signs: a shared function with growing params + `if` branches per caller. Fix:
1. Inline it back into each caller.
2. In each caller, delete the branches that caller never takes.
3. Re-extract only what is truly common now.
This is a behaviour-preserving refactor - tests must stay green.

## Repeated work: allowed only when cheaper
Repeating a computation/IO is fine when caching or sharing it would cost more (memory, invalidation risk,
coupling, reader effort) than recomputing. Otherwise hoist it, compute once, or cache with a stated
invalidation rule (adding a cache = flag, SKILL §6).

## Before writing new code
Grep for the verb/noun you're about to implement (`slugify`, `retry`, `parse_date`, `chunk`). Prefer the
standard library and existing project utilities over a new helper.
