# OxHack-2026: Product Requirements Document
*{{event · track}} · repo: https://github.com/saliha006/OxHack-2026 · v{{n}} · {{date}}*
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
- 2026-10-24: target tracks are **HRT "Best Use of Data for Predictions & Decision Making"** (main) and **Best Handmade** (also); TIME is optional but applies to Handmade (event doc §3). (saliha)
- 2026-10-24: the doc owner is saliha; the working branch is `sali`; `.claude/`, `Resreach-Context/` and `.env*` never go to GitHub. (saliha)

**Pending** (design choices not made yet; leanings, not decided):
- Idea: Momentum (Pokémon win probability + coach-style replay review, optional ElevenLabs voice) is the lead; Honest Clock is the fallback. Owner saliha, lock in the first hours.
- Elo angle: estimate a player's Elo from their decisions, using a dataset with ratings at all levels, plus top-500 ladder players' replays. Dataset choice waits on the research notes. Owner saliha.
- Layered design (data layer, decision layer, bot layer) and the four bot-skeleton choices (framework, server, format, bot↔decision contract): owner saliha; needs Nate and Derrick to agree (CLAUDE.md §2c).
- Bot layer + log parser (fills Derrick's `BattleState` contract): saliha said yes on 2026-10-24 to owning it (proposed by Derrick); **waiting on Nate's yes**. Decision layer is Python (`uv run pytest --cov=decision`).
- Handmade piece: physical or not, and what "from scratch" means: ask the organisers (event doc §6).

**Research pass done (2026-10-24):** merged into `OxHack-2026-research.md` (Grep it, ~200KB; passes 1-3 are the new ones). Not decided, the user's call: (a) value model = calibrated gradient-boosted win-probability (replaces the HP heuristic); (b) per-turn maximin LP over the payoff matrix instead of argmax-EV; (c) Bayesian opponent-set belief (biggest, 7-9 h); (d) data = `HolidayOugi/pokemon-showdown-replays` main + Metamon raw cross-check, Elo from the `|player|` line, split by battle/time/player; (e) coach text templated from computed numbers only. Suggested cut order: voice, LLM paraphrase, ClickHouse, Elo-from-decisions, belief layer.

**Focus right now:** pick (a)-(e), lock the idea and the evaluation plan, then build. Bot layer + log parser is saliha's once Nate agrees.

**▶ RESUME HERE (2026-10-24 ~18:00, saliha signing off; any account/session):** run `fetch the context`. Layers: Nate = data (`builder-file-nate.md`), Derrick = decision (`builder-file-derrick.md`), saliha = bot (`builder-file-saliha.md`); the three briefs were filled from the template today, each ends with an "Open blanks" list. Waiting on the user: (1) confirm the parser resets `BattleState.sides[*].last_move` to null on switch (Derrick's ⚠️ row), (2) Nate's yes on saliha owning the bot layer, (3) the (a)-(e) build choices above, (4) the bot skeleton choices (poke-env / local server / format). Next code step for saliha: local Showdown server + a random-move bot end to end (brief task 2).

---

## 1. One page ★ *(≤15 lines)*
> Fill: the 30-second version. A judge or a new teammate should get the whole project from this section alone.

**One-liner:** {{who it helps · what it does · how · why it's different, in one or two sentences}}
- **Where it runs, for whom:** {{deployment target; first users or region}}
- **Track:** {{event track, plus anything from other tracks that's built in}}

**What makes it real (and not a mock-up):** *(3–5 claims anyone could check: live data, real datasets with their size, a
trained model with its metric, something that ran unattended)*
1. {{…}}

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
| **Real / live** | {{what runs on real data or for real users}} |
| **Simulated** (labelled on screen) | {{what's synthetic, and why: law, access, time}} |
| **Stretch / next step** | {{…}} |
| **Cut** | {{what was dropped, one line of reason each}} |

**Demo-vs-product gap:** {{what a real deployment needs that the demo fakes: sensing, consent, scale, integrations}}.
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
| {{train / validate / live}} | {{…}} | {{…}} | {{…}} | KEEP / WEAK / cut |

**Entities** (what we store)
| Entity | Key fields | Written by | Read by | Sensitivity | Retention |
|---|---|---|---|---|---|
| {{…}} | {{…}} | {{component}} | {{component}} | public / internal / personal / health | {{…}} |

## 10. System architecture ★ *(diagram ≤25 lines + one table)*
> Fill: the boxes, the arrows, where each one runs, and the resource budget. Freeze the contracts early so nobody blocks.

```
{{inputs → components → stores → outputs, with process/container boundaries and the host}}
```

| Component | Job | Runs on | Talks to | Budget (CPU / RAM) | Area |
|---|---|---|---|---|---|
| {{…}} | {{…}} | {{…}} | {{…}} | {{…}} | {{frontend / backend / ML / platform}} |

**Contracts, frozen by {{time}}:** {{e.g. `contracts/openapi.yaml`, event schemas, the model interface signature, fixtures}}

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
| {{frontend / API / DB / ML / infra}} | {{…}} | {{…}} | {{…}} |
| Design direction | {{palette, type, motion feel from `design-direction` / `motion`; tokens file}} | {{…}} | {{…}} |

## 13. Non-functional requirements ★ *(≤8 rows, each one a number)*
> Fill: targets you could test. "Fast" isn't a requirement; "p95 < 300 ms at 1k events/s" is.

| Quality | Target | How we check |
|---|---|---|
| Throughput | {{…}} | {{…}} |
| Latency | {{…}} | {{…}} |
| Availability / restart | {{…}} | {{…}} |
| Resource limits | {{…}} | {{…}} |
| Accessibility | {{e.g. WCAG 2.2 AA on the main screens}} | `ui-audit` |
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
| {{a feed goes stale}} | {{…}} | {{…}} | {{…}} |

## 16. Sponsor / platform fit *(optional; ≤5 bullets)*
> Fill: how each sponsor or required technology is genuinely used, not bolted on, each with a proof you can show on screen.

- **{{tech}}:** {{how it's used}} · proof: {{command or screen}}

## 17. Evaluation and success ★ *(2 tables + definition of done)*
> Fill: the questions a sceptical judge or user would ask, the evidence that answers each, and the target. Then map
> every judging criterion (event doc) to where we prove it.

| Question | Evidence | Target |
|---|---|---|
| Does it beat the baseline? | {{…}} | {{…}} |

| Judging criterion | Where we prove it (§ / demo beat) |
|---|---|
| {{…}} | {{…}} |

**Definition of done (MVP):** {{the end-to-end path that must work, on which box, with what data}}

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
| {{+1 h}} | Contracts frozen (§10) |
| {{…}} | **Walking skeleton:** {{the thinnest end-to-end path}} |
| {{…}} | Feature freeze |
| {{…}} | **Submit** |

**Cut order (first → last):** 1. {{…}}
**Never cut:** {{…}}

## 20. Risks ★ *(≤6 rows)*
> Fill: what could sink the project (technical, data access, time, people, event rules), not every possible bug.

| Risk | Likelihood | Impact | Mitigation | Trigger to act |
|---|---|---|---|---|
| {{…}} | {{L/M/H}} | {{L/M/H}} | {{…}} | {{…}} |

## 21. Open questions ★ *(≤8; facts to find out)*
> Fill: questions only. Undecided design choices go in §0 → Pending; tasks go to the briefs.

- [ ] {{question}}: owner {{name}}, needed by {{time}}

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
