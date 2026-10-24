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
- `bot/`: Showdown connection, log parser, request handling {{exact paths: not decided}}
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
- Agreement status: Derrick proposed and saliha said yes (2026-10-24 17:20); **Nate's yes is pending** (§2c), so the parser is provisional until it lands.
- Notes (`Research-Context/notes-bot-setup.md`, research doc pass 6): poke-env 0.16.1 works on this Python; Showdown needs Node >= 22.18; the public server requires bot registration (`/ht`) and has a bot policy; a local server needs no account.

**Out of scope:** decision logic, data ingestion, training; voice.

**Guardrails:**
- ⛔ **Off-plan → CLAUDE.md §2c.**
- The four bot-skeleton choices (framework, server, format, bot↔decision contract) are 🟠 decisions for the user; none made yet except that the contract is `BattleState`.
- 🟠 Open from Derrick's board row: the parser must reset `sides[*].last_move` to null when that side switches (the decision layer reads it for Choice lock / Encore). Not confirmed yet; if yes, spell it out in `contracts/battle-state.md`.
- Never commit secrets: any account password goes in `.env`, never in code.

---

## 3. ▶ Current tasks (2026-10-24), in order
*Status: ⬜ not started · 🟡 in progress · ⏸ blocked · ✅ done*

1. ⬜ **Decide the bot skeleton** (framework, server, format): a 🟠 handoff. The notes lean to poke-env, local server first, gen9randombattle then gen9ou.
   - *Done when:* the user picked and it's logged in the PRD NOW.
2. ⬜ **Run a local Showdown server and a bot that plays random legal moves end to end**
   - *Done when:* a full battle completes unattended and the log is saved.
3. ⬜ **Log parser to `BattleState`** `[⚠ touches @derrick: contract meaning, incl. the last_move reset]` `[⏸ waits on @nate: his yes on bot-layer ownership]`
   - Follow `contracts/battle-state.md` and the real sample log in `design/bot-layer.md`; test on a real game, not a hand-made fixture.
   - *Done when:* a recorded game parses turn by turn into valid `BattleState` JSON matching Derrick's turn-2 example.
4. ⬜ **Wire the decision layer** (`build_state` then `select`) `[⚠ touches @derrick]`
   - *Done when:* the bot plays a battle choosing moves via the decision layer and beats the random-move baseline over N games (win rate reported with an interval).
5. ⬜ **Save per-turn state + choice for the coach-style replay review** (voice stays an optional add-on).

## 6a. Reference
- `design/bot-layer.md`; research doc passes 3 (evaluation) and 6 (bot setup); Showdown request kinds and log lines are in the design doc §1a.

## 4. Done log (newest first)
- (empty)

## 5. Working-style notes for the agent
- Verbosity Level 0: options + a recommendation, no teaching notes. Flag scope creep at once.
- Hackathon pace (25 h): the smallest thing that passes its *Done when*; the cut order is in the research doc's READ THIS FIRST.

## 6. Open blanks (fill when the chat or repo answers them, CLAUDE.md 🔁)
- Paths under `bot/`; the 🟠 skeleton choices; confirmation of the `last_move` reset.
- Registry blanks (vault path, team name, Scale, Deploy) are still open in CLAUDE.md.

---
── Archived (superseded <date> — do NOT action) ──
(none)
