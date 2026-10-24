# Saliha: Bot layer (Showdown connection, log parser to BattleState, request handling, end-to-end bot) + doc owner
**GitHub:** `saliha006` · **Branch:** `sali` · **Tool:** Claude Code · **Brief last updated:** 2026-10-24 by saliha
**Spec:** the PRD (`OxHack-2026-PRD.md`) and `design/*.md`. A bare § means the PRD; CLAUDE.md and this brief's own sections are always named.

## 0. How the agent reads this brief (every task)
1. `CLAUDE.md` is already loaded (don't re-read it); read this brief once. Follow both.
2. **Only action `▶ Current tasks`**, top to bottom.
3. Before starting, read `progress.md`'s 📌 Open board (CLAUDE.md §2b). Rows To @saliha come first: tell the user, then resolve or schedule them.
4. Ship each task with the CLAUDE.md §7 sequence, then log it (CLAUDE.md §2b). Use the `debug` skill on every issue.
5. Token budget (CLAUDE.md): Grep `OxHack-2026-research.md` by pass number, never read it whole; read only the `design/` doc for your layer.

**Task tags:** `[⚠ touches @name: what]` = changes someone else's area or a shared contract; get that owner's yes before merging (§2c). `[⏸ waits on @name: what]` = blocked until they deliver (a 📨 row on the Open board).

---

## 1. Ownership
**Owns:**
- `bot/` (proposed): `player.py` (Showdown connection + request handling), `parser.py` (log → `BattleState`), `eval.py`, `demo.py`, `teams/`, `tests/`
- `runs/` (git-ignored): raw logs, decision traces, eval results
- `design/bot-layer.md`: its design
- PRD, CLAUDE.md, skills, event doc, research doc, `progress.md` upkeep (doc owner)

**Does NOT touch:**
| Area / path | Owner | Why it's theirs |
|---|---|---|
| `decision/`, `contracts/battle_state.py` (shape) | @derrick | decision layer + contract author |
| `data/` | @nate | data layer |

**Shared** (flag in `progress.md` ⚠️ Conflicts): `contracts/*`, `fixtures/*`.

## 2. Contract & Guardrails
**Scope contract.** Saliha builds the layer between Showdown and the decision layer (`design/bot-layer.md`):
- Connect to a Showdown server (local first), receive `|request|` JSON + log lines, track state, fill Derrick's `BattleState` each turn, call the decision layer, send the `Choice` back.
- Agreement: Derrick proposed, saliha (doc owner) said yes (17:20) and waived a separate yes from Nate on 2026-10-24 (the bot layer touches the data layer only through `BattleState`). Nate is informed and can object on the Open board.
- Notes (research doc pass 6): poke-env 0.16.1 works on this Python; Showdown needs Node >= 22.18; the public server requires bot registration (`/ht`) and has a bot policy; a local server needs no account.

**Out of scope:** decision logic, data ingestion, training; voice.

**Guardrails:**
- ⛔ **Off-plan → CLAUDE.md §2c.**
- The bot-skeleton choices (framework, format + our team, server) are 🟠 decisions for the user (task 1). The bot↔decision contract is `BattleState` + `agent.choose(request, battle_state)`; with a Python bot it's an in-process call, which settles the contract's open hand-over question.
- Confirmed 2026-10-24: the parser resets `sides[*].last_move` to null when that side switches (the decision layer reads it for Choice lock / Encore). Derrick spells it out in `contracts/battle-state.md`.
- The parser emits `Event.source` values exactly as the contract's examples spell them (`"stealthrock"`, `"item:<id>"`): Derrick's belief rules match on them.
- Never commit secrets: any account password goes in `.env`, never in code.

---

## 3. ▶ Current tasks (2026-10-24 19:45, demo plan), in order
*Status: ⬜ not started · 🟡 in progress · ⏸ blocked · ✅ done*
*Suggested clock: skeleton playing by 23:00 BST · parser + decision wired by 03:00 GMT · eval numbers by 07:00 · demo freeze 10:00 · submit before 12:00 GMT.*

1. ✅ **Pick the bot skeleton** (2026-10-24, research pass 8): **poke-env 0.16.1**, a thin `Player` subclass that taps raw lines and calls Derrick's `Agent`; **gen9ou**, one fixed validated team for us and a seeded pool of validated opponent teams; **local server** (running from `../pokemon-showdown`, port 8000).
   - Still to do: `uv add poke-env==0.16.1` (touches Derrick's `pyproject.toml` `[⚠ touches @derrick]`), then `uv sync` to confirm it installs next to `poke-engine` 0.0.48. Also confirm the `poke-engine` 0.0.48 wheel has Gen 9 built in (foul-play builds non-default generations from source); a gen9ou smoke game through `Agent.choose` settles it. Full report: `Research-Context/reports/Showdown bot framework and format.md`.
2. ⬜ **Local server + smoke battle** (manual setup: §6a)
   - `bot/player.py`: a poke-env `Player` that picks a random legal move; two of them battle on `localhost:8000` (`ws://localhost:8000/showdown/websocket`; poke-env's `/trn name,0,` login works because of `--no-security`).
   - Wrap `super()._handle_battle_message` in try/except: poke-env issue #973 swallows parse errors and hangs the run. Grep the log for "Unhandled exception" after the run.
   - Check that `|request|` arrives after the turn's log lines on forced switches (poke-env issue #246); if not, defer the decision until the lines land.
   - *Done when:* 10 battles in a row finish unattended, each raw log saved to `runs/<battle-id>.log`.
3. ✅ **Parser: protocol lines → `BattleState`** (`bot/parser.py`) `[⚠ touches @derrick: contract meaning]`
   - A pure function over log lines, no network, so it runs on live battles **and** on saved replay `.log` files (Nate reuses it offline: Seams).
   - Covers every row of the table in `contracts/battle-state.md`, incl. the `last_move` reset on switch and the exact `Event.source` strings.
   - Tests, happy / edge / failure: replay `gen9ou-2703852247` turn 2 equals `contracts/examples/battle_state_turn2.json`; forced switch with no `|turn|` before it; double faint; nickname vs species (`p2a: Samurott` → `samurotthisui`); `|detailschange|` / `|-formechange|`; Illusion `|replace|`; Tera (`|-terastallize|` and `, tera:` in DETAILS); `[from] item:` / `[of]` tags; `0 fnt` HP; unknown lines skipped, never a crash.
   - *Done when:* 20 recorded games parse end to end with no exception, and the contract test passes.
4. ⬜ **Wire the decision layer** `[⚠ touches @derrick]`
   - One `Agent(priors)` per battle. Raw lines come from overriding `_handle_battle_message`; the request dict is `battle.last_request`. Skip `wait: true` requests; an `update: true` request refreshes the same decision.
   - `agent.choose(...)` returns `"move 2"` etc.; poke-env sends `SingleBattleOrder` text verbatim, so add the `/choose ` prefix (no `rqid` needed). Team preview returns `/choose team 123456`.
   - Run the search off the event loop (executor or thread), or the 20 s websocket keepalive can drop the connection.
   - `|error|[Invalid choice]` or `[Unavailable choice]` → send the first legal option from the fresh request, and `/choose default` if the error repeats (poke-env's own fallback fires 1 time in 1,000). Never stall the timer.
   - Route the `decision` logger to `runs/<battle-id>.decision.log` (Derrick's 18:50 note).
   - *Done when:* 20 games vs the random bot finish with zero stalls or invalid-choice loops, and no game is lost on time.
5. ⬜ **Decision trace** (`runs/<battle-id>.jsonl`, one line per request) `[⚠ touches @derrick: trace fields]`
   - Turn, request kind, `BattleState`, chosen choice, top 3 options with scores, win-probability estimate, top sets per opponent Pokémon, think time in ms.
   - Feeds the demo, the replay review and Nate's charts.
   - *Done when:* every request of a game has a line, and the file reloads into the same `BattleState`s.
6. ⬜ **Evaluation harness** (`bot/eval.py`): the HRT "decision beats a baseline" proof
   - 100 games each vs poke-env's `RandomPlayer`, `MaxBasePowerPlayer` and `SimpleHeuristicsPlayer` on the local server, 4–8 at once (`max_concurrent_battles` on both sides, a distinct account name per baseline, `battle_against` + `win_rate`; `evaluate_player` is gen8-only). Opponent teams from Nate's pool, seeded.
   - Add a mirror leg (a baseline on our fixed team) to separate team strength from agent skill.
   - Reports win rate with a 95% Wilson interval, p50 / p99 think time, crashes and timeouts; writes `runs/eval-<stamp>.json`.
   - *Done when:* the table is in `progress.md` → 📊 Latest, and the interval's lower bound is above 50% vs `MaxBasePowerPlayer`.
7. ⬜ **Demo mode** (`bot/demo.py`): one command starts a battle on the local server, prints the URL to watch it in the Showdown client, and streams each turn's choice, top options and win probability to the terminal. A browser side panel is a 🟠 scope addition (who builds it is open).
   - *Done when:* the 4-minute judge walkthrough runs from one command, twice in a row, with no internet.
8. ⬜ **Hardening**: reconnect after a dropped socket; forfeit cleanly on an unrecoverable error; save replays of the best games; record a backup video of one full game.
   - *Done when:* killing and restarting the server mid-run loses at most the battles in flight.
9. ⬜ *(stretch, 🟠 your call)* **Public ladder run**: registered account + bot registration (`/ht`), password in `.env`, ~20 ladder games for a real Elo. Check the organisers' rules first.

**Seams** (the same note is in the other two briefs):
- @derrick: `agent.choose(request, battle_state) -> str | None`, one `Agent` per battle; the trace (task 5) needs him to expose top options + win probability.
- @nate: the parser (task 3) turns his replay `.log` files into `BattleState`s for the (state, winner) training pairs; his team pool feeds task 6; his charts read task 5's files.

## 6a. Reference
- `design/bot-layer.md`; `contracts/battle-state.md` (on `main`); research doc passes 3 (evaluation) and 6 (bot setup); request kinds and log lines are in the design doc §1a.
- **Manual setup, once (you):** Node ≥ 22.18 (`node -v`). Then `git clone https://github.com/smogon/pokemon-showdown ../pokemon-showdown`, and in it `npm install`, `cp config/config-example.js config/config.js`, `node pokemon-showdown start --no-security`. Watch at http://localhost:8000. A local server needs no account. Public server only: a registered account plus bot registration via `/ht` (Smogon's bot policy since 2026-10-09; unregistered bots can be banned).
- Metamon is a research project (offline-RL agents + replay datasets) that plays through poke-env on a Showdown server; it is not a separate platform. Nate uses its replays; the bot doesn't need it.

## 4. Done log (newest first)
- ✅ **Task 3, log parser** (`bot/parser.py`): turn 2 of the sample replay equals the contract example; 20 public gen9ou games parse with no skipped line; 25 tests, 100% coverage. On `main` @ `c25be7e`. `progress.md` 2026-10-24 entry.

## 5. Working-style notes for the agent
- Verbosity Level 0: options + a recommendation, no teaching notes. Flag scope creep at once.
- Hackathon pace (25 h): the smallest thing that passes its *Done when*; the cut order is in the research doc's READ THIS FIRST.

## 6. Open blanks (fill when the chat or repo answers them, CLAUDE.md 🔁)
- Which gen9ou team we play (from Nate's pool); whether a browser demo panel is in scope, and who builds it.
- Registry blanks (vault path, team name, Scale, Deploy) are still open in CLAUDE.md.

---
── Archived (superseded 2026-10-24 by the demo plan — do NOT action) ──
- The original five tasks (skeleton, random bot, parser, wiring, per-turn save) are folded into tasks 1–5 above.
