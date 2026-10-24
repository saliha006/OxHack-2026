# Complexity - patterns and profiling

Why it matters: LLM-generated code is measurably less efficient than strong human solutions even when it
passes tests (EffiBench, NeurIPS 2024; Mercury, NeurIPS 2024). Passing tests says nothing about scale.

## How to state complexity
Name the growing variables explicitly: `n` = rows, `k` = results returned, `m` = items per user, etc.
Give time **and** extra space. Use amortised cost where relevant (dynamic-array append is amortised O(1);
a hash map is O(1) average, O(n) worst). Note when a constant factor is genuinely dominant (tiny `n`, I/O-bound).

## Pattern table (bad → good)
| Smell | Typical cost | Fix | Result |
|---|---|---|---|
| `x in list` / `.find()` / `indexOf` inside a loop | O(n·m) | build a `set`/`dict`/`Map` once | O(n + m) |
| Nested loops joining two collections | O(n·m) | index one side by key | O(n + m) |
| Query inside a loop (N+1) | N round-trips | one batched query / `IN (...)` / join / eager load | 1-2 round-trips |
| Load whole table, filter in app code | O(table) per request | `WHERE` on an indexed column, `LIMIT`, aggregate in DB | O(log n + k) |
| Re-sort after every insert | O(n log n) per insert | `bisect`/sorted structure, or sort once at the end | O(log n)/O(n) per insert |
| Top-k by full sort | O(n log n) | heap (`heapq.nlargest`, priority queue) | O(n log k) |
| Sliding window by slicing/rebuilding | O(w) per step | `deque(maxlen=w)` / ring buffer | O(1) per step |
| String built with `+=` in a loop (some langs) | O(n²) | `join` / builder | O(n) |
| `list.pop(0)` / `shift()` as a queue | O(n) each | `deque` / real queue | O(1) |
| Same pure computation repeated in loop | O(n·cost) | hoist / memoise | O(cost) |
| Rewrite a whole blob to change one field | O(size) | per-row/per-key update | O(1)/O(log n) |
| Collection that only ever grows | O(history) memory | TTL, `maxlen`, LRU, retention, move to storage | bounded |
| Count/len of a materialised list | O(n) memory | `COUNT(*)`, generator, `sum(1 for ...)` | O(1) memory |
| Unpaginated list endpoint | O(table) | cursor/keyset pagination | O(page) |

Every hot query should hit an index; name it in the report. Missing indexes and unbounded loads are the most
common real-world database performance bugs (Yang et al., ICSE 2018), and most fixes are under ~5 lines.

## Profiling - measure the right thing
1. Reproduce with realistic input sizes (`{{EXPECTED_SCALE}}`), not toy data.
2. Profile, find the top cost, fix, re-measure. Change one thing at a time.
3. Prefer sampling profilers on real workloads (low overhead, less distortion); use deterministic tracing for
   call counts.

| Stack | CPU | Memory | Notes |
|---|---|---|---|
| Python | `cProfile` + `snakeviz`, `py-spy` (sampling, attach to live), `scalene` | `tracemalloc`, `scalene`, `memray` | `timeit` for micro-checks |
| JS/Node | Chrome DevTools Performance, `node --cpu-prof`, `clinic flame` | DevTools heap snapshots, `clinic heapprofiler` | |
| Go | `pprof` (`go test -cpuprofile`, `net/http/pprof`) | `pprof` heap | `go test -bench` |
| JVM | async-profiler, JFR | JFR, heap dumps | JMH for benchmarks |
| SQL | `EXPLAIN ANALYZE` (Postgres/MySQL 8), query plan viewers | - | look for Seq Scan on big tables, row-estimate mismatch |
| Any | `perf`, flame graphs | | |

Report the complexity class change, not just milliseconds.
