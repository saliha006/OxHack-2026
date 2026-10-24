# Tier 3 playbook: flaky, concurrency, environment, prod-only

Loaded from `debug/SKILL.md` Tier 3. Goal: turn a "sometimes" bug into an "always" bug, then use Tier 1/2.

## 1. Flaky tests

**Quantify it.** Every test is flaky to some degree (Meta). Measure the failure rate instead of arguing:
- pytest: `pytest --count=100 test_x.py` (pytest-repeat plugin); `pytest-randomly` shuffles order (`-p no:randomly` to turn off)
- Jest: `--runInBand` vs parallel, `--randomize`; Go: `go test -count=200 -race -shuffle=on`
- Run the test **alone** and **in the full suite**: passes alone, fails in suite = shared state / order dependence.

**Root causes, roughly by frequency (varies by language - check all):**
1. Async wait - sleeps/timeouts instead of waiting on a real condition
2. Concurrency - races, deadlocks, unordered results compared as ordered
3. Test order dependence - leaked globals, DB rows, files, env vars, singletons, monkeypatches not undone
4. Network / external services - real HTTP, DNS, rate limits
5. Time - `now()`, timezones, DST, midnight/month boundaries, slow CI clocks
6. Randomness - unseeded RNG, hash/set ordering, UUIDs in assertions
7. Resources - ports in use, temp files, file-descriptor/connection leaks
8. Platform - OS, path separators, case sensitivity, locale, float differences

**Check for clusters.** Flaky failures often co-occur and share one root cause (typically network or an unstable
dependency). If several tests flake together, debug the shared fixture, not each test.

**Fix the cause, not the symptom.** Retries, `sleep`, and longer timeouts hide the bug and slow the suite. Only
quarantine a test (with an owner and a ticket) as a stopgap, never as the fix.

## 2. Concurrency / races

- Run with a race detector: C/C++/Rust `-fsanitize=thread`, Go `-race`, Java: jcstress / thread-safety annotations.
  They only catch races on interleavings that actually run, so combine with stress (many iterations, more threads, CPU
  load). Expect a several-fold slowdown (Uber saw ~4x on its Go test suite).
- Heisenbug (vanishes when observed): breakpoints and prints change timing. Use cheap in-memory logging with
  timestamps + thread ids, dumped after failure, or **record-and-replay** (rr on Linux, time-travel debuggers) to
  capture one failing run and replay it deterministically.
- Shrink the interleaving: fewer threads, smaller data, force an ordering with barriers to confirm the hypothesized
  race.
- Typical patterns: check-then-act without a lock, shared mutable collection, lazy init, missing `await`, callbacks
  firing after teardown, non-atomic counters, lock ordering inversion.

## 3. Environment / dependency / config ("works on my machine")

Diff the working vs broken environment, one variable at a time:
- Runtime + dependency versions (lockfile honoured? `pip freeze`, `npm ls`, `go version -m`)
- Env vars and config files actually loaded (print them at startup - redact secrets)
- OS, arch, locale, timezone, file-path case, line endings, permissions
- Feature flags, data present in the DB, caches/build artefacts (clean build)
- Network: proxies, DNS, TLS certs, firewall
Reproduce in a clean container/VM. If it reproduces there, it's in the code; if not, it's in the environment.
After a dependency bump, read its changelog before reading your code.

## 4. Production-only bugs

1. **Stop the bleeding** first: rollback, feature flag, shed load. Root cause comes after users are safe.
2. **Preserve evidence**: logs, the failing request payload, core/heap dump, metrics window. Don't restart away the
   only reproduction without a dump.
3. **What touched it last?** Deploys, config changes, traffic shape, data shape, upstream outages. Overlay them on the
   metric graph.
4. **Capture and replay** the failing input locally or in staging. Then it's a Tier 1/2 bug.
5. Correlation across many metrics is cheap and often spurious - treat it as a hypothesis to falsify.
6. Afterwards: blameless postmortem - timeline, root cause, why detection was slow, the regression test, and the
   monitoring/alert that would have caught it earlier.

## 5. Hardware / IO / serial / devices

Bottom-up, one layer at a time: power and cables -> device enumerated (`dmesg`, Device Manager, `ls /dev/tty*`,
`lsusb`) -> right port -> nothing else holding it -> permissions (dialout group) -> settings match both ends (baud,
parity, stop bits, flow control, endianness) -> raw bytes arrive (serial monitor / loopback) -> parser handles partial
reads and framing. Swap known-good parts (cable, adapter, board) to split hardware vs software.

## Sources
See `Claude instructions/research-ledger.md` §2 debug (Meta probabilistic flakiness, Parry et al. EASE 2025, Luo et al./Python/JS
flaky studies, Uber Go race detection, Google SRE troubleshooting chapter, rr record/replay).
