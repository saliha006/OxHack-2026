---
name: no-slop
description: Code-quality pass that removes AI-generated bloat and fixes it in place - useless comments, verbose or cryptic names, duplicated and near-duplicated logic, dead code and debug leftovers, swallowed errors, over-defensive checks, shallow wrappers, and poor Big-O on hot paths. Run it after EVERY code change (yours or another agent's), and always before every commit, push, PR, or merge. Also use when asked to "clean up", "de-slop", "tidy", "review for quality", "make this less AI-looking", "simplify", or "check efficiency/complexity" of a diff or files.
---

# no-slop

Review the current diff (or the files named) and **fix every issue directly** - do not just list them.
Exception: anything that is a design decision (see §6) is flagged, not silently changed.

The bar: code that reads like a strong engineer on *this* codebase wrote it - least code, least duplication,
least error surface, right complexity class - and not sterile, over-engineered, or padded.

## 0. Inputs from the project

- `{{EXPECTED_SCALE}}` - the load the code must serve (e.g. "10k users, 1M rows, 50 req/s"). Take it from the
  project's CLAUDE.md/AGENTS.md. **If absent or blank:** design for 10x today's real load, and treat every
  user-, row-, or event-shaped collection as unbounded (never O(n²) on it). Say in the report that you assumed this.
- The project's conventions (naming style, error style, logging, lint config). Match them over anything here.
- The test command. If none is documented, find it (package.json, pyproject, Makefile, CI config) before editing.

## 1. Safety rule (overrides everything below)

**Never break or worsen working code.** Every edit keeps behaviour identical or strictly better
(faster, smaller, clearer). Prove it: run the tests before (baseline) and after. If a change's safety can't be
shown - no test covers it and you can't add one cheaply - leave the code alone and flag it.
A cleanup must not change public interfaces, outputs, error types, or log/metric names other code relies on.

## 2. Scope - the change plus its wiring

Scan the diff, then follow the wiring one hop out: **callers, callees, and importers** of anything touched.
Read them; fix slop there too if it is connected to the change. Do not wander the whole repo.

## 3. Procedure (in order)

1. **Baseline.** Run the tests; note failures that already existed so you don't "fix" or blame them.
2. **Map the wiring** (§2). List touched symbols and their call sites (grep/LSP).
3. **Run the tools the project already has** - linter, type checker, dead-code and clone finders
   (see [references/tooling.md](references/tooling.md)). Fix what they report in scope. Don't add new tools
   to the project without flagging (§6).
4. **Walk the checklist** (§4) over the scope. Apply fixes smallest-first.
5. **Complexity pass** (§5) on every hot-path function in scope.
6. **Re-run tests + linters.** All baseline-green tests stay green. If you added behaviour-preserving
   refactors with no coverage, add a characterisation test first.
7. **Report** (§7).

## 4. Checklist

### A. Comments and docs
- Delete comments that restate the code (`# loop over users`, `// increment i`), narrate the change
  (`// now using the new API`), or label sections of a short function. LLM code is measurably over-commented.
- Keep or add comments that say **why**: a constraint, a non-obvious invariant, a workaround with its cause,
  a units/precision assumption, a link to the spec/ticket. Example: `# vendor API rejects >100 ids per call`.
- Docstrings: one line for non-obvious internals; full docs only on public/exported interfaces, where they
  document the contract (inputs, outputs, errors), not the implementation. Delete docstrings that just
  repeat the function name.
- Comments must be true. Fix or delete any comment the code contradicts.

### B. Names - see [references/naming.md](references/naming.md)
- A name states the **concept**, not the type or the mechanics: `retry_delay`, not `delay_value_int`.
- **Length scales with scope.** One letter is fine for a 3-line loop index or a math formula (`i`, `x`, `k`);
  module-level and public names get full words. Cryptic abbreviations (`usrCnt`, `tmp2`) and vague nouns
  (`data`, `result`, `info`, `obj`, `handler2`, `manager`) are out wherever they live beyond a few lines.
- No AI-verbose names: drop words the context already supplies. `UserService.get_user_by_id_from_database`
  → `UserService.get`/`by_id`; `calculate_the_total_sum_of_values` → `total`/`sum_values`.
- Functions: verb or verb phrase for actions (`send`, `parse_header`); noun/adjective for pure queries
  and properties (`total`, `is_expired`). Booleans read as predicates (`is_`, `has_`, `can_`).
- One concept, one word across the codebase (don't mix `fetch`/`get`/`load` for the same operation).

### C. Duplication - see [references/duplication.md](references/duplication.md)
- **Same knowledge, two places → one source.** If two pieces would always have to change together
  (a rule, a formula, a constant, a schema), merge them. A fix applied to only one copy is a latent bug.
- **Coincidental similarity → leave it.** Code that looks alike but changes for different reasons stays separate.
- **Rule of three for *new* abstractions.** Two similar call sites: tolerate. Third: extract.
- **Search before you write.** Before adding a helper, grep for an existing one; extend or call it.
- **Extend vs. new function:** parameterise an existing function only when the new case fits its existing
  contract. If merging needs a boolean/mode flag that forks most of the body, or a growing `if kind == ...`
  ladder, it is the *wrong* abstraction - keep separate functions sharing a smaller common core.
- Repeated work is acceptable only when it is cheaper (in runtime *and* in reader effort) than the alternative.

### D. Dead and leftover code
- Remove unused imports, variables, parameters, functions, branches, feature flags that are always on/off,
  commented-out code, and unreachable code. (Version control remembers it.)
- Remove debug leftovers: `print`/`console.log`/`dbg!`, hardcoded test values, temporary sleeps.
- Placeholders in committed code (`TODO` with no ticket, `...` bodies, `raise NotImplementedError` on a
  reachable path, `# implement later`) - implement or remove. Legit structural no-ops (abstract methods,
  protocol stubs, intentional `pass`) stay.
- Never hardcode secrets, tokens, or absolute local paths.

### E. Error handling
- No swallowed errors: `except: pass`, `catch (e) {}`, or log-and-continue on a failure that should stop the
  operation. Generic catch-all and empty handlers are among the anti-patterns most tied to defects.
- Catch the narrowest exception type you can actually handle; let the rest propagate.
- Handle an error only where you can recover, retry, degrade, or add context. Otherwise don't catch it.
- Don't replace a crash with a silent default that hides corrupt state.

### F. Defensive code
- **Validate at trust boundaries** (user input, network, files, env, third-party APIs) - fully.
- **Trust internal invariants** past that boundary. Remove re-checks the type system or caller already
  guarantees (null-checks on non-nullable values, `isinstance` on typed params, re-validating validated data).
- No speculative generality: optional params, config knobs, or extension points nobody asked for.

### G. Structure and abstraction
- **Prefer deep modules:** a small interface hiding real work. Inline a helper that is *shallow* - its
  interface is as complex as its body and it is called once (pass-through wrappers, one-line forwarders,
  chains of functions that only call the next).
- **Keep** a single-use helper when it hides a real decision, names a non-obvious concept, isolates I/O,
  or is a test seam. "Called once" alone is not a reason to inline; "adds nothing" is.
- Don't split a coherent algorithm into many tiny functions; don't build class hierarchies for one variant.
- Unrequested scope (new features, files, layers, compatibility shims) - remove, or flag if unsure.
- Match the surrounding code's style; don't restyle code you aren't otherwise changing.

### H. Types and tests
- Use precise types at public boundaries; no `any`/untyped dict blobs where a real type is cheap.
- Tests check behaviour through the public interface, not mocks of the thing under test. Delete tests that
  assert nothing meaningful or only re-assert the implementation. Never weaken or skip a test to go green.

## 5. Efficiency = complexity class at `{{EXPECTED_SCALE}}`

Judge each function by how time **and** memory grow with the inputs that grow (users, rows, events, items).
Not micro-tuning, not line count. Detail and patterns: [references/complexity.md](references/complexity.md).

- **Target the lowest class that is cheap to reach:** O(1) → O(log n) → O(n) → O(n log n). Take a better class
  when it is a local change. If it needs a redesign, take the best quick class that still serves
  `{{EXPECTED_SCALE}}` with headroom, and flag the redesign (§6).
- **Must fix or justify on any request/hot path:** O(n²) or worse over a growing input; work proportional to
  the *whole* table/fleet to serve one key; N+1 queries; linear search inside a loop; unbounded growth
  (caches, lists, maps with no eviction).
- **Follow the chain.** A slow consumer is often fed too much by its producer. Fix at the point that removes the
  most work for the whole call chain (filter/aggregate/index upstream, especially in the database).
- **Measure, don't guess,** when unsure where time goes: profiler for CPU/memory, `EXPLAIN ANALYZE` (or
  equivalent) for queries. Benchmark only with realistic sizes.

## 6. Flag, don't fix (design decisions)

Stop and surface these instead of changing them silently - use the project's decision-handoff format if it has one:
- Changing a public API, schema, stored-data format, error contract, or default behaviour.
- Adding/removing a dependency, tool, or service.
- Introducing a cache (state its invalidation), an index/migration, concurrency, or batching that changes semantics.
- A complexity fix that needs a redesign, or a trade of correctness/durability for speed.
- Anything touching security, auth/permissions, or safety-critical behaviour.
- Deleting code whose use you can't prove (reflection, dynamic dispatch, external callers).

## 7. Report format

```
no-slop: <scope: diff / files> · wiring checked: <n callers, n callees>
Fixed:
- <file:line> <what> - <why, one clause>
Complexity (hot paths in scope):
- <function>: <time>, <space> via <structure/index> (was <old>) | "unchanged, already optimal: <reason>"
- Settled for <class> instead of <better class> because <cost>   (only if applicable)
Flagged (needs a decision):
- <item> - <options in one line>
Tests: <baseline result> → <after result>  ·  Scale assumed: <{{EXPECTED_SCALE}} or default>
```
Keep it short. No praise, no restating unchanged code.
