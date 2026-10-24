# Profiling cheat-sheet: CPU, memory, hangs

Loaded from `debug/SKILL.md` Tier 2 step 7. Rule of thumb: **measure a baseline, change one thing, measure again.**
Start broad (whole system), drill down (process -> function -> line -> data structure), then walk the data flow back.

## 0. Before any profiler - which resource is the problem?

USE method (Brendan Gregg): for every resource - CPU, memory, disk, network, locks, connection pools, queues - check
**Utilization, Saturation, Errors**. This tells you whether to profile CPU, memory, IO, or contention.

Anti-methods to avoid: running whatever tool you know ("streetlight"), tweaking settings until it looks better
("random change"), blaming another component without evidence.

## 1. CPU / "it's slow"

| Stack | Tool | Use |
|---|---|---|
| Python | `py-spy record -o out.svg --pid <pid>` / `py-spy top` | Sampling flame graph, attaches to a running process, no restart, low overhead |
| Python | `python -m cProfile -s cumtime script.py` | Deterministic, fine for local scripts |
| Node/JS | `node --cpu-prof` / Chrome DevTools Performance tab | Flame chart |
| JVM | async-profiler, JFR (`jcmd <pid> JFR.start`) | Low-overhead sampling |
| Go | `pprof` (`go test -cpuprofile`, `net/http/pprof`) | Built in |
| Native/Linux | `perf record -g` + flame graph | Whole system incl. kernel |
| SQL | `EXPLAIN ANALYZE` | Missing index, N+1, full scans |

Reading a flame graph: width = time. Find the widest frame that is *yours*. Then ask: is it slow per call, or called too
often? "Too often" usually means a loop over a collection that grew, or an N+1 query/request.

## 2. Memory growth / leaks

Method (same in every language):
1. Warm up first (let imports/caches settle) so startup noise isn't in the diff.
2. Snapshot A -> repeat the suspect action N times -> snapshot B (take both at the same point in the loop).
3. Diff B vs A, sort by size growth / object count growth.
4. Pick the top grower -> find its **allocation site** (where made) and its **retainer** (who still points to it).
5. Walk up the data flow to who keeps adding and why nothing removes. Classic culprits: cache/dict with no eviction,
   event listeners/callbacks never removed, global or class-level lists, closures capturing big objects, unbounded
   queues, connection/file handles never closed, memoization keyed on unique values.

| Stack | Tool | Notes |
|---|---|---|
| Python | `tracemalloc` (`start(25)`, `take_snapshot()`, `b.compare_to(a, 'lineno')`, `'traceback'` for full stacks) | Does **not** see C-extension allocations - if RSS grows but tracemalloc doesn't, suspect native code |
| Python | `objgraph`, `gc.get_referrers()` | Find what retains an object |
| Python native | `memray` | Includes native allocations |
| Node/Chrome | DevTools Memory: heap snapshot -> **Comparison** view, sort by Size Delta; **Retainers** pane; "Detached" filter for DOM | Retained size = what you'd free by deleting the object |
| JVM | `jcmd <pid> GC.heap_dump`, Eclipse MAT dominator tree | |
| Go | `pprof` heap profile, `-inuse_space` vs `-alloc_space` | |
| Native | Valgrind massif, heaptrack, ASan/LSan | |

Production: chart memory over time first. A steady climb or saw-tooth with rising floor = leak; flat = not a leak.
Also check the runtime/library version against known bugs - leaks are sometimes upstream.

## 3. Hangs / deadlocks

Dump every thread/task stack while it is hung, twice a few seconds apart; frames that don't move are the hang.
- Python: `py-spy dump --pid <pid>` (add `--locals`), `faulthandler.dump_traceback_later()`
- JVM: `jstack <pid>` (reports deadlocks)
- Go: `SIGQUIT` or `/debug/pprof/goroutine?debug=2`
- Native: `gdb -p <pid>` then `thread apply all bt`
- Node: `--inspect` and pause, or `why-is-node-running`
Look for: two threads each holding a lock the other wants, an await on a future nobody resolves, blocking IO on the
event loop, a full bounded queue with a dead consumer.

## 4. Sources
See the ledger: `Claude instructions/research-ledger.md` §2 debug (Gregg USE/methodology, Python tracemalloc docs, py-spy README,
Chrome DevTools heap snapshot docs, BuzzFeed tracemalloc case study).
