> **Status, 2026-10-25 ~10:00 UTC.** Live parser/player, demo (terminal + one battle-chat line per decision), traces and the eval harness (MCTS pairings, Foul Play levels, manifest guard) are on `main`, which runs Kenar's MCTS by default. How the system works today: PRD v4.

# Saliha: Bot layer (Showdown connection, log parser to BattleState, request handling, eval harness, demo) + doc owner
**GitHub:** `saliha006` · **Branch:** `sali` · **Tool:** Claude Code · **Brief last updated:** 2026-10-25 ~10:00 UTC by saliha
**Spec:** the PRD (`OxHack-2026-PRD.md`) and `design-decision/*.md`. A bare § means the PRD; CLAUDE.md and this brief's own sections are always named.

## 0. How the agent reads this brief (every task)
1. `CLAUDE.md` is already loaded (don't re-read it); read this brief once. Follow both.
2. **Work `▶ Current tasks` top to bottom.** The order is the pass 9 build plan: two research agents plus an adversarial critic, using peer-reviewed papers, official docs and source, practitioner consensus, the current code and the PRD. Each task names the recommended design and the main alternative.
3. **Want a different route, more features or another decision in your area? Go ahead.** Your Claude always asks first: "Have you told the team? Who agreed?" (CLAUDE.md §2c). Changes to another builder's path or a shared contract wait for that owner's yes.
4. Before starting, read `progress.md`'s 📌 Open board (CLAUDE.md §2b). Rows To @saliha come first: tell the user, then resolve or schedule them.
5. Ship each task with the CLAUDE.md §7 sequence, then log it (CLAUDE.md §2b). Use the `debug` skill on every issue.
6. Times are **UTC** (UK clocks go back at 02:00 BST on Sunday).

**Task tags:** `[⚠ touches @name: what]` = changes someone else's area or a shared contract; get that owner's yes before merging (§2c). `[⏸ waits on @name: what]` = blocked until they deliver (a 📨 row on the Open board). `[🟠 your call]` = a design decision for the user (CLAUDE.md §1).

---

## 1. Ownership
**Owns:**
- `bot/`: `player.py` (Showdown connection + request handling), `parser.py` (log → `BattleState`), `eval.py`, `demo.py`, `tests/`
- `runs/` (git-ignored): raw logs, decision traces, eval results
- `design-decision/bot-layer.md`: its design
- PRD, CLAUDE.md, skills, event doc, research doc, `progress.md` upkeep (doc owner)

**Does NOT touch:**
| Area / path | Owner | Why it's theirs |
|---|---|---|
| `decision/`, `tests/`, `pyproject.toml`, `contracts/battle_state.py` (shape) | @derrick | decision layer + contract author |
| `data/` | @nate | data layer |

**Shared** (flag in `progress.md` ⚠️ Conflicts): `contracts/*`, `fixtures/*`.

## 2. Contract & Guardrails
**Scope contract.** Saliha builds the layer between Showdown and the decision layer, plus the proof that it works (`design-decision/bot-layer.md`): connect to the local server, track state with the parser, call `agent.choose(request, battle_state)` per request, send the choice back, write the trace, run the eval, drive the demo.
- Agreement: Derrick proposed, saliha said yes (17:20) and waived a separate yes from Nate on 2026-10-24. Nate is informed and can object on the Open board.

**Out of scope:** decision logic, data ingestion, training; voice; public ladder play; browser side panel.

**Guardrails:**
- ⛔ **Off-plan → CLAUDE.md §2c.**
- The bot↔decision contract is `BattleState` + `agent.choose(request, battle_state)`, in-process. The parser resets `sides[*].last_move` on switch and emits `Event.source` exactly as the contract spells it.
- Never commit secrets or data files.

---

## 3. ▶ Current tasks (2026-10-25 ~10:00 UTC)
*Demo freeze 10:30 UTC (no code after it), submission 12:00 UTC. Status: ⬜ not started · 🟡 in progress · ⏸ blocked · ✅ done*

1. 🟡 **Merge the eval** `[⏸ waits on @derrick @kenar @nate: runs/eval/<machine>-*.jsonl]`: this laptop's slice is done (seed 104, fphard: `mcts8` 2-2, `mcts8joint` 4-7, 15 games; games that overlapped a demo battle are flagged). Put every file in `runs/eval/`, run `uv run python -m bot.eval report`.
2. ⬜ **Pick the demo flags and pinned team** by the PRD §0 rule (flag only with a Wilson lower bound above 50% vs `mcts8`; team by win rate among teams whose median game is 35 turns or less). Candidates: `--engine-threads 4` (Nate 11/14), `--teams bot/teams/standin/team_6.txt`. `[🟠 your call]`
3. ⬜ **Verify the browser view** with the chosen flags: the raw log has `|c|☆oxhack demo|` lines and no "must be registered to chat". *(Already true for today's demo battles 577–591.)*
4. ⬜ **Rehearse twice by 10:20, freeze at 10:30.**
5. ⬜ **10:30–12:00, docs only:** README (demo command, what the terminal and battle chat show, the honest win-rate table, credit to Foul Play and Laplace); `progress.md` entry + 📊 Latest; Devpost submission.
6. ⬜ **Board rows waiting on others:** @kenar's yes/no on the opt-in Tera gate in his files; @nate's yes/no on the observed-set priors files in `data/`.

── Archived (superseded 2026-10-25 ~10:00 UTC — do NOT action) ──

### Current tasks (2026-10-24 21:10 UTC, pass 9 build plan), in order
*Status: ⬜ not started · 🟡 in progress · ⏸ blocked · ✅ done · Hours = focused work*

1. ✅ **Rust toolchain + `poke_engine` build** (0.75 h, timebox 45 min). Nothing that calls `Agent.choose` runs on this machine until `poke-engine` builds from source.
   - Install `uv`, then Rust: `rustup` with the `gnu` host (msys64 mingw is already on PATH) or the MSVC build tools. Then `uv sync` and `uv run pytest --cov=decision`.
   - Not building by 21:45 UTC → Docker Desktop (installed) or run agent work on Derrick's Mac, and keep going on a stub agent.
   - *Done when:* `uv run pytest --cov=decision` is green on this machine.
2. ✅ **Add `poke-env==0.16.1`** to `pyproject.toml` (0.1 h) `[⚠ touches @derrick: pyproject.toml]`: notify him with a ⚠️ row (he adds `scikit-learn` himself when his tasks need it; nate adds `matplotlib`).
3. ✅ **Smoke battle + bot integration** (`bot/player.py`, 1.5 h; first real game by 00:30 UTC) `[⚠ touches @derrick]`
   - **Recommended [P9 B1 + critique]:** a poke-env `Player` subclass. Override `_handle_battle_message` and feed **the whole message** to our `Parser` **before** calling `super()`, so state is current when the request is handled (#246). `choose_move` calls `agent.choose(...)` **blocking**: one `Agent` per battle, `max_concurrent_battles=1` per process. Parallelism comes from shard processes (task 5), not threads.
   - **Rejected:** a `ProcessPoolExecutor` job per turn. `Agent` keeps per-battle state (belief, last choice), so stateless jobs lose the belief reweight.
   - Wrap `super()._handle_battle_message` in try/except, plus a per-battle watchdog that forfeits a hung battle (#973). On a forced-switch request, assert our parser's turn matches the request.
   - `/choose ` prefix on every order; team preview sends `/choose team 123456`. `|error|[Invalid choice]` → first legal option from the fresh request, then `/choose default`.
   - **Count fallbacks per game** (decision errors and timeouts); fail the smoke run if they're above a few percent. Route the `decision` logger to `runs/<battle-id>.decision.log`.
   - *Done when:* 10 battles in a row vs the random bot finish unattended, each raw log saved to `runs/<battle-id>.log`, with the fallback rate printed.
4. 🟡 **Decision trace** (`runs/<battle-id>.jsonl`, one line per request; 0.5 h) `[⏸ waits on @derrick: agent.last_trace]`
   - Turn, request kind, `BattleState`, choice, top 3 options with scores, win probability, top sets per opponent Pokémon, think time in ms, fallback flag.
   - *Done when:* every request of a game has a line, and the file reloads into the same `BattleState`s.
   - *(2026-10-25 annotation: ✅ with Kenar's MCTS `last_trace`: worlds, own/opponent support, sampled worlds. No win probability: visit shares instead.)*
5. 🟡 **Eval harness** (`bot/eval.py`, built 22:33 UTC; final run waits on @nate's team pool + real priors and @derrick's belief fixes)
   - **Built (B+, saliha's pick):** six matches, same team on both sides, sides alternating. Headline full vs SimpleHeuristics 300; data ladder full vs frozen prior 200 and frozen prior vs flat prior 200; 5 scenarios vs 1 200; MaxBasePower 100; Random 30. Add learned vs HP value (200) when derrick's model ships.
   - Shard processes (cores − 2), one line per game in `runs/eval-<match>-<machine>-<shard>.jsonl`, reruns skip finished games, `report` merges all machines' files: Wilson 95% + team bootstrap, fallback rate, worst p99. Eval budget 1.0 s.
   - **Added 23:10 UTC (saliha's pick B):** blind shuffled schedule, anonymous names, random opponent think time, random team per game; Elo ladder (uneven random-move mixes, our variants, Foul Play at 3 uneven search bands); Bradley-Terry ratings + ±1–3 neighbour report; turn-0 games void. 27 pairings, 1,750 games; first full run started 23:10 UTC on stand-in priors.
   - *Done when:* the merged table is in `progress.md` → 📊 Latest, and the headline interval's lower bound is above 50%.
   - *(2026-10-25 annotation: ✅ harness extended for MCTS: pairings vs SimpleHeuristics and Foul Play `fphard`, head-to-heads vs `mcts8`, `runs/eval/<machine>-<shard>.jsonl`, manifest guard. The legacy pairings measure the one-ply bot. Today's merged table is current task 1.)*
6. ⬜ **Record a full live battle** (client + terminal, with Wi-Fi up; 0.5 h, by 04:00 UTC). The local client redirects to `psim.us`, so the live view needs internet [P9 B5].
   - *Done when:* a video of one whole game plus its `runs/*.jsonl` is saved.
   - *(2026-10-25 annotation: traces of demo battles 577–591 are saved in `runs/`; `bot.demo replay` covers no-Wi-Fi. No video recorded.)*
7. ✅ **Demo mode + terminal stream** (`bot/demo.py`, 1.5 h): one command starts a battle vs `SimpleHeuristicsPlayer`, prints the URL, streams each turn in plain ANSI: choice, top 3 options, win probability, top opponent sets. It can also replay a saved `runs/*.jsonl` when there's no internet.
   - *Done when:* the 4-minute walkthrough (§18) runs from one command twice in a row, and the replay mode works offline.
8. ⬜ **Final eval** on frozen code: the full run started 23:10 UTC is the demo's numbers unless derrick's fixes + nate's priors land early enough for a rerun to finish by ~05:30 UTC. *(2026-10-25 annotation: superseded: the demo bot is now MCTS, measured by today's 08:20–09:45 slices.)*
9. ⬜ *(stretch, first to cut; proposed hand-over from @derrick, needs his yes)* *(2026-10-25 annotation: cut, PRD §4.)* **Coach review** (1.5 h): per-turn regret on the **baseline's** turns in our eval games (we hold both requests; our own bot's regret is zero by construction). Value = expected next state in win-probability points [P9 D5 + critique].

**Seams** (the same note is in the other two briefs):
- @derrick: `agent.choose(request, battle_state) -> str | None`, one `Agent` per battle; `agent.last_trace` feeds task 4; his p50/p99 profile sets the eval think budget (task 5).
- @nate: `states_from_log(log_lines, us)` turns his replays into training states; his team pool feeds task 5; his charts read `runs/*.jsonl` and `runs/eval-*.jsonl`.

## 6a. Reference
- `design-decision/bot-layer.md`; `contracts/battle-state.md`; research doc passes 3, 6, 8 and 9 (`research_notes/pass9-bot-data-eval.md`, `pass9-critique.md`).
- **Local server (done once):** `pokemon-showdown/` checkout, `node pokemon-showdown start --no-security`, http://localhost:8000. `generate-team gen9ou` throws locally; teams come from Nate's pool.

## 4. Done log (newest first)
- ✅ **Demo decisions in the battle chat + opt-in Tera gate flag** (`bot/demo.py`, `--tera-min-wins`): one chat line per decision so browser viewers see the search's view. Needs the local `pokemon-showdown/server/chat.ts` patch. On `main` @ `a466c0c`.
- ✅ **Opt-in Tera gate + eval arms** (`mcts8tera`, `mcts8mix`; `decision/search_policy.gate_tera`, Kenar's path, ⚠️ row): on `main` @ `8f0a3f2`.
- ✅ **Four-thread arm** (`mcts8t4`, `--engine-threads`): on `main` @ `1205e5c`.
- ✅ **Observed-set priors** (code name "joint") (`data/pipeline/joint_sets.py` → `data/set_candidates_joint.json`, arm `mcts8joint`; Nate's path, ⚠️ row): on `main` @ `698492b`.
- ✅ **fphard Foul Play level + MCTS eval pairings** (vs SimpleHeuristics, vs Foul Play, head-to-heads vs `mcts8`): on `main` @ `a935f71`, `ba1b455`.
- ✅ **Live demo search view** (Weighing / Expects them / Guessing per turn): on `main` @ `b04c95f`.
- ✅ **Task 7, demo mode** (`bot/demo.py`): live battle streamed turn by turn (choice in words, actives, think time, any agent fields generically) and offline replay of a saved trace. On `main` @ `ecbb278`.
- 🟡 **Task 4, trace**: `runs/<battle>.jsonl` gets a line per request (turn, kind, choice, think ms, fallback, `BattleState`), line-buffered, and reloads into the same states; top options + win probability arrive when derrick exposes `agent.last_trace`. `progress.md` 2026-10-24 21:47.
- ✅ **Tasks 1–3, toolchain + live bot** (`bot/player.py`, `bot/smoke.py`): uv + Rust (MSVC) installed, `poke-engine` builds; `poke-env==0.16.1` added. Measured: the log always lands before the request on the local server (#246 doesn't reproduce). 10/10 smoke games vs RandomPlayer finished unattended; 51 bot tests, 100% on `player.py`. Fallbacks (12.7%) all come from two `belief.py` bugs (Open board to @derrick) and the 2-species example priors. On `main` @ `d8bf19f`. `progress.md` 2026-10-24 21:47.
- ✅ **Task 3 (old numbering), log parser** (`bot/parser.py`): turn 2 of the sample replay equals the contract example; 20 public gen9ou games parse with no skipped line; 25 tests, 100% coverage. On `main` @ `c25be7e`. `progress.md` 2026-10-24 20:36.
- ✅ **Task 1 (old numbering), bot skeleton** (research pass 8): poke-env 0.16.1, gen9ou with one fixed team + a seeded pool, local server. `progress.md` 2026-10-24 20:15.

## 5. Working-style notes for the agent
- Verbosity Level 0: options + a recommendation, no teaching notes. Flag scope creep at once.
- Hackathon pace: the smallest thing that passes its *Done when*; cut order is PRD §19.

## 6. Open blanks (fill when the chat or repo answers them, CLAUDE.md 🔁)
- Which `competitive/gen9ou` team we play (nate's task 3 picks it with saliha and derrick). *(2026-10-25: superseded: the demo plays one of the 10 teams in `bot/teams/standin/`, pinned or random; current task 2.)*
- Registry blanks (vault path, team name, Scale, Deploy) are still open in CLAUDE.md.

---
── Archived (superseded 2026-10-24 21:10 UTC by the pass 9 build plan — do NOT action) ──
- Old task 2 (local server + smoke battle) → folded into task 3, now with the whole-message tap, blocking `choose_move` in shard processes, and fallback counting.
- Old task 4 (wire the decision layer: search off the event loop in an executor) → replaced by task 3's blocking call in shard processes (the `Agent` is stateful).
- Old task 5 (trace) → task 4. Old task 6 (eval, 100 games per baseline) → task 5 (team-neutral, 300 on the headline leg).
- Old task 7 (demo) → tasks 6–7. Old task 8 (hardening: reconnect) → dropped; resume-from-file and the watchdog cover it.
- Old task 9 (public ladder run) → cut (PRD §4).
- The original five tasks (skeleton, random bot, parser, wiring, per-turn save) → folded in earlier.
