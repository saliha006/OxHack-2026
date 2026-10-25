# OxHack-2026: progress log and conflict board

The one shared doc that lives on `main`. It's where the team, and every teammate's agent, sees who shipped what, when, on
which branch, whose work it touches, and who is waiting on whom. The plan itself (`CLAUDE.md`, the PRD, the briefs) lives
on the `context` branch; this file is the history.

> **Template.** Fill `{{…}}` as the project's details arrive. Delete this note when the first real entry lands.

## How this file works (read once)
- **Newest first.** A new entry goes at the top of the Log. Stamps are `YYYY-MM-DD HH:MM` in {{timezone}}, so top to
  bottom is newest to oldest.
- **One entry per finished thing:** a feature, a fix, a deploy or infra change, a decision that changes someone's work, or
  a scope change. Not one per work-in-progress commit.
- **Write it in the same turn you push**, then commit and push `progress.md` to `main` straight away. The board is never behind.
- **Every ⚠️ conflict and 📨 need also gets a row on the Open board.** The row is removed once it's resolved, and the entry's
  Status line records who resolved it. Entries are history: never delete or reword someone else's, only annotate.
- **Merge conflict in this file?** Keep both sides, sorted newest first. Never drop an entry.
- **Volatile facts** (current commit, test counts, deploy status) live only in 📊 Latest.
- Agents: when to read and write this file is CLAUDE.md §2b; scope changes are §2c.

**Entry format** (copy it to the top of the Log):
```
### <YYYY-MM-DD HH:MM> — <feat | fix | deploy | decision | scope | docs> — <what, in plain words> — @<builder>
- **Where:** `<branch>` @ `<short sha>` · merged to `main`: yes | not yet
- **Did:** <what changed and why, 1–3 lines; numbers if you measured something>
- **Touched:** <files / modules / endpoints / contracts / infra>
- **Brief task:** <task n in builder-file-<name>.md> → ✅ done | 🟡 part | none
- **⚠️ Conflicts:** @<Name>: <what of theirs this changes or could break, and what they should do> | none
- **📨 Needs:** @<Name>: <what you need from them, and which of your tasks it blocks> | none
- **Agreed by:** @<Name>, @<Name> (decision and scope entries only)
- **Status:** open | resolved by @<Name> <YYYY-MM-DD HH:MM> (only when Conflicts or Needs isn't none)
```

---

## 📌 Open board (read on every prompt)
Everything still waiting on someone. Look for your name, or `@all`, under **To**.

| Since | From | To | Kind | What, and what to do | Entry |
|---|---|---|---|---|---|
| 2026-10-25 08:10 | @saliha | @kenar @derrick @nate | 📨 waiting on | **Eval slice by 09:30 UTC** on `main`: `git pull && uv sync`, local server running, then @kenar `uv run python -m bot.eval run --pairings mcts-foulplay-high mcts-deeper-foulplay-high --games 30 --seed 101 --machine kenar --shards 6` (stop v2 panels first) · @derrick `... --pairings mcts-deeper --games 50 --seed 102 --machine derrick --shards 3` · @nate `... --pairings mcts-headline --games 50 --seed 103 --machine nate --shards 3`. Own seed each (same seed replays the same games). Stop at 09:30, send `runs/eval/<machine>-*.jsonl` to @saliha; she runs `bot.eval report` | 2026-10-25 08:10 |
| 2026-10-25 06:41 | @derrick | @saliha | 📨 waiting on | PRD NOW: add "decision layer = Kenar's `Kenar-coherent-sets` (MCTS default, coherent priors opt-in); derrick's backtest, `choose_public` and the 1825-cutoff proposal withdrawn"; take "Backtesting frontend" out of Pending. Replaces my 03:30 row | 2026-10-25 06:41 |
| 2026-10-25 03:00 | @nate | @derrick | ⚠️ conflict | **Training data for your model is in Tiger `turns`**: 489,840 turns from 20,000 games, each `state` identical to `states_from_log`; spec, access with your read-only login, splits and baselines in `contracts/turns.md`. Bar to beat on test: HP-heuristic log loss **0.6407**, Brier **0.2246**. Also: `belief.py` `_rebuild` drops status moves on Choice items, but only Assault Vest bars them (Choice Scarf + Trick); a species missing from the set file entirely (e.g. `urshifu`) still raises KeyError in `Belief.__init__`; `predictions.md` A1 credits the set file to saliha | 2026-10-25 03:00 |
| 2026-10-25 03:00 | @nate | @saliha | ⚠️ conflict | `data/set_candidates.json` is on `main`, so `--priors data/set_candidates.json` (your default) now runs real priors: 243 species + 78 forme aliases (`keldeoresolute → keldeo`, `zamazentacrowned → zamazenta`), which answers the forme row from the data side. Your parser skips old HP strings like `20/100y` (one fact lost per such line) | 2026-10-25 03:00 |
| 2026-10-25 00:32 | @saliha | @derrick | 🔀 scope proposal | **Decision-layer plan from research pass 10** (`design-decision/strategy-research-pass10.md` on `context`): 4 specialist agents + a cross-check, peer-reviewed + official source + our own measurements. Core ~4.5 h: (1) instrumentation, (2) the two `belief.py` crash fixes + a floor (these caused the 12.7% fallbacks), (3) dual-path featurizer, (5) logistic `LearnedValue` behind a flag with HP fallback; stretch: switch share + quantal opponent model, then pool/depth-2/LP default-off. All your call; key measured facts: one-ply dominance drops Swords Dance and the top-3 EVs on our test position are 0.503/0.501/0.497, so the HP value is the weak point | 2026-10-25 00:32 |
| 2026-10-25 00:30 | @derrick | @nate | ⚠️ conflict | **Team-conditioned set priors (A6): yes, please build it after the demo.** Starting sets per opponent Pokémon from past games whose teams match theirs. Fallback: require all 5 teammates to match, then one fewer at a time until at least N games match (N is your call); at 0 it's the general priors. Belief needs it at team preview, so it's a function of their six, not a fixed file: agree the shape with @derrick first | 2026-10-25 00:30 |
| 2026-10-24 23:27 | @saliha | @all | ⚠️ conflict | **Timeline moved up: demo ready 04:00–06:00 UTC**, presentation 06:00–09:00 (PRD §19). Whatever you want in the demo needs to be on `main` by 04:00 UTC: @nate set candidates + team pool, @derrick the two belief fixes. The eval rerun on real priors only happens if it can finish by ~05:30. @derrick: the backtesting frontend is still undecided; say if you want it and who builds it | 2026-10-24 23:27 |
| 2026-10-24 20:52 | @saliha | @all | ⚠️ conflict | `context` now holds only `CLAUDE.md`, the PRD, `builder-files/` and `design-decision/` (was `design/`). Skills, the event doc and the research doc are local now. Sync with `git archive origin/context | tar -x`, then delete your old `design/` copy. Publish steps are in `CLAUDE.md` | 2026-10-24 20:52 |
| 2026-10-24 20:36 | @saliha | @derrick | ⚠️ conflict | The parser is on `main`: `from bot.parser import Parser, states_from_log`. `Parser(us).feed(line)` per protocol line, `.snapshot()` per request. Unblocks your task 3 (build_state on a parser-made BattleState) | 2026-10-24 20:36 |
| 2026-10-24 22:49 | @saliha | @derrick @nate | ⚠️ conflict | Forme mismatch at the BattleState ↔ set-candidates seam: a Keldeo with Secret Sword shows in battle as `keldeoresolute`, but team files (and likely chaos stats) key it `keldeo`, so `Belief.__init__` raises `KeyError` and that game falls back on every turn. Same risk for other battle-only formes. Needs one agreed rule: map battle-only formes to the base species (where? parser, belief lookup, or the set file's keys) | 2026-10-24 22:49 |
| 2026-10-24 21:47 | @saliha | @derrick | ⚠️ conflict | I added `poke-env==0.16.1` to your `pyproject.toml` (and `uv.lock`). `scikit-learn` and `matplotlib` come with the tasks that need them. The bot is live: `uv run python -m bot.smoke --games 10` | 2026-10-24 21:47 |
| 2026-10-24 21:15 | @saliha | @derrick | 🔀 scope proposal | Your brief is reordered by the pass 9 build plan (two research passes + a critique: peer-reviewed papers, official source, practitioner consensus, our code and the PRD). Every "Recommended" line is advice: accept it or pick your own route (decision-layer calls are yours). Key finding: poke-engine's built-in MCTS hard-wires its Rust eval, so the learned value + LP stay in our Python loop. Also yes/no on handing task 8 (belief scoring) to nate and the coach to saliha: you're at ~13 h | 2026-10-24 21:15 |
| 2026-10-24 19:16 | @saliha | @all | ⚠️ conflict | `scripts/` and every skill except `debug` and `no-slop` are gone from `context`. Keep your local copies (they stay git-ignored); `sync`/`publish` won't update from `context` any more | 2026-10-24 19:16 |

**Kinds:** ⚠️ conflict (my change touches your work) · 📨 waiting on (I'm blocked until you do X) · 🔀 scope proposal (needs
the whole team's yes, CLAUDE.md §2c) · ❓ question for a teammate (project-wide unknowns go in the PRD §21).

## 👥 Team
Full ownership and tasks live in each builder's brief (`builder-file-<name>.md` on `context`). Update your own **Now** cell
whenever you log an entry.

| Who | GitHub | Role | Branch | Owns (paths) | Now |
|---|---|---|---|---|---|
| Saliha | `saliha006` | Bot layer; doc owner | `sali` | `bot/`, `runs/` (git-ignored) | bot plays live games through `Agent.choose`; next: task 5 eval harness |
| Nate | `aldrichbanas07` | Data layer | `nate-data` | `data/` (`data/pipeline/`, `data/tests/`, `data/set_candidates.json`; `data/raw/` and `data/clean/` git-ignored), `contracts/turns.md`, the Tiger service `oxhack-data` | set file and turns table done; next: team-conditioned priors (A6) after the demo |
| Derrick | `RandomGeeb` | Decision layer | `derrick` | `decision/`, `tests/`, `contracts/battle_state.py` | own unmerged work dropped (`derrick` kept as archive); Kenar's `Kenar-coherent-sets` is the decision layer's source of truth; next: TBD |
| Kenar | `kxnar` | TBD | `Kenar-coherent-sets` | TBD | joined 2026-10-25; getting set up |

**Shared** (anyone may edit; flag it in ⚠️ Conflicts): {{e.g. `contracts/*`, `fixtures/*`, compose files}}

## 🚀 Start here (new teammate, first 15 minutes)
1. Clone `https://github.com/saliha006/OxHack-2026`. Set `git config user.email` to your GitHub email (commits are credited by author) and
   `git config team.builder <your-name>` (the scripts and the Open board use it). {{Any other one-time git setup}}
2. `bash scripts/sync-context.sh` pulls `CLAUDE.md`, the PRD, your brief and the skills. After that the prompt hook
   re-syncs before every prompt. Codex: run `bash scripts/prompt-check.sh` at the start of each task (AGENTS.md).
3. Read your brief's `▶ Current tasks`, then the 📌 Open board above.
4. {{Access to the deploy target, data and secrets: where each lives. Never in git or chat}}

## 📊 Latest (volatile facts live only here)
- **`main` (2026-10-25 08:10):** Kenar's MCTS + coherent-set merge (PR #1, 07:01; MCTS 8 worlds × 150 ms default, coherent priors opt-in) + live demo search view + MCTS eval pairings. One live demo game on saliha's Windows laptop: won, 0/33 fallbacks, think p99 2.1 s. No MCTS-vs-baseline win rate measured yet (evals running to 09:30).
- **As of 2026-10-25 00:58:** `main` @ `4e88dac` · tests: 148 green, 100% coverage (`uv run pytest --cov=decision`) · smoke: 10/10 games vs RandomPlayer finished unattended, 10 won, think p50 ~65 ms / p99 ~300–700 ms, fallback rate 12.7% (all from the two `belief.py` bugs, Open board) · deploy: none yet
- **Backtest (`derrick` @ `9f86111`):** dropped 2026-10-25 06:41, branch kept as an archive; its numbers stay in Log entries 04:15 and 04:55.
- **Data (Tiger `oxhack-data`, 2026-10-25 03:00):** `battles` 2,506,142 games · `battle_logs` 2,506,142 (uncompressed, 9.2 GB) · `turns` 489,840 rows from 20,000 games (15k train / 5k test) · HP-heuristic test log loss 0.6407, Brier 0.2246 · opponent switch rate 19.2% of acted turns
- **On branches, not merged yet:** `Kenar-coherent-v2` @ `a37709e` (conservative coherent priors, panels unfinished; keep off `main` until after the demo) · `derrick` @ `9f86111` (archive, won't be merged)

---

## Log (newest first)

### 2026-10-25 08:10 — feat — Eval pairings that measure the MCTS bot, plus a 4×300 ms arm — @saliha
- **Where:** `sali` @ `ba1b455` · merged to `main`: yes
- **Did:** `headline` and every `full~*` pairing play the **one-ply** arm (`ARMS["full"]`), not the MCTS bot the demo runs. Adds `mcts-headline` (mcts8 vs SimpleHeuristics, 200), `mcts-foulplay-high` (mcts8 vs Foul Play `fphigh`, 60), `mcts-deeper-foulplay-high` (`mcts4x300` vs `fphigh`, 60) and `mcts-deeper` (`mcts4x300` vs mcts8, 80). `mcts4x300` = 4 worlds × 300 ms, the same 1.2 s as mcts8, so the 3 s budget is untouched (research passes 13A/18: Foul Play `fphigh` searches 1 world 450–700 ms, 3–4× our per-tree depth). Planned counts are smoke-sized: 60 games resolve only ~25-point gaps.
- **Touched:** `bot/eval.py` (`MCTS_ARM_OPTIONS`, `MCTS_PAIRINGS`), `bot/tests/test_mcts_evaluation.py`
- **Brief task:** none
- **⚠️ Conflicts:** @kenar: new arm and pairings sit in your `MCTS_ARM_OPTIONS`/`MCTS_PAIRINGS`; no default or existing pairing changed
- **📨 Needs:** @kenar @derrick @nate: run your eval slice (board row 08:10) and send `runs/eval/<machine>-*.jsonl` to @saliha by 09:30
- **Status:** open

### 2026-10-25 08:00 — feat — Live demo shows what the search is weighing, expecting and guessing — @saliha
- **Where:** `sali` @ `b04c95f` · merged to `main`: yes
- **Did:** `bot.demo live` printed all ~25 MCTS trace fields as truncated JSON each turn. Search turns now print three lines: our top options with pooled support, the opponent reply the search expects, and the guessed item/Tera for their active (counts over the sampled worlds); the raw trace still goes to the `.jsonl`. One live game on saliha's Windows laptop vs SimpleHeuristics: won in 26 turns, 0/33 fallbacks, think p50 1346 ms, p99 2134 ms. Set `PYTHONUTF8=1` so `·` prints in a Windows console.
- **Touched:** `bot/demo.py`, `bot/player.py` (`_label` is now public `label`), `bot/tests/test_demo.py`, `bot/tests/test_player.py`
- **Brief task:** none
- **⚠️ Conflicts:** none (one-ply demo view and trace format unchanged)
- **📨 Needs:** none

### 2026-10-25 06:58 — fix — Reconcile MCTS and coherent-set branches for main review — @kenar
- **Where:** reconciled `Kenar-coherent-sets` candidate, based on `50d9a43` + committed MCTS `aecf217` + main handoff `adc8a0b`; merged to `main`: not yet
- **Did:** Reconciled branch histories and current main without editing evaluation checkouts. Preserved MCTS state/Tera/reliable-belief fixes and optional IV conversion. Included the missing offline policy-metrics helper needed by committed reporting code; corrected the builder contract test to distinguish optional IVs from required fields.
- **Defaults:** broad `data/set_candidates.json` unchanged; MCTS 8 × 150 ms, one native thread, three-second ceiling, reliable beliefs and type-based leads. Coherent priors, move/stat leads and root mixing stay opt-in; no learned policy/value or cycle veto enabled. Uncommitted experiments remain outside the candidate.
- **Validation:** 551 tests passed, one local-chaos-download test skipped; isolated native-worker import/search probe passed. Original 91 bot/decision source files across the three evaluation checkouts were hash-verified unchanged. No new battle evaluation, queue/process changes or Tiger work.
- **Evidence:** `evaluation/integration-mcts-coherent-20261025.json`; detailed docs retained on the reconciled coherent branch and omitted from the separate main PR candidate, per the handoff.
- **Touched:** decision/bot integration, contracts/data compatibility, offline evaluation tools/tests, README and progress history
- **⚠️ Conflicts:** @saliha: bot changes still require your approval under the 06:41 handoff
- **📨 Needs:** @saliha: approve bot edits before main merge; existing evaluation worktrees deliberately retain their original local branch heads
- **Status:** prepared for review; no main merge or experimental promotion

### 2026-10-25 06:41 — decision — Kenar's branch becomes the decision layer; derrick's unmerged work dropped — @derrick
- **Where:** `Kenar-coherent-sets` @ `50d9a43` is the source of truth · `derrick` @ `9f86111` kept as an archive, not merged · merged to `main`: not yet
- **Did:** Withdrew derrick's backtest CLI, `choose_public` and the 1825-cutoff proposal (entries 03:30–04:55). The decision layer going forward is Kenar's work: MCTS over sampled opponent teams as the default (`one_ply` kept for comparisons), the reworked belief, opt-in coherent set priors. Kenar's results are in `docs/mcts-results.md` and `docs/coherent-sets-results.md` on that branch.
- **Touched:** none yet (board and docs only)
- **Brief task:** derrick tasks archived (superseded)
- **⚠️ Conflicts:** @nate: the 1825-cutoff proposal is withdrawn, so the set file needs no rebuild for it. @saliha: once Kenar's branch merges, `bot/` changes too (`eval.py`, `parser.py`, `player.py`, `demo.py`, `smoke.py`); it needs your yes first
- **📨 Needs:** @kenar: merge plan (Open board row). @saliha: PRD NOW update (Open board row)
- **Agreed by:** @derrick, @saliha, @nate, @kenar (whole team, per @derrick)
- **Status:** resolved by @kenar 2026-10-25 07:01 (PR #1 merged to `main`)

### 2026-10-25 06:13 — eval — Coherent OU mixture improves forecasts but not battle screening — @kenar
- **Where:** `Kenar-coherent-sets`, compared with isolated `a8613b9`; not merged into the concurrent policy branch.
- **Outcome:** Fixed 100-test-game retrospective next-reveal loss improved from 4.5569 to 4.2334 and coverage from 73.8% to 76.6%. At matched requested MCTS compute, the optional 50/50 mixture finished 25–35 over all 60 screened games, no draws/voids. Wilson interval 30.1–54.3%; sparse-team bootstrap 25–60%. No demonstrated strength gain; default prior stays unchanged and no confirmation expansion is justified by this screen.
- **Reliability:** All 43,712 worlds usable; zero fallbacks, rejected choices, failed worlds or decisions over three seconds. Final suite 478 passed with one pre-existing 0.6-second fixture failure reproduced exactly in the untouched baseline; 22 focused data/evaluation tests pass. Source/engine/prior identities rechecked after completion.
- **Evidence:** `evaluation/coherent-sets/screening-v2-results.json`, companion game rows, prediction/extraction artifacts and `docs/coherent-sets-results.md`. Team pools are synthetic combinations of known component sets, not an independent competitive-team holdout. Current source snapshots on historical replays are retrospective evidence.
- **Next:** Diagnose/tune role probabilities on development evidence before another prior experiment. Preserve optional importer/extractor and integrate separately with the other chat's accepted engine only after resolving branch overlap.


### 2026-10-25 05:56 — feat — Add opt-in seeded mixing of mature supported move pairs — @kenar
- **Where:** `Kenar-mcts` · merged to `main`: not yet
- **Did:** Added a separately seeded heuristic for exactly two sufficiently supported near-tied legal non-Tera moves, with conservative fixed maturity gates, deterministic fallback and detailed decision traces. Worker replay records the final chosen action; preview, switch and Tera decisions stay deterministic. Tests pass, but native transport/exposure and original/predecessor/opponent-panel comparisons remain pending. The policy remains off by default.
- **Touched:** `decision/root_mixing.py`, Agent opt-in configuration/bookkeeping, fixed policy plan/verification and focused tests
- **Brief task:** user's six-stage handoff → Stage 6 optional candidate committed; evaluation pending
- **⚠️ Conflicts:** none; accepted deterministic policy unchanged
- **📨 Needs:** none; no richer-data requirement
- **Status:** experimental/off; no strength or exploitation-resistance claim

### 2026-10-25 05:56 — fix — Separate cold bootstrap coverage from post-start retention fixtures — @kenar
- **Where:** `Kenar-mcts` · merged to `main`: not yet
- **Did:** Preserved an investigation showing that both frozen baseline/current workers can miss a short fixture's event precondition before any result exists. Post-start fault tests now wait for and requeue the real ready handshake before measuring their unchanged short budget/bounds; explicit cold-bootstrap/fallback coverage remains, and genuine cold crash/history tests use the production ceiling with exact assertions. No production Agent/SearchWorker/deadline behavior changed, and no sole CPU cause or new retention defect was established.
- **Touched:** `tests/test_search.py`, preserved deadline investigation artifact and logs
- **Brief task:** user's six-stage handoff → Stage 6 broader verification gate repaired
- **⚠️ Conflicts:** none; running evaluation sources unchanged
- **📨 Needs:** none
- **Status:** broad and full regression selections pass; candidate live smoke still pending

### 2026-10-25 05:51 — docs — Publish two full screening comparisons and fresh diagnostics — @kenar
- **Where:** `Kenar-mcts` · merged to `main`: not yet
- **Did:** Published complete initial-state-fix and reliable-belief-versus-original screens with intervals, reliability, resource and native-discard measurements. Initial Stage 1 is promising but inconclusive, so its already frozen full historical confirmation is queued; it predates the Tera repair. Stage 2's incremental comparison remains in progress. Fixed pre-revelation ablations on the completed Stage 1 histories show no predictive benefit, and fresh win/loss-controlled signatures remain investigation leads rather than guard justifications.
- **Touched:** complete screening/game artifacts, fresh belief scores/loss audit, experiment index and staged documentation
- **Brief task:** user's six-stage handoff → first controlled screens and fresh diagnostics published; remaining comparisons/stages pending
- **⚠️ Conflicts:** none; measured source identities and old-source limits remain explicit
- **📨 Needs:** none; no new data access or scoring-set tuning
- **Status:** Stage 1 promising but inconclusive; Stage 2 contribution pending; no demonstrated strength improvement

### 2026-10-25 05:38 — feat — Isolated coherent-set prior and public-reveal extraction — @kenar
- **Where:** `Kenar-coherent-sets`, separate checkout based on `a8613b9`; not merged to main or the active MCTS-policy branch.
- **Did:** Imported pinned Showdown OU roles as validated coherent candidates, preserved IV overrides, retained broad usage fallback in an optional 50/50 mixture, and added chronological public-revelation extraction with conservative item/copy/identity exclusions. Existing default prior is unchanged. The comparison runner freezes independent prior files for each arm.
- **Measured so far:** Bounded 200-game Tiger sample; retrospective 100-game test diagnostic favors the mixture on next-reveal loss/coverage. This is not a strength result. Frozen source/priors and side/team-balanced game manifests are under `evaluation/coherent-sets/`; measured status and limits stay current in `docs/coherent-sets-results.md`.
- **Touched:** `data/pipeline/import_curated_sets.py`, `data/pipeline/reveal_evidence.py`, `data/pipeline/sample_replay_logs.py`, optional-IV candidate compatibility and isolated evaluation support. No writes to the original active checkout.
- **Coordination:** Data-independent MCTS work continues separately; reconcile IV compatibility and evaluator prior-path support at integration. No new roster-conditioned learned prior or joint-team model yet.

### 2026-10-25 05:36 — docs — Reject an unsupported historical switch-cycle guard — @kenar
- **Where:** `Kenar-mcts` · merged to `main`: not yet
- **Did:** Audited three historical switch cycles and the one eligible near-support case with all recorded worlds, conditional successors, repeat searches and controlled counterexamples. Staying and switching trade different remaining resources; neither the observed faint nor a simple HP diagnostic proves the search choice was wrong. Rejected the proposed guard before adding runtime behavior, retaining its failed-bootstrap and successful-audit artifacts.
- **Touched:** strategic-guard development audit plan/results, offline successor/counterexample tooling/tests and staged documentation
- **Brief task:** user's six-stage handoff → historical Stage 5 hypothesis assessed; fresh loss mining remains pending
- **⚠️ Conflicts:** none; no production policy, native checks or deadline overhead added
- **📨 Needs:** none; continue fresh diagnostics from the preceding controlled screens
- **Status:** hypothesis rejected; no guard enabled and no strength gain claimed

### 2026-10-25 05:32 — docs — Verify the actual native-worker import boundary and rebased lead transport — @kenar
- **Where:** `Kenar-mcts` · merged to `main`: not yet
- **Did:** Independently recorded the spawned native grandchild's loaded decision modules and engine extension for original/corrected/lead snapshots; the probe delegates unchanged frozen workers. Rebased optional-lead transport passed, and four fresh fixed-allocation screening plans are frozen with matched side/team assignments. Preserved the historical scorer and froze a separate corrected runtime for future predeclared fresh scoring. These are integrity/integration gates and plans, not strength results.
- **Touched:** native-import provenance, rebased lead smoke/results, fixed-allocation manifests, scoring runtime and staged documentation
- **Brief task:** user's six-stage handoff → evaluation integrity and controlled comparisons prepared
- **⚠️ Conflicts:** none; no active source/schedule mutation
- **📨 Needs:** none; Tiger pause unchanged
- **Status:** integrity/smoke complete; queued game comparisons, fresh scoring and later-stage audits pending

### 2026-10-25 05:29 — docs — Repeat equal-effort allocation measurements after the Tera correction — @kenar
- **Where:** `Kenar-mcts` · merged to `main`: not yet
- **Did:** Repeated the exact development positions/order/seeds/world samples on corrected state. The unsupported native Tera roots disappeared while legitimate unspent-Tera options remained. All selected position actions agreed across allocations; native disagreement and real compute differences are still reported. Preserved both versions and kept the default eight-world allocation. The Tera correction also passed transport smoke and is accepted for correctness, with separate strength comparisons pending.
- **Touched:** allocation v2 plan/results/integrity, follow-up smoke/results/index and live documentation
- **Brief task:** user's six-stage handoff → Stage 4 development measurement complete; fixed-budget games and later stages pending
- **⚠️ Conflicts:** none; active evaluations retain frozen source and original scope
- **📨 Needs:** none; Tiger pause and deferred data roadmap unchanged
- **Status:** development evidence only; no allocation/adaptivity/guard promotion or strength claim

### 2026-10-25 05:24 — fix — Preserve irreversible Tera history when a fainted request omits it — @kenar
- **Where:** `Kenar-mcts` · merged to `main`: not yet
- **Did:** Native own-team reconstruction now retains a current request's transformed flag or the confirmed transformed identity in public history. Added two actual historical request fixtures, regression tests and a matched native before/after probe. This corrects the newly reproduced search-resource defect without inventing a transformed slot from side-level resource use. Formal acceptance awaits smoke, and strength comparisons remain separate.
- **Touched:** `decision/state.py`, captured request fixture/tests, adapter audit and Tera probe plan/results
- **Brief task:** user's six-stage handoff → Stage 1 follow-up correction committed; evaluation pending
- **⚠️ Conflicts:** none; existing running studies retain their original source and scope
- **📨 Needs:** none; original data roadmap and Tiger pause unchanged
- **Status:** correctness regression gates pass; transport smoke and controlled comparisons pending
- **Update, 2026-10-25 05:29:** transport smoke passed and the correction was accepted for correctness; controlled strength comparisons remain pending. The earlier Status records the state at commit time.

### 2026-10-25 05:21 — docs — Allocation diagnostics expose an omitted fainted-Tera transition — @kenar
- **Where:** `Kenar-mcts` · merged to `main`: not yet
- **Did:** Completed the frozen equal-requested-effort development measurement and audited mapping discards separately from server rejections. A historical request can omit a fainted Pokémon's irreversible Tera state despite public history retaining it, allowing native search to consider a second Tera before final legality filtering. This requires a narrow state correction before allocation/lead policy conclusions; earlier fixtures did not cover the omitted request flag. Preserved the affected measurements with this limitation and verified that the installed native API exposes no tree-continuation handle.
- **Touched:** allocation development plan/results/integrity/API audit and offline measurement tooling; state repair is in progress
- **Brief task:** user's six-stage handoff → Stage 4 development diagnostics; Stage 1 follow-up defect reproduced
- **⚠️ Conflicts:** none; active evaluations retain their frozen source and original scope
- **📨 Needs:** none; no Tiger/data dependency
- **Status:** diagnostic measurement complete; correction and fresh comparisons pending, allocation/adaptivity unchanged

### 2026-10-25 05:15 — feat — Add optional preview scoring from supplied moves and stats — @kenar
- **Where:** `Kenar-mcts` · merged to `main`: not yet
- **Did:** Added an explicit opening heuristic using our actual request moves/stats and public opposing priors, with traced damage, speed/priority, fragility and hazard/pivot/Taunt components. Preserved the type-only default and added a fixed-lead test option. The model is approximate and remains off pending controlled game evidence; a higher heuristic score is not a strength result.
- **Touched:** `decision/lead_model.py`, Agent preview configuration, focused tests, development benchmark and staged documentation
- **Brief task:** user's six-stage handoff → Stage 3 optional candidate implemented; evaluation pending
- **⚠️ Conflicts:** none; changes remain on the implementation branch for review
- **📨 Needs:** none; current priors reused and opponent private team files are not model inputs
- **Status:** experimental/off by default; strength unknown

### 2026-10-25 05:10 — fix — Guard uncertain belief inference while preserving confirmed facts — @kenar
- **Where:** `Kenar-mcts` · merged to `main`: not yet
- **Did:** Separate direct revelations, guarded inferred item rules and soft replay. Reproduced called-move, incomplete-turn, changed-hazard and old-item-period defects against the frozen baseline; reliable mode corrects those cases while legacy mode preserves the comparison. Added pre-revelation scoring ablations and leakage checks. Reliable mode is enabled for correctness; full original/predecessor strength comparisons remain in progress.
- **Touched:** `decision/belief.py`, `decision/agent.py`, `decision/search.py`, reliability/scorer tests and evaluation scoring plans/tooling
- **Brief task:** user's six-stage handoff → Stage 2 correctness accepted; game and diagnostic comparisons pending
- **⚠️ Conflicts:** none; changes remain on the implementation branch for review
- **📨 Needs:** none; existing local priors retained, Tiger paused
- **Status:** correctness improved in reproduced cases; strength unknown

### 2026-10-25 05:04 — fix — Remember supported battle state through switches and continuation requests — @kenar
- **Where:** `Kenar-mcts` · merged to `main`: not yet
- **Did:** Retain own request PP and max HP by Pokémon/move identity; label observed PP spend as estimated; reconstruct observed Protect streaks and keep publicly visible extended effects present. Added partial-turn/source metadata without inventing a hidden queued opponent action. Reproduced the targeted defects and added controlled Showdown mechanics fixtures. Correctness improved in those fixtures; playing-strength comparison is still in progress.
- **Touched:** `bot/parser.py`, `bot/player.py`, `decision/state.py`, `decision/adapter.py`, optional BattleState fields/docs, adapter audit and focused fixtures/tests
- **Brief task:** user's six-stage handoff → Stage 1 correctness work committed; controlled comparison pending
- **⚠️ Conflicts:** none; changes remain on the implementation branch for review
- **📨 Needs:** none; Tiger remains paused and its unrelated files were excluded
- **Status:** focused correctness work committed; strength unknown

### 2026-10-25 04:58 — scope — Six data-independent MCTS stages opened with a frozen comparison anchor — @kenar
- **Where:** `Kenar-mcts` · merged to `main`: not yet
- **Did:** User requested state reconstruction, belief reliability, leads, search allocation, evidence-backed guards and optional near-tie mixing in that order. Opened a persistent goal and a live record in `docs/mcts-improvement-log.md`; original anchor is `2c02fc8daa84f047ea2bddd7d0f36f6463fff1e2`. Each change requires original/predecessor comparisons and a recorded decision. No new implementation or strength result is claimed by this scope entry.
- **Touched:** improvement documentation; compact experiment records will live in `evaluation/mcts-improvements/`
- **Brief task:** user's six-stage handoff → started
- **⚠️ Conflicts:** none; requested work stays on the implementation branch for review
- **📨 Needs:** none for this scope; richer sets, Nate's A6/team priors and learned evaluation remain deferred until new data/scope is supplied. Tiger download/training remains paused and its pending files are preserved
- **Agreed by:** user, 25 October 2026
- **Status:** scope recorded; implementation/evaluation in progress

### 2026-10-25 04:55 — decision — Drop the 1825 cutoff from the set priors (waits on @nate) — @derrick
- **Where:** no branch change yet; a test build at `runs/priors/set_candidates-cutoff0.json` (local: Nate's builder, unchanged, on Smogon's 2026-09 `gen9ou-0`)
- **Did:** Found why so many species were missing: the Tiger games are median Elo 1322 (1.7% of players 1825+, 0.8% of games with both), while the set file is Smogon's 1825 band, which lists 243 species where the all-ratings file lists 458 (same battles). The 1825 choice was @derrick's own on 2026-10-24 (`02-set-priors.md`), with no reason recorded. Backtest, same 200 test games and seed: 1825 file → 125 played, 29.9% same as p1 (95% 27.6–32.4%); no cutoff → 195 played, 31.5% (29.6–33.5%); on the 125 games both played, 29.9% → 30.8%, so common species didn't get worse priors for these games. The 5 still skipped are unevolved Pokémon and cosmetic formes (Florges colours, Gastrodon-East, Minior colours). Switching is unchanged: the strat switches on 4% of turns, the players on 24%.
- **Decided:** the set priors drop the rating cutoff and use the same month's all-ratings usage (@derrick). Needs @nate's yes: it's his file, and the contract's source line changes
- **Touched:** none yet
- **⚠️ Conflicts:** @nate: rebuild `data/set_candidates.json` from `gen9ou-0` (Open board row). @saliha: the PRD's priors line changes once Nate agrees (Open board row)
- **📨 Needs:** @nate: yes/no
- **Status:** withdrawn by @derrick 2026-10-25 06:41 (Kenar's branch is the decision layer's source of truth)

### 2026-10-25 04:30 — decision — MCTS becomes development default by user request; assess larger replay corpus — @kenar
- **Where:** `Kenar-mcts` · merged to `main`: not yet
- **Did:** User selected MCTS as the direction to improve. `Agent`, demo and smoke default to eight MCTS worlds; historical one-ply evaluation arms now select their backend explicitly. This promotion records the user's choice, not a new statistically established strength result. Assessed HolidayOugi's replay corpus against existing project ingest/turn contracts; source revision and recommended inference/prediction experiments are in `docs/holidayougi-assessment.md`. No large download or new dataset training was performed.
- **Touched:** decision default, bot CLI defaults, pinned comparison arms, regression fixtures and current documentation
- **Brief task:** user's follow-up → default promotion and dataset assessment
- **⚠️ Conflicts:** retained comparisons explicitly use one-ply, so switching the application default cannot silently change their opponent
- **📨 Needs:** reuse the team's existing turn export for the next data experiment; current assessment did not verify Tiger access
- **Agreed by:** user, 25 October 2026
- **Status:** verified — 379 decision/bot tests passed; default CLI live smoke won in 15 turns with 0/18 fallbacks, 136/136 native worlds usable and no rejected choices. `evaluation/mcts-default-smoke-20261025.json` records the exact no-backend-flag command.

### 2026-10-25 04:15 — feat — Backtest CLI on Tiger games, and its first results — @derrick
- **Where:** `derrick` @ `9f86111` · merged to `main`: not yet
- **Did:** `uv run python -m backtest.engine` plays a seeded sample of Tiger games turn by turn through `choose_public` and checks each choice against what p1 played. It skips games with a species missing from the set file (counted per species), records a strat error for its turn and goes on, and writes one JSONL per run plus a summary to `runs/backtest/`. No frontend. First run: 200 test games sampled (seed 2026): 125 played, 75 skipped for a species missing from the set file. Same move or switch as p1 on 29.9% of 3,003 scorable turns (95% by game: 27.6–32.4%), 21.4% counting Tera too; 38% when p1 attacked, 3% when p1 switched (the strat switches on 4% of turns, the players on 24%). Think p50 163 ms, p99 475 ms, max 954 ms on the 3 s budget. 1 error in 3,310 turns: a NaN expected value crashes `select`. That crash is in the shared selector, so live games can hit it too and fall back to the first legal option; the NaN comes from `simulate` or `value`, not traced yet. 172 tests green.
- **Decided:** (1) games with a species missing from the set file are skipped and counted; (2) the backtest is a backend with a CLI, no frontend or dashboard. Both @derrick.
- **Touched:** `backtest/engine.py` (new), `decision/adapter.py` (`replay_action`), `tests/test_engine.py`, `tests/test_adapter.py`
- **⚠️ Conflicts:** none: new files, plus one new function in the adapter
- **📨 Needs:** @saliha: decisions (1)–(2) into PRD NOW (Open board row)
- **Status:** withdrawn by @derrick 2026-10-25 06:41 (Kenar's branch is the decision layer's source of truth)

### 2026-10-25 04:03 — feat — Alternative deadline-isolated MCTS and separate prediction evaluation — @kenar
- **Where:** `Kenar-mcts` · base `main` @ `81c8f1c` · merged to `main`: not yet
- **Did:** Added stock Gen9/Tera MCTS behind `backend="mcts"`, preserving the one-ply default. One persistent worker contains belief replay, preparation and native search; completed worlds stream before pooling legal visit support. Fixed revelation-preserving belief recovery, full-team sampling, state legality/counters, trace retention and evaluation lifecycle races. The original requested plan is in `docs/mcts-plan.md`.
- **Measured:** Clean side-swapped integration: 1–1 over two games, 139/139 worlds usable, zero fallbacks/rejections. The frozen-source 24-game pilot completed with 7,863/7,863 worlds usable and zero observed MCTS fallbacks, rejected choices or decisions over three seconds. MCTS8 versus one-ply was 3–1 (95% interval 30.1–95.4%); this is not a strength claim. Public prediction experiment: 96 eligible replays, chronological 67/14/15 battle split; calibrated logistic test log loss 0.6600 versus HP-only 0.6348, so prediction stays experimental and outside search.
- **Touched:** `decision/`, `bot/`, optional BattleState fields, tests, `prediction/`, evaluation configs/artifacts and `docs/` (including a live walkthrough). Real OU priors reused unchanged; no learned reranker or extra opponent weighting added.
- **Brief task:** user's attached MCTS plan → baseline implementation, prediction tools, bounded comparisons and live results walkthrough done; larger confirmatory evaluation remains configured
- **⚠️ Conflicts:** Decision/bot/contract changes overlap Derrick/Saliha's paths; all changes remain on this branch for review. Default backend remains `one_ply`.
- **📨 Needs:** none for implementation; confirmatory strength evaluation needs more held-out teams/games than the bounded pilot
- **Status:** implementation and bounded pilot complete on branch; larger confirmatory study not run

### 2026-10-25 03:58 — feat — The strat layer can play a Tiger turn without a request — @derrick
- **Where:** `derrick` @ `9c42b11` · merged to `main`: not yet
- **Did:** `Agent.choose_public(battle, our_sets)` scores a replay turn from the `BattleState` alone. Our side is built the way the opponent's already was (what's been seen plus one guessed set per Pokémon, `build_public_state`), and our options are listed the same way (`public_actions`). `sets_from_game` makes our guesses once per game. `choose(request, battle)` is unchanged. On the first 10 Tiger games with the real set file: p50 117 ms, p99 462 ms on a 1 s budget; the same move or switch as p1 on 29 of 87 scorable turns (33%). 162 tests green, `decision/` at 100%.
- **Decided:** (1) a request-free entry point next to `choose`, not a fake request and not a new contract; (2) our side takes moves and Tera type from the whole game, and items and abilities as each turn shows them (items change hands). Both @derrick.
- **Touched:** `decision/adapter.py`, `decision/agent.py`, `decision/belief.py`, `decision/opponent.py`, `tests/`
- **⚠️ Conflicts:** @saliha: nothing changes for the bot: `choose` and `opp_actions` behave as before; the private `_opponent` in `adapter.py` is now `_guessed_side`/`_guessed`. @nate: species missing from the set file (Open board row)
- **📨 Needs:** @saliha: decisions (1)–(2) into PRD NOW (Open board row)
- **Status:** withdrawn by @derrick 2026-10-25 06:41 (Kenar's branch is the decision layer's source of truth)

### 2026-10-25 03:30 — decision — Backtest engine started: Tiger's turns on disk, and four decisions on how it takes data — @derrick
- **Where:** `derrick` @ `78453b9` · merged to `main`: not yet
- **Did:** `backtest/tiger.py` copies Tiger `turns` verbatim to `runs/tiger/turns.jsonl` (git-ignored; 489,840 rows, 3.05 GB) with `uv run --group data --env-file .env python -m backtest.tiger`. The pull takes ~5–7 min because the venue network caps at ~9–10 MB/s, shared by everything (measured: a second Tiger stream and a non-Tiger download both split it; client CPU 5%, server work ~60 s). Reading the file back takes ~20 s. 152 tests green on `derrick`.
- **Decided:** (1) the engine never modifies or substitutes data: it only ingests it and pipes it to the strat layer; (2) `psycopg[binary]` (3.3.6) in a `data` dependency group, so the default install doesn't pull it in; (3) Tiger is pulled once to a local file, not streamed on every run; (4) Tiger rows feed both predictions and move choice, with our side's request built from set candidates (where and how is still open). All @derrick's.
- **Touched:** `backtest/` (new), `tests/test_tiger.py`, `pyproject.toml`, `uv.lock`
- **⚠️ Conflicts:** @nate: the dump reads every column of `turns` as it is today; say before a rebuild changes them. @saliha: none yet (the engine will read `bot.parser`, without changing it)
- **📨 Needs:** @saliha: decisions (1)–(4) into PRD NOW (Open board row)
- **Agreed by:** @derrick (owner per PRD Pending); the team hears via the 🔀 row To @all
- **Status:** withdrawn by @derrick 2026-10-25 06:41 (Kenar's branch is the decision layer's source of truth)

### 2026-10-25 03:00 — feat — Set file with forme aliases, all 2.5M replays in Tiger, and a 20k-game turn table — @nate
- **Where:** `nate-data` @ `ad5ba10` · merged to `main`: yes (fast-forward)
- **Did:** (1) `data/set_candidates.json` from chaos 2026-09 gen9ou-1825: 243 species, ≤30 sets each, every item keeps its usage share, Choice items keep status moves (only Assault Vest bars them), plus 78 forme aliases from Showdown's pokedex. (2) Data frozen at 2026-10-24 12:00 BST. All HolidayOugi gen9ou replays (2,506,142 games, 2022-11 → 2026-10-05) cleaned to local Parquet with DuckDB and loaded into Tiger Cloud (TimescaleDB, on the MLH credits): `battles` (players, pre-game Elo from `|player|`, winner, turns, rated, teams, leads) and `battle_logs`; read-only logins for derrick and saliha, sent privately. (3) `turns`: one row per turn from saliha's Parser (identical to `states_from_log`), 20,000 games, 15k train (2025-01 → 2026-05-18) and 5k test (2026-05-19 →); no game in two splits, 1,909 test games share no player or team with train; spec in `contracts/turns.md`. (4) Answers: derrick's contract row, yes to the shape and to `data/set_candidates.json`; pass 10 step 4, derrick trains the model from `turns`, and the measured switch rate is 19.2%; pass 9, tasks 1–2 done, storage is local Parquet + DuckDB with Tiger for sharing, the extract comes from HolidayOugi (raw names, to 2026-10-05) instead of Metamon.
- **Touched:** `data/pipeline/*`, `data/tests/*`, `data/set_candidates.json`, `contracts/turns.md` (new), `.gitignore` (`data/raw/`, `data/clean/`)
- **Brief task:** 1 ✅ (after the 01:00 target) · 2 ✅ (snapshot saved locally) · 4 🟡 (20k extract + leakage check; no validation split or learning curve yet) · 3 ⬜ (team pool not started)
- **⚠️ Conflicts:** @derrick: your model's data is Tiger `turns` (`contracts/turns.md`), plus the Choice-item rule, the missing-species KeyError and the A1 wording (Open board row). @saliha: real priors are on `main` and the forme aliases answer your row from the data side (Open board row)
- **📨 Needs:** none
- **Status:** open (the ⚠️ rows to derrick and saliha)

### 2026-10-25 02:19 — chore — Branch tidy-up: Nate's branch renamed to nate-data; merged branches deleted — @saliha
- **Where:** GitHub branches · `context` @ `ee0fb62` · merged to `main`: n/a
- **Did:** Renamed `Data-stuff-(Nate)` to `nate-data` (pushed the same commit under the new name, checked it matched, then deleted the old name). Deleted saliha's merged feature branches (`eval-blind`, `eval-ladder`, `eval-foulplay`, `demo-mode`); `derrick-main` was already gone. saliha's work stays on `sali` from now on. Added derrick's belief-floor line to PRD → NOW (his wording) and closed his row; Nate's brief names the new branch.
- **Touched:** branches only; `builder-files/builder-file-nate.md` line 2, `OxHack-2026-PRD.md` NOW (one added line)
- **Brief task:** none
- **⚠️ Conflicts:** @nate: your branch's upstream is gone until you re-point it (Open board row)
- **📨 Needs:** none

### 2026-10-25 00:58 — feat — Type-matchup lead is on main; all of derrick's code is now on main — @derrick
- **Where:** `derrick` @ `a50936e` · merged to `main`: yes (cherry-picked as `4e88dac`; `derrick` and `main` share no history, so a merge was refused and would have brought the old doc commits along)
- **Did:** Team preview now sends the lead with the best average STAB type edge against their six (`decision/lead.py`), as PRD → NOW records. `derrick` stops tracking the shared docs (main's ignore rules plus `design/`), so nothing doc-shaped can reach `main` from it. 148 tests, 100% coverage.
- **Touched:** `decision/lead.py`, `decision/data/typechart.json`, `decision/agent.py`, `decision/actions.py`, `tests/test_lead.py`, `tests/test_agent.py`
- **Brief task:** feature 11 (lead) → ✅ done
- **⚠️ Conflicts:** @saliha: team preview no longer sends `team 123456`; the lead depends on their six, so eval/demo runs may lead differently than before
- **📨 Needs:** none

### 2026-10-25 00:46 — fix — Belief no longer crashes on Ruination or an empty belief; contradicted sets are floored — @derrick
- **Where:** `derrick` @ `e683a12`, `5a2b9d8`, `4e9bcf1` · merged to `main`: yes (cherry-picked: `b371346`, `03a3203`, `4e9bcf1`; the rest of `derrick` waits until its tracked docs are removed)
- **Did:** Fixed saliha's three belief reports. (1) Fixed-damage moves like Ruination return one damage value; read it as both max and crit. (2) When every set and the usage rebuild fail the reveal filter, keep the old guesses at a floor instead of an empty belief. A set that fails the speed/damage replay now keeps 3% of its weight (`FLOOR = 0.03`) instead of zero, so one misread line can't wipe out the true set. (3) Data files read as UTF-8 for Windows. 148 tests on `derrick`, 144 on `main`, 100% coverage.
- **Touched:** `decision/belief.py`, `decision/state.py`, `decision/opponent.py`, `tests/test_belief.py`, `tests/test_reweight.py`
- **Brief task:** derrick task 2 (belief floor) → ✅ done
- **⚠️ Conflicts:** @saliha: belief now never empties, so the smoke run's fallback-every-turn from these two bugs should stop; rerun when convenient. One behaviour change: if no set passes the replay, belief keeps them at their old weights instead of rebuilding from usage
- **📨 Needs:** @saliha: the PRD → NOW line (board row)
- **Status:** open

### 2026-10-25 00:32 — docs — Research pass 10: a decision-layer plan for derrick; A6 line added to PRD NOW — @saliha
- **Where:** `context` @ `4f5e5c7` (`design-decision/strategy-research-pass10.md`, PRD NOW) · merged to `main`: n/a
- **Did:** saliha asked for specialist research on the move-choice problem (our move × their move × hidden set × dice, collapsed to a matrix per turn). Four agents (search, belief, opponent model + value, speed) and a cross-check under the research protocol. Verdict: a one-ply expected-value agent with a learned leaf. Fix the belief crashes first, then a calibrated logistic value behind a flag; depth-2, process pool and LP are default-off stretch. Measured: poke-engine never releases the GIL (use processes); Python ~1.1–1.6 ms per cell; on our test position one-ply dominance drops Swords Dance and the top-3 EVs are within 0.006. Also added derrick's A6 decision to PRD → NOW (closes his row).
- **Touched:** `design-decision/strategy-research-pass10.md`, PRD NOW
- **Brief task:** none
- **⚠️ Conflicts:** @derrick: proposal for your layer (Open board); @nate: proposed training hand-over
- **📨 Needs:** @derrick: accept or change the plan; @nate: yes/no on step 4
- **Status:** open (derrick's plan) · nate's part resolved by @nate 2026-10-25 03:00

### 2026-10-25 00:30 — decision — Team-conditioned set priors (A6): yes, with a stepped fallback — @derrick
- **Where:** `context` (`design-decision/predictions.md`) · merged to `main`: n/a
- **Did:** Said yes to nate's proposal: starting set guesses for each opponent Pokémon come from past games whose teams match theirs, which beats the general usage file. Fallback: require all 5 teammates to match, then one fewer at a time until at least N games match; at 0 it's the general priors.
- **Touched:** `design-decision/predictions.md` (A6)
- **Brief task:** none
- **⚠️ Conflicts:** @nate: you build it (data layer), after the demo. Belief reads it at team preview, so the hand-off is a function of their six; agree the shape with @derrick before building
- **📨 Needs:** @saliha: the PRD → NOW line (board row) · @nate: pick N
- **Agreed by:** @derrick (decision-layer choices are his, PRD → NOW); proposed by @nate
- **Status:** open

### 2026-10-24 23:49 — feat — Demo mode: live battle streamed turn by turn, or replayed offline — @saliha
- **Where:** `demo-mode` → `main` @ `ecbb278` · merged to `main`: yes
- **Did:** `uv run python -m bot.demo live --priors-from-teams` starts a battle vs SimpleHeuristics, prints the URL to watch it and streams each turn: the choice in words ("Icicle Crash + Tera", "switch to Zapdos"), both actives with HP and Pokémon left, think time, and any field the agent adds (shown generically, so a new prediction field needs no demo change). `--pace` slows our side so judges can follow. `bot.demo replay runs/<battle>.jsonl` replays a saved game offline. Two live test games ran: one won in 44 turns.
- **Touched:** `bot/demo.py`, `bot/player.py` (trace label + per-decision callback), `bot/tests/test_demo.py`, `bot/tests/test_player.py`
- **Brief task:** saliha task 7 ✅
- **⚠️ Conflicts:** @derrick: anything you put in `agent.last_trace` shows up in the demo stream as `key: value`; no shape is assumed
- **📨 Needs:** none

### 2026-10-24 23:10 — feat — Foul Play tops the eval ladder; full eval run started — @saliha
- **Where:** `eval-foulplay` → `main` @ `61b10cc` · merged to `main`: yes
- **Did:** Foul Play (pmariglia, same `poke-engine` 0.0.48 build) runs as three uneven search-time levels (40–80, 150–260, 450–700 ms) in its own venv inside a git-ignored `foul-play/`. Each shard feeds it a team list in its own game order so games stay same-team; it downloads real Smogon stats, so it needs internet once. Measured: Foul Play at 200 ms beat our agent in 50 turns. Turn-0 games are now void (Foul Play crashes on Keldeo-Resolute too, so team 7 left the pool). `*.env` is ignored now: `saliha-tiger.env` was not covered by `.env*`. Full run: 27 pairings, 1,750 games, 5 shards, stand-in priors from the 10 pool teams.
- **Touched:** `bot/eval.py`, `bot/tests/test_eval.py`, `.gitignore`, `bot/teams/standin/`
- **Brief task:** saliha task 5 🟡 (full run in progress)
- **⚠️ Conflicts:** @nate: your `.env` file must end in `.env` or start with `.env` to stay ignored
- **📨 Needs:** none new

### 2026-10-24 22:53 — feat — Elo ladder in the eval — @saliha
- **Where:** `eval-ladder` → `main` @ `f36a4c7` · merged to `main`: yes
- **Did:** saliha picked option B (our bots + Foul Play on top). This part adds the levels we already have: SimpleHeuristics mixed with random moves at uneven rates (83/58/31/12%) and MaxBasePower at 46%, so steps aren't even and levels overlap; our agent variants are levels too. The agent plays every level (40 games), neighbouring levels play each other (30), 1,540 games in all. `report` fits Bradley-Terry ratings on the Elo scale (Random = 1000) with bootstrap intervals and lists the levels ±1–3 places around the agent. This is an internal ladder Elo, not a Showdown ladder Elo. Foul Play levels come next.
- **Touched:** `bot/eval.py`, `bot/tests/test_eval.py`
- **Brief task:** saliha task 5 🟡
- **⚠️ Conflicts:** none
- **📨 Needs:** none new

### 2026-10-24 22:49 — feat — Eval is blind and varied — @saliha
- **Where:** `eval-blind` → `main` @ `10f123a` · merged to `main`: yes
- **Did:** One seeded shuffled schedule across every pairing; opponents get random account names and a right-skewed random think time before each move (median 0.25 s, capped at 3 s); each game draws a random team from the pool for both sides. Stand-in priors merge every set across 11 validated Metamon `competitive/gen9ou` teams (5 of 16 fail now Tera Blast is banned), so belief faces real uncertainty until `data/set_candidates.json` lands. Fixed: trailing blank lines in team files made poke-env parse an empty 7th Pokémon. Results now live in `runs/eval/<machine>-<shard>.jsonl` with the battle tag.
- **Touched:** `bot/eval.py`, `bot/smoke.py`, `bot/teams/standin/`, `bot/tests/test_eval.py`, `bot/tests/test_smoke.py`
- **Brief task:** saliha task 5 🟡
- **⚠️ Conflicts:** @derrick @nate: forme mismatch (`keldeoresolute` vs `keldeo`), Open board
- **📨 Needs:** an agreed forme rule from @derrick and @nate
- **Status:** open

### 2026-10-24 22:33 — feat — Eval harness: agent ablations vs baselines and each other — @saliha
- **Where:** `sali` @ `fa8f4ed` · merged to `main`: yes (fast-forward)
- **Did:** `bot/eval.py`, saliha's pick of an improved prediction-centred design: headline full agent vs SimpleHeuristics (300); a data ladder: full vs frozen-prior belief (200), frozen prior vs flat prior (200); 5 scenarios vs 1 (200); MaxBasePower 100, Random 30. Same team on both sides, sides alternate, so results measure play, not teams. The think-time curve was dropped: think p50 is ~65 ms, so the budget never binds. Shards are separate processes appending one line per game; reruns skip finished games; `report` merges every machine's files with Wilson + team-bootstrap intervals. Ablations wrap `Agent`/`Belief` in `bot/`, so `decision/` is untouched. 2+2-game smoke passed.
- **Touched:** `bot/eval.py`, `bot/player.py` (summary records our side), `bot/tests/test_eval.py`
- **Brief task:** saliha task 5 🟡 (built; final run waits on the team pool, real priors and the belief fixes)
- **⚠️ Conflicts:** @derrick: the ablations subclass `Belief` (`FrozenBelief`, `FlatBelief`) and pre-set `Agent.belief`; renaming `candidates`, `previous` or the `belief` attribute breaks them. @nate: `--teams` takes a folder of team files: one Showdown-export team per file, nothing else in it
- **📨 Needs:** none new
- **Status:** open

### 2026-10-24 21:47 — feat — Bot plays live Showdown games through the decision layer — @saliha
- **Where:** `sali` @ `d8bf19f` · merged to `main`: yes (fast-forward)
- **Did:** Rust + uv installed so `poke-engine` builds on saliha's machine. `bot/player.py`: a poke-env player feeds each whole message to our parser before poke-env answers (measured on the local server: the log always lands before the request, incl. forced switches), calls `Agent.choose`, and writes `runs/<battle>.log`, `.jsonl` trace and `.decision.log`. Rejected choices retry with the first legal option, then `default`; Showdown's timer ends any hung battle. `bot/smoke.py` runs N games vs RandomPlayer: 10/10 finished, 10 won. Stand-in team `bot/teams/standin-gen9ou.txt` (Metamon `competitive/gen9ou` team 5; 5 of those 16 teams fail validation now that Tera Blast is banned).
- **Touched:** `bot/player.py`, `bot/smoke.py`, `bot/teams/`, `bot/tests/test_player.py`, `bot/tests/test_smoke.py`, `pyproject.toml`, `uv.lock`
- **Brief task:** saliha tasks 1, 2, 3 ✅; task 4 (trace) 🟡: written every turn, waits on `agent.last_trace` for top options and win probability
- **⚠️ Conflicts:** @derrick: `poke-env` added to your `pyproject.toml`; two `belief.py` bugs found live (Open board). @nate: the example priors cover 2 species, so the agent falls back on every turn until `data/set_candidates.json` exists; smoke uses `--priors-from-team` to test the plumbing meanwhile
- **📨 Needs:** @nate: set candidates (your task 1) unblock real play
- **Status:** open

### 2026-10-24 21:15 — scope — Pass 9 build plan: every brief reordered, PRD filled — @saliha
- **Where:** `context` @ `9de3c7f` (PRD v3, all three briefs, `CLAUDE.md` @ `d57de97`) · merged to `main`: n/a (docs branch)
- **Did:** Two research agents (decision/prediction; bot/data/eval/demo) and a critic set a recommended design and an order for every feature; all three briefs now follow it and PRD §1–§22 are filled. Biggest changes: the bot runs one blocking `Agent` per shard process (the `Agent` is stateful), the eval headline is a team-neutral 300-game leg vs SimpleHeuristics, the value model goes logistic first, the LP is flagged and default off, and the live client needs internet (record a fallback video). `CLAUDE.md` §2c: builders may extend their own area after their Claude asks whether the team knows.
- **Touched:** PRD, `builder-file-saliha/derrick/nate.md`, `CLAUDE.md`
- **Brief task:** none (plan change)
- **⚠️ Conflicts:** @derrick, @nate: your task lists are renumbered and reordered (old tasks archived at the bottom of each brief, nothing deleted)
- **📨 Needs:** @derrick: three dependency OKs; yes/no on the hand-overs. @nate: confirm your branch; set candidates first
- **Agreed by:** saliha (proposer); derrick and nate to accept or change their items (Open board rows)
- **Status:** open · nate's items answered by @nate 2026-10-25 03:00

### 2026-10-24 20:52 — docs — One project folder; context trimmed to the plan docs — @saliha
- **Where:** `context` @ `1a96e99` · `main` @ `ab7b121` (`.gitignore`) · merged to `main`: yes
- **Did:** Rebuilt saliha's checkout as one folder (no sibling worktrees; the Showdown server sits in a git-ignored `pokemon-showdown/`). `context` keeps `CLAUDE.md`, the PRD, the three briefs and `design-decision/`; skills, the event doc and the research doc stay local, and research is deleted per feature once it ships. `CLAUDE.md` publishes through a temporary git index instead of a second checkout. The PRD's NOW, scope, data, failure modes, evaluation, milestones and open questions are filled from what's built.
- **Touched:** `context` (all files), `.gitignore`
- **Brief task:** none
- **⚠️ Conflicts:** @all: `design/` became `design-decision/`; the skills and the research and event docs left `context` (Open board row)
- **📨 Needs:** none
- **Status:** open (the note to @all)

### 2026-10-24 20:36 — feat — Bot layer: log parser to BattleState — @saliha
- **Where:** `sali` @ `c25be7e` · merged to `main`: yes (fast-forward)
- **Did:** `bot/parser.py` turns Showdown protocol lines into the contract's `BattleState`. It's pure, so live battles and saved replays use the same code. Replay `gen9ou-2703852247` turn 2 equals `contracts/examples/battle_state_turn2.json`; 20 recent public gen9ou games (383–457 turns) parse with no skipped line. 25 tests, 100% coverage on `bot/`.
- **Touched:** `bot/__init__.py`, `bot/parser.py`, `bot/tests/test_parser.py`, `bot/tests/fixtures/gen9ou-2703852247.log`
- **Brief task:** saliha task 3 ✅
- **⚠️ Conflicts:** @derrick, @nate: new shared entry point (Open board rows). No contract field changed meaning
- **📨 Needs:** none
- **Status:** open (the note to @derrick) · nate's note resolved by @nate 2026-10-25 03:00

### 2026-10-24 20:15 — decision — Bot runs on poke-env, gen9ou, local server; all three briefs get the demo plan — @saliha
- **Where:** `context` @ `538549d` · merged to `main`: n/a (docs branch)
- **Did:** Picked poke-env 0.16.1 (a `Player` subclass tapping raw lines and calling `Agent.choose`) on gen9ou with one fixed team and a seeded opponent pool, on a local Showdown server (research pass 8). Briefs now cover a working demo: parser, wiring, decision trace, eval harness vs poke-env's three baselines, demo mode. The PRD's architecture and stack are filled from what's built. saliha and derrick own design choices; decision-layer ones are derrick's.
- **Touched:** `context`: PRD, `CLAUDE.md`, research doc, all three briefs, `design/DESIGN.md`, `design/bot-layer.md`
- **Brief task:** saliha task 1 ✅
- **⚠️ Conflicts:** @derrick: the bot adds `poke-env` to `pyproject.toml` (yours). @nate: new tasks in your brief
- **📨 Needs:** @derrick: OK on the dependency, and your calls on tasks 8–9. @nate: read tasks 6–8
- **Status:** open

### 2026-10-24 19:26 — feat — Decision layer: lead picked by type matchup at team preview — @derrick
- **Where:** `derrick` @ `a50936e` · merged to `main`: not yet
- **Did:** Feature 11. At preview each of our six is scored on STAB type matchups against the opponent's six (log₂ of our best multiplier minus theirs, immunity floored at ×0.25); best leads, back five keep order. Forced switches keep the main-loop scoring. Type chart snapshot at `decision/data/typechart.json`. 144 tests, 100% coverage.
- **Decided:** lead = type-matchup rule (C), forced switch = reuse the main loop (A), both by @derrick. Revisit the lead if it loses turn 1 often in real games; the switch if the value model upgrade is cut.
- **Touched:** `decision/lead.py`, `decision/agent.py`, `decision/actions.py` (comment), `decision/data/typechart.json`, `tests/test_lead.py`, `tests/test_agent.py`
- **Brief task:** none listed (feature 11 is in the brief's scope contract); Done log line written locally, not published
- **⚠️ Conflicts:** none: preview still answers `team ……` through `Agent.choose`, so the bot's interface is unchanged
- **📨 Needs:** @saliha: publish the feature 11 docs + brief line, mirror the decisions in PRD → NOW, and look at the publish script refusing non-owners since the trim (Open board row)
- **Status:** open (the row to @saliha)

### 2026-10-24 19:16 — docs — Context branch trimmed; Derrick's feature 12 docs published — @saliha
- **Where:** `context` @ `54086aa` · merged to `main`: n/a (docs branch); `.gitignore` on `main`
- **Did:** Published `design/decision/12-budget-fallback.md` and the §7 tick from `derrick`, which closes both of Derrick's publish rows. Removed the duplicate `.claude/`, `scripts/` and every skill except `debug` and `no-slop` from `context`. `main`'s `.gitignore` now also ignores `.claude/`, `scripts/`, `builder-files/`, `design/`, `skills/` and `Research-Context/`.
- **Touched:** `context` branch, `.gitignore`
- **Brief task:** none
- **⚠️ Conflicts:** @all: `scripts/` is no longer on `context`, so a fresh clone can't bootstrap the sync hook from it
- **📨 Needs:** none
- **Status:** open (the note to @all)

### 2026-10-24 18:50 — feat — Decision layer: 3 s turn budget and a fallback that never stalls — @derrick
- **Where:** `derrick` @ `a57313e` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** `Agent.choose()` always answers: a 3 s budget (most likely scenarios first, best-so-far when time's up), and any error is logged with the turn and replaced by the first legal option, or `default` if even that fails. 140 tests, 100% coverage.
- **Touched:** `decision/agent.py`, `tests/test_agent.py`
- **Brief task:** none new
- **⚠️ Conflicts:** @saliha: `choose()` never raises now; decision errors appear on the `decision` logger, so the bot should send its logs somewhere visible. It can also return `"default"`
- **📨 Needs:** none new
- **Status:** open (the note to @saliha)

### 2026-10-24 18:40 — feat — Decision layer: the turn loop runs end to end — @derrick
- **Where:** `derrick` @ `640216c` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** `Agent(priors).choose(request, battle)` turns a Showdown request + BattleState into a choice string, running belief → 5 scenarios → build_state → both sides' actions → simulate → value → select. Selector now takes the opponent's odds per set. Team preview and forced switches have stand-ins until feature 11. A full move decision takes well under a second in tests. 135 tests, 100% coverage.
- **Touched:** `decision/agent.py`, `decision/selector.py`, `tests/test_agent.py`, `tests/test_selector.py`
- **Brief task:** none new (the core loop is task 1, already ✅; belief task 4 still 🟡)
- **⚠️ Conflicts:** @saliha: the bot's whole hook into the decision layer is one call per request: `agent.choose(request_dict, battle_state) -> "move 2" | "switch 4" | "team 123456" | None` (None on a wait), with one `Agent(priors)` per battle
- **📨 Needs:** none new
- **Status:** open (the note to @saliha)

### 2026-10-24 18:32 — docs — BattleState contract: last_move reset and Event.source spellings written in — @derrick
- **Where:** `derrick` @ `eb56c61` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** Answered saliha's 18:30 ask: `contracts/battle-state.md` + `battle_state.py` now say `last_move` resets to null when that side switches, and list the exact `Event.source` strings belief matches. No field changed meaning.
- **Touched:** `contracts/battle-state.md`, `contracts/battle_state.py`
- **Brief task:** none
- **⚠️ Conflicts:** none (writes down what saliha already agreed)
- **📨 Needs:** @saliha: publish the newer 03-05 + decision-layer.md (Open board row)
- **Status:** open → publish asks resolved by @saliha 2026-10-24 19:16 (`context` @ `54086aa`)

### 2026-10-24 18:30 — decision — Bot layer is saliha's; `last_move` resets on switch; Derrick's notes 02-05 published — @saliha
- **Where:** `context` @ `cb32fd0` (docs only) · merged to `main`: n/a
- **Did:** (1) saliha owns the bot layer and the log parser; as doc owner saliha waived a separate yes from Nate (the bot layer meets the data layer only through `BattleState`), Nate is informed and can object here. (2) Answer to Derrick's ⚠️: yes, the parser resets `sides[*].last_move` to null when that side switches; Derrick please spell it out in `contracts/battle-state.md`. (3) The parser will emit `Event.source` exactly as the contract examples spell it (`"stealthrock"`, `"item:<id>"`). (4) Published `design/decision/02..05-*.md` from `derrick` @ `e4cef23`; the earlier 12 docs were already out.
- **Touched:** `design/decision/02-05`, `builder-file-saliha.md`, PRD NOW
- **Brief task:** saliha tasks 1-5 unchanged; the Nate wait tag removed from task 3
- **⚠️ Conflicts:** none
- **📨 Needs:** @derrick: add the `last_move` rule to the contract. @nate: review `contracts/set-candidates.md` (Derrick's 18:14 entry). The user picks the (a)-(e) build choices and the bot skeleton on the main account
- **Agreed by:** saliha, derrick (proposer); nate informed
- **Status:** resolved by @saliha 2026-10-24 18:30 (the 🔀, ⚠️ and 📨 rows above are cleared)

### 2026-10-24 18:29 — feat — Decision layer: soft reweight by replaying each turn in poke-engine — @derrick
- **Where:** `derrick` @ `7fb50c3` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** Belief now replays last turn per candidate set (the loop calls `belief.chose(request, action)` after choosing) and drops sets the engine can't square with the observed move order or damage (both ways, crits included, ±1 for rounding). Speed ties, flinches, U-turn pivots and KOs handled; switches, one-sided turns and multi-hit moves give no evidence. 126 tests, 100% coverage.
- **Touched:** `decision/belief.py`, `decision/simulate.py` (`engine_move` now public), `tests/test_reweight.py`
- **Brief task:** 4 → 🟡 part (all belief logic built on hand-made priors; the real set file and the "beats uniform log loss" check wait on @nate's data)
- **⚠️ Conflicts:** @saliha: belief reads event order within `last_turn` (move → damage) and each damage event's `crit`; `hit_count` is parked in the contract for multi-hit moves
- **📨 Needs:** none new
- **Status:** open (the note to @saliha)

### 2026-10-24 18:17 — feat — Decision layer: belief (hard filter + sampling) on hand-made priors — @derrick
- **Where:** `derrick` @ `7ca09bb` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** `Belief(priors, battle)` keeps each opponent slot's set weights for the battle. `update()` filters on revealed moves/item/ability/Tera and four implied-item rules (Choice, Assault Vest, Leftovers, Boots), rebuilding from usage when nothing fits. `scenarios(k=5)` gives the active's top 5 with the bench at its best guess. Soft reweight (04) is next. 113 tests, 100% coverage.
- **Touched:** `decision/belief.py`, `tests/test_belief.py`
- **Brief task:** 4 → 🟡 part (logic on hand-made priors; real set file waits on @nate)
- **⚠️ Conflicts:** @saliha: the rules read `Event.source` values `"stealthrock"` and `"item:<id>"` exactly as the contract's examples spell them
- **📨 Needs:** none new
- **Status:** open (the note to @saliha)

### 2026-10-24 18:14 — decision — Derrick drafts the SetCandidates contract; belief logic starts ahead of the merge — @derrick
- **Where:** `derrick` @ `f9744ee` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** Drafted the per-species set file the data layer builds and the decision layer's belief loads (`contracts/set-candidates.md`, `contracts/set_candidates.py`, example with real 2026-09 1825 usage). Derrick's contents decisions: chaos 1825 / 2026-09, sets combined from usage shares, 30 per species, no teammate data, no "other" set. Starting brief task 4's belief logic (hard filter, reweight, sampling) on hand-made sets before task 2 (the merge).
- **Touched:** `contracts/set-candidates.md`, `contracts/set_candidates.py`, `contracts/examples/set_candidates_example.json`, `tests/test_set_candidates_contract.py`
- **Brief task:** 4 in builder-file-derrick.md → 🟡 part (logic only; the set file is @nate's)
- **⚠️ Conflicts:** @nate: this defines the shape of your set-candidates output (`data/`), please review before building it
- **📨 Needs:** @nate: yes/no on the contract and the file path (proposed `data/set_candidates.json`). @saliha: publish the 02-05 decision notes from `origin/derrick` (`design/decision/02..05-*.md`)
- **Status:** resolved by @nate 2026-10-25 03:00

### 2026-10-24 18:00 — docs — Research merged, builder briefs filled, Derrick's docs published — @saliha
- **Where:** `context` @ `1163870` (docs only) · merged to `main`: n/a
- **Did:** Merged six research passes into `OxHack-2026-research.md` (READ THIS FIRST at the top). Published Derrick's 12 decision-layer feature docs and his research section 7. Filled `builder-file-saliha/nate/derrick.md` from the template and 👥 Team below. CLAUDE.md halved; research protocol is now the `research-protocol` skill; Read guard + active-session warning added to the prompt hook.
- **Touched:** `OxHack-2026-research.md`, `design/decision*`, `builder-files/*`, `CLAUDE.md`, `scripts/prompt-check.sh`
- **Brief task:** briefs created for all three builders
- **⚠️ Conflicts:** none. Each builder should read their brief once and fix the "Open blanks" list in it
- **📨 Needs:** @nate: yes/no on saliha owning the bot layer, your branch name and `data/` paths; run `bash scripts/prompt-check.sh --install-guard` once. @derrick: same install
- **Status:** open

### 2026-10-24 17:51 — feat — Decision layer: Struggle, and Encore no longer crashes the engine — @derrick
- **Where:** `derrick` @ `bd84938` (code) · docs handed off at `9c98381` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** When Choice lock / Encore / Taunt leave the opponent no usable move, `build_state` gives it Struggle (poke-engine only runs it from the move list). Fixed a crash: poke-engine panics on any Encored side unless `last_used_move` is set, which the adapter now does. Found: poke-engine's gen9 Struggle is a Normal-type move with no recoil (real one is typeless, ¼ recoil). 96 tests, 100% coverage.
- **Touched:** `decision/adapter.py`, `decision/opponent.py`, `tests/test_opponent.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** none
- **📨 Needs:** @saliha: publish the decision-layer docs from `origin/derrick` (Open board row). The publish script only lets the doc owner publish them
- **Status:** open

### 2026-10-24 17:41 — feat — Decision layer: opponent options + uniform policy — @derrick
- **Where:** `derrick` @ `82e0eb6` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** `opp_actions(state, battle)` lists the opponent's moves, Tera moves (while unused) and switches; Choice lock, Encore and Taunt limit them. `uniform_policy()` gives each move/switch an equal share, split with its Tera copy. Adds a `moves.json` snapshot for move categories. 92 tests, 100% coverage.
- **Touched:** `decision/opponent.py`, `decision/data/moves.json`, `tests/test_opponent.py`, `tests/turn2.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** @saliha: relies on `BattleState.sides[*].last_move` being reset when the active Pokémon switches out (Choice lock / Encore)
- **📨 Needs:** none new
- **Status:** open (the note to @saliha)

### 2026-10-24 17:20 — decision — saliha accepts the bot layer + log parser; waiting on Nate — @saliha
- **Where:** PRD §0 NOW (published to `context`) · merged to `main`: n/a (docs only)
- **Did:** Answered Derrick's 🔀 proposal: saliha owns the bot layer and builds the parser that fills the `BattleState` contract. Not agreed yet: Nate's yes (§2c). Research for the data, decision and bot layers is running; notes land in the research doc.
- **Touched:** none in code
- **Brief task:** none
- **⚠️ Conflicts:** none
- **📨 Needs:** @nate: yes/no on saliha owning the bot layer. @derrick: push `design/decision/*.md` to `context` (not there yet; `design/decision-layer.md` is)
- **Agreed by:** saliha, derrick (proposer); nate pending
- **Status:** open

### 2026-10-24 17:05 — feat — Decision layer: full poke-engine state from a request + BattleState — @derrick
- **Where:** `derrick` @ `a104fb4` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** `build_state(request, battle_state, sets)` builds the whole turn state: our team from the request, the opponent + field from `BattleState`, hidden opponent details from one guessed set per slot (nature + EVs → stats). Revealed info beats the guess. Tested on the contract's turn-2 example. 81 tests, 100% coverage.
- **Touched:** `decision/adapter.py`, `decision/sets.py`, `tests/test_adapter.py`, `tests/test_sets.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** none (reads `contracts/battle_state.py`; the parser that fills it is the open 🔀 proposal to @saliha)
- **📨 Needs:** none new

### 2026-10-24 16:46 — scope — Proposal: saliha owns the bot layer and builds the log parser to Derrick's BattleState contract — @derrick
- **Where:** `derrick` @ `e98b302` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** Drafted the `BattleState` contract (what the parser hands the decision layer each turn, as JSON): both sides in the same shape, field, and last turn's events; Showdown IDs and 0–100 HP. Real example from turn 2 of replay `gen9ou-2703852247`, plus a test that keeps example and types in step.
- **Touched:** `contracts/battle-state.md`, `contracts/battle_state.py`, `contracts/examples/battle_state_turn2.json`, `tests/test_battle_state_contract.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** none yet (no bot layer code exists)
- **📨 Needs:** @saliha: yes/no on owning the bot layer + building the parser; review the contract. @nate: yes/no on the ownership
- **Agreed by:** not yet (proposal)
- **Status:** open

### 2026-10-24 16:31 — feat — Decision layer: heuristic value + looser selector ties — @derrick
- **Where:** `derrick` @ `0ca12e4` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** `value(state)` scores a position 0–1 (0.5 = even): each Pokémon = alive + HP fraction, ours vs theirs. Same scale as the planned win-probability model. The selector's tie tolerance is now 1e-6, matching poke-engine's 32-bit probabilities. 59 tests, 100% coverage.
- **Touched:** `decision/value.py`, `decision/selector.py`, `tests/test_value.py`, `tests/test_selector.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** none
- **📨 Needs:** none

### 2026-10-24 16:23 — feat — Decision layer: our poke-engine side from a Showdown request — @derrick
- **Where:** `derrick` @ `e6cc855` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** `our_side(request)` builds our team as a poke-engine `Side` (HP, status, stats, moves + PP, item, ability, Tera) in request order. Types and weight come from a committed snapshot of Showdown's `pokedex.json`. State is rebuilt every turn (no memory). 47 tests, 100% coverage.
- **Touched:** `decision/state.py`, `decision/data/pokedex.json` (524 KB), `tests/test_state.py`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** bot layer owner (not assigned): boosts, volatiles, hazards, weather and the whole opponent side must come from `BattleState`; the request doesn't carry them | none else
- **📨 Needs:** none new
- **Status:** open (the bot layer note above)

### 2026-10-24 16:13 — feat — Decision layer: one-turn simulation via poke-engine — @derrick
- **Where:** `derrick` @ `50b9a77` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate)
- **Did:** `simulate(state, ours, theirs)` returns every outcome of a turn as (probability, next state), using poke-engine (Rust, built from source with its gen9 Tera feature). Replaying turn 1 of a real gen9ou game matches the log (Kingambit 66%). 0.038 ms per call. 31 tests, 100% coverage.
- **Touched:** `decision/simulate.py`, `tests/test_simulate.py`, `pyproject.toml` (new dependency `poke-engine==0.0.48`; building it needs Rust)
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** bot layer owner (not assigned): the decision layer now works in poke-engine's `State`, so whatever `BattleState` becomes gets converted to it once per turn (feature 01, decision side) | none else
- **📨 Needs:** none new
- **Status:** open (the bot layer note above)

### 2026-10-24 16:00 — feat — Decision layer: legal actions from a request, and the action selector — @derrick
- **Where:** `derrick` @ `b27a235` · merged to `main`: yes, as one clean commit `5e203fc` (2026-10-24 19:00; agreed by saliha, nate) (`derrick` was branched from `context`, so its shared docs must come off before a merge)
- **Did:** `our_actions(request)` lists our legal moves / Tera moves / switches / leads from Showdown's raw `|request|` JSON. `select()` picks the highest expected value over opponent actions × sets, tie-break on worst case. Python + uv + pytest; 25 tests, 100% coverage.
- **Touched:** `decision/actions.py`, `decision/selector.py`, `tests/`, `pyproject.toml`, `uv.lock`, `.gitignore`
- **Brief task:** none (no brief for derrick yet)
- **⚠️ Conflicts:** bot layer owner (not assigned): the decision layer is Python, so the bot ↔ decision seam crosses languages if the bot is TS | none else
- **📨 Needs:** @saliha: publish the decision-layer docs, record Python + the test command (Open board row). Bot layer owner: `BattleState`, which feature 07 is blocked on
- **Status:** open

