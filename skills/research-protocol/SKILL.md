---
name: research-protocol
description: The team's research protocol. Use whenever ANY research is about to start, whether the user asks ("look this up", "validate this", "find papers", "research X") or Claude or a subagent is about to search the web on its own. Gives the sourcing rules, the KEEP / WEAK / DO NOT USE ledger and the one-research-doc structure. Load before spawning any research agent.
---

# Research protocol: every time (asked OR self-initiated)

**Trigger:** ANY research, whether the user asks ("look this up / validate this") **or Claude spins up a research agent on
its own.** One step, not deferred: **gather sources AND produce the per-source `KEEP` / `WEAK` / `DO NOT USE` ledger AND
save it into the research doc, in the same pass.** Never hand back findings without the ledger.

**Sourcing rules:**
- **Peer-reviewed papers, reputable journals, credible articles and official engineering sources**, not blogs or SEO pages.
- **Recency:** prefer the **last 1–2 years**; extend to **3–4** only when recent high-quality work is scarce, and say so.
- **Region:** prioritise UK / EU / US venues, but **quality wins**. A stronger paper from anywhere beats a weaker local one.
- **Verify existence before citing.** Actually fetch/open the source. Never cite from memory or a bare ID.

**Consensus (never trust one paper):**
- Every **load-bearing claim or metric** needs **≥2 independent corroborating** sources.
- **Hunt for refutations.** If **multiple credible sources refute** a claim, mark it **`DO NOT USE`**, list the disproving
  sources, **move it to the bottom**, and **strip its metrics from active use**. Leave a short tombstone so it isn't
  re-litigated.
- **Verdict per source: `KEEP` (corroborated) · `WEAK` (thin support) · `DO NOT USE` (refuted).**

**Community consensus (blend it in):** mine Reddit / Hacker News / StackExchange / Quora. Weight by **agreement**
(upvotes, agreeing replies) and **repetition across threads**. Note contrasting views and which wins.
**Final call = professional consensus + community consensus, aggregated.** State both.

**Doc structure:** **one research file** (the research doc); don't spawn new `research-*.md` files. Each pass is a
clearly-labelled section with topic sub-headings and an updated CATEGORY INDEX. **`KEEP` at the top** (with
corroborating sources), **`DO NOT USE` quarantined at the bottom** of its section (with refuting sources + the discredited
metric). Breezy and skimmable.

**Token rules for research agents (CLAUDE.md Token budget):** each agent writes its note straight to a file under
`Research-Context/research_notes/<topic>/` and replies in ≤300 words with the file path; the main session never reads an
agent's raw output file. At most 4 agents unless the user asks for more. Merge the notes into the research doc with a
script or one agent, not by reading them in the main session.
