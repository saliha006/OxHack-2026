---
name: debug
description: Evidence-first debugging workflow for any language or stack. Use whenever something is broken - an error or stack trace, a crash, a failing or flaky test, wrong or surprising output, a performance or memory regression, a hang, "works on my machine" / env / config / dependency trouble, a bug that only shows up in production, hardware or serial/IO weirdness, or the user says "it's broken", "this doesn't work", "why is this happening". Also use when you are stuck, have tried two fixes that did not work, or are about to edit code you do not yet understand.
---

# Debug

Debugging is a search, not a guess. Find the cause with evidence, prove it, fix it once, and lock it in with a test.
Source ledger for every rule here: `Claude instructions/research-ledger.md` §2 debug.

## The 5 laws (apply at every tier)

1. **Reproduce before you fix.** No repro = no proof the fix worked. (Agans "Make it fail"; agent studies show a correct repro is what makes fixes land.)
2. **Look, don't guess.** Read the actual error, data and state. Guesses only decide *where* to look next.
3. **One change at a time,** and write down what you tried and what happened.
4. **Root cause, not symptom.** Ask "why does this value/state exist?" until you reach the first wrong thing, not the line that crashed.
5. **If you didn't prove it, it isn't fixed.** The repro must fail before the fix and pass after.

## Tier 1 - Fast path (most bugs, aim for minutes)

Use when: there is a clear error or failing test, it reproduces every time, and the cause looks local.

1. **Read the whole error.** Every line of the trace. Find the *first* frame in our code, and any `caused by` / chained exception. The last line is where it blew up, not always why.
2. **Reproduce it** with one command (the failing test, a script, a curl). Save that command - it is your oracle.
3. **Check the plug.** Right file, right branch, saved, rebuilt, right venv/node_modules, right env vars, right port/device, server actually restarted. Takes 60 seconds; catches a surprising share of "bugs".
4. **Inspect the failing line and its inputs.** Read the code around it. Print/log the real types, shapes and values going in. Grep that every function, attribute and import you rely on actually exists in *this* version (never trust memory for APIs or package names).
5. **Ask "what changed?"** `git diff`, `git log -p -- <file>`, recent dependency bumps, config edits. Recent changes are the most common cause.
6. **Write the regression test first** (or keep the repro command) and watch it fail for the right reason.
7. **Make one minimal fix** at the root cause. Run the repro: it must pass. Then run the Regression gate below.

**Escalate to Tier 2 the moment any of these is true:**
- The first fix did not work (revert it first - never stack a second fix on a failed one).
- You cannot reproduce it reliably, or it is intermittent.
- No error at all: wrong output, slow, memory growth, hang.
- The crash line is clearly a victim (bad data arrived from somewhere else).
- More than ~15 minutes or 2 failed hypotheses without new evidence.
- It touches concurrency, caching, external services, env/config, hardware, or only happens in one environment.

## Tier 2 - Deep protocol (evidence triangulation)

1. **Write the problem statement.** Expected vs actual, exact repro steps, when it started, where it happens and where it does *not*. The "does not" is often the best clue.
2. **Gather at least 3 independent sources of truth** before forming a theory. Pick what fits:
   - failing test / repro output
   - logs (raise verbosity at the boundaries, add a request/correlation id)
   - traces or a debugger/breakpoint at the boundary
   - metrics over time (when did it start? does it correlate with a deploy, load, time of day?)
   - git history: `git log`, `git blame`, `git diff <last-good>..HEAD`
   - the actual data: DB rows, request/response bodies, files on disk, serialized state
   - a profiler (CPU or memory) - see `references/profiling.md`
   - environment diff between a working and a broken setup
   Triangulate: a cause you believe must be consistent with *every* source. One that explains only the stack trace is not the cause.
3. **List 2-5 ranked hypotheses.** For each: what it predicts, and the cheapest experiment that would *disprove* it. Think horses, not zebras - common causes first. Correlation is a lead, not a conclusion.
4. **Run the cheapest falsifying test first.** Record each result (hypothesis -> experiment -> result -> verdict). A ruled-out hypothesis is progress; keep it in the log so you don't re-test it.
5. **Narrow the search space by halving** when hypotheses run out:
   - **In history:** `git bisect run <repro-script>` (exit 0 good, 1 bad, 125 skip). Works for perf too: `--term-old fast --term-new slow`.
   - **In input:** shrink the failing input by repeatedly removing half until it stops failing (delta debugging). Aim for a minimal repro.
   - **In code/data flow:** check the value at the midpoint of the pipeline. Right there? The bug is downstream. Wrong? Upstream. Repeat.
   - **In environment:** swap one difference at a time between working and broken setups.
6. **Trace back to the origin.** When you know the line but not the cause, walk the data flow *backwards*: who produced this value, who called with it, where was it last correct? Fix where it first goes wrong, not where it is finally noticed.
7. **Non-crash bugs - pick the matching branch:**
   - **Wrong output:** find the first intermediate value that differs from expectation (step 5, code/data-flow halving). Check units, off-by-one, timezones/encoding, float precision, stale cache, mutated shared state.
   - **Slow / CPU:** measure, don't guess. Profile -> hottest function -> what it iterates over -> why that collection is that big or called that often. Use a baseline number and compare.
   - **Memory growth:** take two heap snapshots across repeated work, diff them, find the type/allocation site that grows, then the *retainer* holding it (cache with no eviction, listener never removed, global list, closure, unbounded queue). Trace up the data flow to who keeps appending.
   - **Hang:** dump all thread/task stacks (py-spy dump, jstack, gdb `thread apply all bt`, Node inspector). Look for lock waits, blocked IO, awaits that never resolve.
   Details and tools per language: `references/profiling.md`.
8. **Fix, then pass the Regression gate.**

## Tier 3 - Heisenbugs, flaky, concurrency, env, prod-only

Use when: it is intermittent, disappears under the debugger or prints, differs between machines, or only happens in production. Full playbook: `references/nondeterminism.md`.

- **Measure flakiness first:** run the test N times (e.g. 50-200) and record the failure rate. Re-run in random order and in isolation to expose order dependence. "How flaky" beats "is it flaky".
- **Usual suspects, in order:** async waits/timeouts, shared state between tests, test order, network/external services, time/timezone/clock, randomness without a seed, concurrency (races, deadlocks), resource leaks, platform differences.
- **Make it deterministic:** fix seeds, freeze time, stub the network, pin versions, then add stress (more threads, CPU load, slower IO) to raise the failure rate.
- **Use the right instrument:** race detectors (TSan, `go test -race`), record-and-replay (rr, time-travel debuggers) to capture one failure and replay it forever, lightweight logging instead of breakpoints when observation changes timing.
- **Env/config/dependency:** diff the two environments (versions, lockfile, env vars, OS, locale, file paths/case, permissions, feature flags, data). Reproduce in a clean container.
- **Prod-only:** stop the bleeding first (rollback/feature flag), preserve the evidence (logs, dumps, the bad payload), ask what changed (deploy, config, traffic, data). Reproduce locally with the captured input before touching code. Never debug by editing prod.
- **Hardware / IO / serial:** check power and physical connections, the right port/device, matching baud/protocol settings on both ends, another process holding the device, permissions, cable/adapter. Then loopback-test each layer separately (device -> driver -> bytes -> parser).

## Regression gate (mandatory before you call it fixed)

- [ ] The repro/regression test **failed before** the fix and **passes after**. (Optional strong check: revert the fix, see it fail again, re-apply.)
- [ ] **Blast radius checked:** grep every caller/user of what you changed; did you change a contract, default, type, or shared state they rely on?
- [ ] **Full relevant test suite** run, not just the one test. Plus lint/typecheck/build if the project has them.
- [ ] **Diff is minimal:** no drive-by refactors, no leftover debug prints, no commented-out code, no new dependency unless the user agreed.
- [ ] **Siblings checked:** does the same bug pattern exist elsewhere? Report it; fix only if in scope.

## Stopping rule - when to stop and ask the user

Stop, summarize, and ask when any is true:
- **3 hypotheses falsified, or 2 fixes failed,** with no new evidence. Then step back: re-read the problem statement, consider a fresh start with only the facts learned (long failed loops degrade agent debugging fast).
- The fix needs a **design decision**: changing an API/contract, data/storage, a dependency, security/permissions, or a safety behaviour.
- You need **access or info you don't have**: prod logs, credentials, hardware in hand, a customer's data, the intended behaviour.
- The real fix is **much bigger than the bug** (a refactor, a migration).
- The test or spec itself looks wrong. Say so - never "fix" it silently.

When asking, give: what you know (evidence), what you ruled out, your best hypothesis with confidence, and the specific question.

## Never

- Edit, weaken, skip, or delete a test to make it pass, or change expected values to match wrong output. If the test is wrong, stop and say why.
- Special-case the code for the test's inputs, hard-code expected outputs, or mock away the thing under test.
- Wrap the failure in `try/except` / `catch` / `|| true` / `?.` to silence it, or lower a log level to hide it.
- Shotgun edits: several changes at once, or keeping a change that "didn't hurt".
- Stack a new fix on top of a failed one. Revert first.
- Call an API, flag, or package from memory without checking it exists in this version.
- Add retries, sleeps, or longer timeouts to "fix" flakiness without knowing the cause.
- Declare it fixed from reasoning alone. Show the passing output.
- Dismiss the error message as wrong before proving it is.

## Report format (end every debug session with this)

```
**Root cause:** <one sentence: the first wrong thing and why it happened>
**Evidence:** <the 2-3 observations that prove it - test output, log line, profiler/bisect result>
**Ruled out:** <hypotheses tested and rejected, one line each>
**Fix:** <what changed, file:line, why this is the root and not a symptom>
**Regression test:** <name/command - failed before, passes now>
**Blast radius:** <callers/users checked, full suite result>
**Follow-ups:** <siblings found, monitoring to add, open risks>
```

Tier 1 bugs can collapse this to three lines (cause, fix, test). Never skip the test line.
