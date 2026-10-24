# OxHack-2026: Product Requirements Document
*OxHack 26 · HRT: Best Use of Data for Predictions & Decision Making · repo: https://github.com/saliha006/OxHack-2026 · v2 · 2026-10-24*
*Links: `CLAUDE.md` (how we work) · `builder-file-<name>.md` (who builds what) · the research doc (evidence) · `contracts/` (exact interfaces)*

> **How Claude fills this PRD** (delete this block once §1–§6 are filled)
> - **It fills itself as the chat goes** (CLAUDE.md 🔁): answers to a `{{…}}` or a `> Fill:` prompt go in the same turn.
>   An unknown stays `{{…}}`; never invent a number, a source or a claim. Bump `v{{n}} · {{date}}` on each published change.
> - **Fit, don't grab.** A leaning or a "maybe" goes to §0 NOW → Pending (and the vault Log), not into the spec.
>   Decided things go into the spec *and* into §0 → Decisions in force.
> - **The PRD records decisions; it doesn't make them.** Filling a section that is a design decision (data, contracts,
>   trust boundaries, failure modes, stack) goes through the CLAUDE.md §1 Decision Handoff first.
> - **Once the team has agreed the plan, it's guarded.** Changing scope, features, flows, architecture, contracts or the
>   stack needs the whole team's yes (CLAUDE.md §2c). The change is then logged as a `scope` entry in `progress.md`.
> - **One home per fact.** The pitch lives in §1 (CLAUDE.md's top line mirrors it), the cut list in §4, endpoints in §11,
>   the stack in §12. Everywhere else, point to the section. Never restate CLAUDE.md (process, branches, commands, ship
>   sequence) or the briefs (people, ownership, tasks, acceptance criteria).
> - **Evidence lives in the research doc.** Here you write the claim plus a ledger ref (`[R§3]`), not the source dump.
>   KEEP sources only; never a DO NOT USE metric.
> - **Stay inside each heading's length budget.** Over budget → move the detail to `contracts/`, a config file, a brief or
>   the Appendix. Prefer a table to prose. A filled MVP PRD lands at about 2,500–3,500 words.
> - **★ = required for the MVP.** Fill those first, in order. Section numbers never change: an optional section that
>   doesn't apply says `n/a: <why>` rather than being deleted, so § refs in the briefs stay valid.
> - Delete each `> Fill:` line once its section is filled.

---

## 0. NOW ★ *(≤20 lines; the part every agent reads at session start)*
> Fill: what's true today. Update it the moment a decision, the direction or the headline changes (CLAUDE.md §8 mirrors).

**Decisions in force** (newest first; one line each, full ADR in the vault Log):
- 2026-10-24: one project folder. `context` holds `CLAUDE.md`, this PRD, `builder-files/` and `design-decision/`; `main` holds code, `README.md` and `progress.md`. Research and the event doc stay local and are deleted per feature once it ships. (saliha)
- 2026-10-24: bot = poke-env 0.16.1 (`Player` subclass tapping raw lines, calling `Agent.choose`), format gen9ou with one fixed team + a seeded validated opponent pool, local Showdown server. Own websocket client is the fallback. Research pass 8. (saliha)
- 2026-10-24: system design choices are owned by saliha and derrick, and decision-layer choices are derrick's. The four decision-layer lines below are recommendations he can override; he already built a type-matchup lead (feature 11). (saliha)
- 2026-10-24: forced switch reuses the main loop with the opponent's only option `None` (double faint = normal switch-vs-switch matrix). Score stays Derrick's next-turn evaluation until the trained value model lands, then post-switch value only. (saliha, delegated to a reviewing agent)
- 2026-10-24: team preview uses Derrick's type-matchup lead (`decision/lead.py`, his decision C, built and tested); the earlier fixed-order recommendation is superseded. (derrick)
- 2026-10-24: action pruning: v1 enumerates everything and measures p50/p99 turn time; over budget, Tera only on the top few moves by damage, always keeping switches and one or two status moves. Opponent top-n only once the policy is trained, and never dropping the columns that hurt us most. (saliha, delegated to a reviewing agent)
- 2026-10-24: selector stays argmax-EV for v1 (built and tested). Next upgrade is a maximin mixed strategy from an LP over the payoff table behind a flag, kept if it wins in self-play; the tuned blend comes after that. The LP solver is a new dependency and needs the team's yes. (saliha, delegated to a reviewing agent)
- 2026-10-24: target tracks are **HRT "Best Use of Data for Predictions & Decision Making"** (main) and **Best Handmade** (also); TIME is optional but applies to Handmade (event doc §3). (saliha)
- 2026-10-24: the doc owner is saliha; the working branch is `sali`; `.claude/`, `Research-Context/` and `.env*` never go to GitHub. (saliha)

**Pending** (not decided yet):
- The demo story: the battle agent is what's being built. Whether a Momentum-style replay review (win probability per turn plus the agent's preferred move) is added, reusing the parser and value model: saliha.
- Calibrated win-probability model replacing the HP heuristic: Derrick's call (his task 8).
- Data storage (ClickHouse vs plain files) and the high-Elo cut-off: Nate, with saliha and derrick.
- `poke-env==0.16.1` in `pyproject.toml` (Derrick's file): waiting on his OK. A Rust toolchain on saliha's machine so `poke-engine` builds: waiting on saliha.
- Handmade piece: no plan; ask the organisers what counts (event doc §6). Elo-from-decisions: parked.

**Focus right now:** bot smoke battle and decision-layer wiring (saliha, blocked on the dependency OK); team pool and set candidates (nate); decision trace and win-probability model (derrick).

**▶ RESUME HERE (2026-10-24 ~21:30):** the log parser is on `main`. Next for saliha: brief task 2 (poke-env smoke battle) once Derrick OKs the dependency, then task 4 (wire `Agent.choose`). Numbers: `progress.md` → 📊 Latest.

---

## 1. One page ★ *(≤15 lines)*
> Fill: the 30-second version. A judge or a new teammate should get the whole project from this section alone.

**One-liner:** a Pokémon Showdown Gen 9 OU battle agent that turns usage stats and replays into predictions (the opponent's hidden sets, the chance of winning) and uses them to choose every move, with its win rate measured against standard baseline bots.
- **Where it runs, for whom:** one laptop running a local Showdown server; judges watch live battles in the Showdown web client.
- **Track:** HRT Best Use of Data for Predictions & Decision Making (main); Best Handmade (also; no plan yet).

**What makes it real (and not a mock-up):** *(3–5 claims anyone could check: live data, real datasets with their size, a
trained model with its metric, something that ran unattended)*
1. A parser that reads real Showdown logs into the shared `BattleState` (tested on public gen9ou games; numbers in `progress.md` → 📊 Latest).
2. A tested decision layer that answers any request within a 3 s budget and never stalls.
3. {{eval-harness win rates vs three baselines: not run yet}}

**Novelty line:** *Unlike {{existing option A}} (which {{its gap}}) and {{option B}} (which {{its gap}}), OxHack-2026
{{the one thing only it does}}.* Name the prior art openly, and claim nothing broader than the gap.

## 2. Problem and evidence ★ *(≤6 bullets + the never-say lines)*
> Fill: who is hurt, how badly, how often, and why now. Each bullet is a claim plus its ledger ref; the evidence itself
> stays in the research doc.

- **Who:** {{affected people, and how many if a source supports it}} [R§]
- **How bad, how often:** {{…}} [R§]
- **Why today's fixes fail:** {{…}} [R§]
- **Why now:** {{…}} [R§]
- **Prior art:** {{named products or programmes, and what they don't do}} [R§]

**Claims we never make:** ⚠️ {{overclaims to avoid, e.g. "never say it would have saved X", "never quote a count we can't source"}}

## 3. Users and decisions ★ *(one row per actor)*
> Fill: everyone who touches the system, what they get, and the decision it helps them make. Include the person who is
> harmed if it goes wrong, even if they never log in.

| Actor | Context (their day, their constraints) | Gets (screen / channel) | Decision it supports |
|---|---|---|---|
| {{…}} | {{…}} | {{…}} | {{…}} |

## 4. Scope ★ *(≤10 rows; the only project-wide out-of-scope list)*
> Fill: what's real, what's simulated, what's next and what's cut. Briefs may add area-specific exclusions.

| Layer | What's in it, and why |
|---|---|
| **Real / live** | Battles on a local Showdown server; set priors and training data from real replays and Smogon usage stats |
| **Simulated** (labelled on screen) | Opponents are baseline bots, not ladder players: the public ladder needs a registered bot |
| **Stretch / next step** | Calibrated win-probability model, maximin LP selector, browser side panel, public ladder run, replay review |
| **Cut** | Voice and LLM coaching text (no feature scheduled); TypeScript runtime (replaced by Python + poke-engine) |

**Demo-vs-product gap:** a registered bot account under Smogon's bot policy for ladder play; opponents that adapt; more than one team.
CLAUDE.md §2 treats anything in this list as a 🟠 decision.

## 5. User flows ★ *(2–4 flows, ≤7 steps each; the demo flow first)*
> Fill: step-by-step journeys. Each step names the actor, the screen or endpoint (§11), and what the system does.
> Include the one unhappy path that matters most.

**Flow A: {{name}} (the demo flow)**
1. {{actor}} {{does what}} on {{screen / endpoint}} → system {{does what}} → {{actor}} sees {{what}}

**Flow B: {{name}}**
1. {{…}}

## 6. Functional requirements ★ *(≤15 rows)*
> Fill: what the system must do, numbered so the briefs' *Done when:* lines can cite them (`FR-3`). Use testable verbs:
> "returns", "shows", "rejects", not "supports" or "handles".

| ID | Requirement | MVP / stretch | Flow |
|---|---|---|---|
| FR-1 | {{…}} | MVP | A |

## 7. Core logic *(★ if non-trivial; ≤10 lines per component)*
> Fill: the rules and algorithms that make the decisions: inputs → output, each threshold and where its number comes
> from, and why this rule beats the obvious one. Long value tables go to config files; link them.

### 7.1 {{component}}
- **In:** {{…}} · **Out:** {{…}}
- **Rule:** {{…}}
- **Why:** {{…}} [R§]

## 8. AI, models and agent *(optional; `n/a` if there's no AI)*
> Fill: every model, where it runs and how it's judged against a baseline. Then the decisions the agent makes that a
> script couldn't, and the anti-wrapper test.

| # | Model / component | Framework | Runs where | Trained on | Metric (vs baseline) |
|---|---|---|---|---|---|
| M1 | Baseline: {{the simplest thing that could work}} | {{…}} | {{…}} | {{…}} | {{…}} |

- **Decisions a script can't make:** {{1–3, each with what it decides, from which input, and what it logs}}
- **Agent loop:** {{tick or trigger}} · memory in {{store}}, survives a restart: {{yes/no}} · on a failed tick: {{behaviour}}
- **Anti-wrapper test:** {{"delete the LLM and every decision is unchanged", or exactly what changes}}
- **Human in the loop:** {{which actions need approval}}

## 9. Data ★ *(2 tables)*
> Fill: every source the system reads, then every entity it stores. Sensitivity and retention drive §14.

**Sources**
| Role | Dataset / feed | Span / latency | Licence / access | Status |
|---|---|---|---|---|
| train | `HolidayOugi/pokemon-showdown-replays` (Hugging Face) | 34.3M replays, ~2.5M gen9ou | no licence stated | KEEP |
| validate | Metamon raw replays | ~2.68M rows, cutoff 2026-05-19 | pseudonymised; parsed set CC BY-NC 4.0 | KEEP |
| test | Showdown replay API, games after 2026-05-19 | live | public uploads only | KEEP |
| priors | Smogon chaos stats `gen9ou-1825`, 2026-09 | monthly | public | KEEP |
| live | Local Showdown server battles | per turn | ours | KEEP |

**Entities** (what we store)
| Entity | Key fields | Written by | Read by | Sensitivity | Retention |
|---|---|---|---|---|---|
| Battle log + decision trace | turn, `BattleState`, choice, top options, win probability, think time | bot | eval harness, charts, replay review | internal | local `runs/`, through the demo |
| Set candidates | per species: weighted sets + an "other" bucket | data layer | decision layer | public (derived) | rebuilt per stats month |
| Team pool | seeded packed gen9ou teams | data layer | bot eval | public | kept with its seed |

## 10. System architecture ★ *(diagram ≤25 lines + one table)*
> Fill: the boxes, the arrows, where each one runs, and the resource budget. Freeze the contracts early so nobody blocks.

```
OFFLINE (data layer)                         ONLINE, per request (one laptop)
replays + chaos stats ─► set candidates ─────────────────────┐
                     └─► (state, winner) pairs ─► value model (later)
Showdown server ─log lines─► bot parser ─► BattleState ─► Agent.choose() ─► choice ─► server
                                  └─► runs/*.jsonl trace ─► eval harness · demo · charts
```

| Component | Job | Runs on | Talks to | Budget (CPU / RAM) | Area |
|---|---|---|---|---|---|
| Showdown server | Runs battles; judges watch in the web client | Local, Node ≥ 22.18 | Bot | {{…}} | platform |
| Bot layer | Connection, parser, trace, eval harness | Local, Python | Server, decision layer | {{…}} | backend |
| Decision layer | Belief → simulate → value → select, 3 s budget | In-process with the bot | Bot, set candidates | {{…}} | ML |
| Data layer | Ingestion, set candidates, training pairs, charts | Offline | Files for the other two | {{…}} | ML / data |

**Contracts, frozen by {{time}}:** `contracts/battle-state.md` and `contracts/set-candidates.md` (drafts on `main`), and `agent.choose(request, battle_state) -> str | None`

## 11. Interfaces ★ *(one row per endpoint or event; the full spec lives in `contracts/`)*
> Fill: every API endpoint, event or function boundary that another builder depends on.

| Method · path / event | Purpose | Consumer | Auth | Key fields in → out |
|---|---|---|---|---|
| {{GET /health}} | {{…}} | {{…}} | {{…}} | {{…}} |

## 12. Tech stack ★ *(one row per layer; the stack's only home)*
> Fill: each layer, the choice, why it beat the obvious alternative, and the gotcha that bit us (or could). Every new
> dependency is a 🟠 decision (CLAUDE.md §2).

| Layer | Choice | Why (vs alternative) | Gotcha |
|---|---|---|---|
| Decision layer | Python, `poke-engine` 0.0.48, `uv`, `pytest --cov` | Built and merged on `main` | Legality comes from the request, not the engine |
| Bot layer | Python, poke-env 0.16.1 | Only option with baseline bots + concurrent battles; raw lines via `_handle_battle_message`, request via `battle.last_request` | Parse errors can hang a run (#973); add `/choose ` ourselves; search off the event loop |
| Game server | Pokémon Showdown, local, `--no-security` | No account, no rate limits, watchable | The public server needs bot registration (`/ht`) |
| Data storage | 🟠 pending: ClickHouse vs lighter files | {{…}} | {{…}} |
| Design direction | {{palette, type, motion feel; tokens file}} | {{…}} | {{…}} |

## 13. Non-functional requirements ★ *(≤8 rows, each one a number)*
> Fill: targets you could test. "Fast" isn't a requirement; "p95 < 300 ms at 1k events/s" is.

| Quality | Target | How we check |
|---|---|---|
| Throughput | {{…}} | {{…}} |
| Latency | {{…}} | {{…}} |
| Availability / restart | {{…}} | {{…}} |
| Resource limits | {{…}} | {{…}} |
| Accessibility | {{e.g. WCAG 2.2 AA on the main screens}} | checked by hand |
| Privacy / retention | {{…}} | {{…}} |

## 14. Security and trust ★ *(≤2 tables + hard rules)*
> Fill: who can do what, how data is protected, and the realistic threats. Everything here is a 🟠 decision before it's code.

| Role | Can | Can't |
|---|---|---|
| {{…}} | {{…}} | {{…}} |

| Threat | Mitigation |
|---|---|
| {{…}} | {{…}} |

- **At rest / in transit:** {{…}}
- **Hard rules:** {{data that must never be stored, endpoints that must never exist, e.g. "no real personal data on the
  demo box"}}. Secrets are never committed.

## 15. Failure modes ★ *(≤10 rows)*
> Fill: what breaks, how we notice, what the system does, and what the user sees. Include demo-day fallbacks (the Wi-Fi
> dies, an API rate-limits, the model won't load).

| Failure | Detected by | System behaviour | User sees |
|---|---|---|---|
| Decision error or over 3 s | `Agent.choose` catches it; `decision` logger | first legal option, else `default` | the battle goes on |
| Malformed protocol line | parser warning | skips the line, keeps the state | nothing |
| Invalid choice | `|error|[Invalid choice]` | resend the first legal option, then `default` | nothing |
| Socket drop (slow search) | poke-env keepalive | search off the event loop; reconnect | a battle may be forfeited |
| No Wi-Fi at the demo | n/a | everything runs locally | nothing |

## 16. Sponsor / platform fit *(optional; ≤5 bullets)*
> Fill: how each sponsor or required technology is genuinely used, not bolted on, each with a proof you can show on screen.

- **{{tech}}:** {{how it's used}} · proof: {{command or screen}}

## 17. Evaluation and success ★ *(2 tables + definition of done)*
> Fill: the questions a sceptical judge or user would ask, the evidence that answers each, and the target. Then map
> every judging criterion (event doc) to where we prove it.

| Question | Evidence | Target |
|---|---|---|
| Does it beat the baseline? | 100 games each vs poke-env's `RandomPlayer`, `MaxBasePowerPlayer`, `SimpleHeuristicsPlayer`; win rate with a 95% Wilson interval | lower bound above 50% vs `MaxBasePowerPlayer` |
| Are its win probabilities honest? | log loss, Brier and a reliability diagram on held-out games, split by battle, time and player | better than the HP heuristic |

| Judging criterion | Where we prove it (§ / demo beat) |
|---|---|
| {{…}} | {{…}} |

**Definition of done (MVP):** one command starts a live gen9ou battle on the local server in which the agent plays every turn through the decision layer with no stalls, and the eval table vs the three baselines exists.

## 18. Demo script ★ *(≤{{length}}; one row per beat)*
> Fill: timed beats. Say what's live and what's recorded. Every beat has a fallback.

| Time | Beat | Live / recorded | Fallback |
|---|---|---|---|
| 0:00 | **Hook:** {{one line that makes the problem real}} | {{…}} | {{…}} |
| {{…}} | **Honest limits + next steps** | {{…}} | {{…}} |

## 19. Milestones and cut order ★ *(≤10 rows; no per-person tasks)*
> Fill: checkpoints with times and what "done" means at each. Then what gets cut first if time runs out, and what never
> gets cut. Per-person tasks live in the briefs.

| When | Milestone (done means…) |
|---|---|
| Sat 23:00 BST | Bot plays random legal moves on the local server |
| Sun 03:00 GMT | **Walking skeleton:** parser + decision layer play full games with no stalls |
| Sun 07:00 GMT | Eval numbers vs three baselines; feature freeze 10:00 |
| Sun before 12:00 GMT | **Submit** on Devpost with the GitHub link |

**Cut order (first → last, proposed):** 1. public ladder run · 2. browser side panel · 3. maximin LP · 4. calibrated win-probability model
**Never cut (proposed):** the live demo battle and the eval table vs baselines

## 20. Risks ★ *(≤6 rows)*
> Fill: what could sink the project (technical, data access, time, people, event rules), not every possible bug.

| Risk | Likelihood | Impact | Mitigation | Trigger to act |
|---|---|---|---|---|
| {{…}} | {{L/M/H}} | {{L/M/H}} | {{…}} | {{…}} |

## 21. Open questions ★ *(≤8; facts to find out)*
> Fill: questions only. Undecided design choices go in §0 → Pending; tasks go to the briefs.

- [ ] The real Devpost deadline and what the form requires: owner saliha, needed by Sun 09:00 (event doc §6)
- [ ] Can one project win HRT and Best Handmade? How is HRT judged, and by whom? Owner saliha, needed by Sun 09:00
- [ ] Are datasets prepared before 12:00 Saturday allowed? Owner saliha, needed before training

## 22. Glossary *(★ if the domain has jargon; one line per term)*
| Term | Meaning |
|---|---|
| {{…}} | {{…}} |

---

## Appendix *(agents can stop reading here)*

### A. Judge / user Q&A
| Likely question | Short answer (point to the §) |
|---|---|
| {{…}} | {{…}} |

### B. Key sources
Full list: the research doc. Here, only the 3–6 links a judge might click.

### C. Version history *(≤3 lines; the reasons live in the vault Log ADRs)*
- v1 {{date}}: {{…}}
