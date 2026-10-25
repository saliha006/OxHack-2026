# HRT question bank: what we built, and why

*For the judging table (HRT: Best Use of Data for Predictions & Decision Making). Each answer is what to say in about 20 seconds, then where the detail lives. Written 2026-10-25 ~10:00 UTC from `main` @ `abf0e19`; the full spec is the PRD (v4). Numbers marked **[10:00]** are a snapshot: the merged eval table goes in `progress.md` → 📊 Latest and the README.*

---

## 1. The 30-second pitch

"Our agent plays Pokémon Showdown, a game with hidden information: you can't see the opponent's items, abilities or Tera types. Every turn it **predicts** what's hidden, using usage statistics from real players and what it has seen so far. It then **decides** by searching 8 different versions of the game that fit its prediction and picking the move that does best across all of them. We show both halves live in the battle chat, and we measured both: the decisions head to head against other bots with confidence intervals, the predictions against simple baselines on held-out games."

**Talk track (4 minutes; matches PRD §18):**
1. **0:00 Hook:** the pitch above, one sentence.
2. **0:30 Live battle:** open the battle room. Point at one chat line and read it: what it played, what it's weighing, what it expects, what it guesses is hidden.
3. **1:45 Decisions:** the eval table. Same team on both sides, Wilson intervals, vs SimpleHeuristics and vs Foul Play at ladder strength.
4. **2:30 Predictions, honestly:** guess accuracy, belief scoring and the win-probability model against their baselines. Say plainly where we don't beat the baseline yet.
5. **3:15 Limits and next steps:** bot opponents, one format, no ladder Elo; next is team-conditioned priors. One line: all code is ours; the sampled-worlds idea comes from Foul Play, and two levers we tested come from Laplace.

---

## 1b. The whole system in plain words *(read this first if you're new, or if you've missed the last few hours of changes)*

Pokémon Showdown hides most of the opponent's team: you see the six Pokémon, but not their items, abilities, exact moves or Tera types. Our agent plays it the way a good player does: guess what's hidden, then pick moves that still work if the guess is a bit off. Three parts do that, built by different people and joined by small written contracts.

The **data layer** works before any battle. It turns Smogon's monthly usage statistics into a list of likely builds ("sets") for every Pokémon in the format (243 species, up to 30 weighted sets each), and loads 2.5 million public replays into a shared Postgres database, cut into 489,840 turn-by-turn positions for training and testing prediction models.

The **bot layer** is the connection to the game. Every message from the Showdown server goes through our own parser, which keeps an exact picture of the battle (HP, status, boosts, hazards, every move and item revealed). When the server asks for a move, the bot hands that picture and the legal options to the strategy layer. It then sends the answer back, logs everything, and posts the reasoning to the battle chat.

The **strategy layer** decides:
1. It keeps a **belief** about each opposing Pokémon's hidden set. That belief starts from the data layer's usage statistics and is updated every turn:
   - Reveals rule sets out.
   - Clues narrow them, e.g. no Stealth Rock damage on entry means Heavy-Duty Boots.
   - Replaying the last turn down-weights any set that can't explain what happened.
2. It draws **eight complete guesses** of the opponent's team from that belief.
3. It runs 150 ms of tree search in each guess with the `poke-engine` simulator.
4. It plays the move that was favoured most across all eight.
This runs in its own process under a hard three-second deadline, so a slow turn can never lose a game on time.

Around that, two offline layers keep us honest. **Prediction** scores the belief and a win-probability model on games they never saw. **Evaluation** plays hundreds of same-team games against other bots, and reports every win rate with an interval.

The changes since the start, in one line each:
- The first strategy layer looked one turn ahead and lost to strong bots, so Kenar's tree search replaced it this morning.
- The demo now shows its reasoning in the battle chat.
- The eval now measures the tree-search bot against Foul Play at ladder strength.
- The demo pins `team_6.txt`.

---

## 2. Using data to predict

**Q: What exactly are you predicting?**
Each opponent Pokémon's hidden **set**: its moves, item, ability, nature/EVs and Tera type. In the chat that's the `Guessing their X: item (n/8 worlds) · Tera type` line. Separately, offline, we built a model of **P(we win)** from the public board state. (PRD §7.2, §7.3)

**Q: Where does the prediction come from?**
Two data sources, combined:
1. **Prior:** Smogon's monthly usage stats for gen9ou (September 2026, players rated 1825+), turned into up to 30 weighted candidate sets per species (`data/set_candidates.json`, 243 species).
2. **Evidence in the battle:** every revealed move, item, ability or Tera rules sets out (a hard filter). We also replay each turn in the simulator: if a set can't explain the damage or move order we saw, its weight drops to 3% instead of zero.
(PRD §7.2, §9)

**Q: Why a floor of 3% and not zero?**
Rounding, unusual spreads, or a set missing from the stats would otherwise wipe out the right answer forever. A floor lets a set come back when later turns fit it. Same idea as Foul Play's belief. (PRD §7.2)

**Q: How do you know the predictions are any good?**
We score them, and we report the result even when it's bad:
- **Win probability:** a logistic model with Platt calibration on public replays, chronological train/test split. It currently **loses** to a simple HP-difference heuristic (log loss 0.6600 vs 0.6348). We don't use it in the bot, and we say so.
- **Set belief:** next-reveal log loss (how surprised the belief is by the next thing revealed). In the pilot the **prior beat the updated belief** (2.71 vs 3.08), so in-battle updating isn't yet shown to help.
- **Guess accuracy in today's demos:** 48–65% of guessed items and 20–57% of guessed Tera types were right, depending on the team. One battle per team, so treat this as a spot check. **[10:00]**
(PRD §17)

**Q: Your prediction model is worse than the baseline. Isn't that a failure?**
It's a measured result, and the honest part of the project. Calibrated win probability in Pokémon is hard: the HP heuristic is a strong baseline and our public study was small (96 games). What we did right is the method: held-out test games after the training period, a baseline, calibration, and not shipping the model into the bot just because it exists. Next step: more training data from our Tiger tables (489,840 turns from 20,000 games). (PRD §7.3)

**Q: Are the percentages in the chat ("Weighing: Flip Turn 20%") win probabilities?**
No. They're **MCTS visit shares**: how much of its search time the bot spent on each option, pooled over 8 worlds. They show what it's weighing, not calibrated chances. We never call them probabilities. (PRD §2, §22)

**Q: Did you try better priors?**
Yes, two, both opt-in:
- **Coherent priors** (Kenar): Showdown's curated role sets mixed 50/50 with usage. Predictions improved slightly (next-reveal loss 4.05 → 3.71), but play didn't: 25 wins, 35 losses in a 60-game screen. So it stays off.
- **Observed-set priors** (Saliha; code name "joint"): complete sets actually observed from Foul Play, blended 75/25 with usage. Being tested today (`mcts8joint`).
(PRD §9; `coherent-sets.md`)

**Q: What are observed-set priors, and why did you build them?** *(code name: "joint", e.g. `mcts8joint`, `data/set_candidates_joint.json`)*
- **The problem:** usage stats list each field separately (how often a Pokémon runs each move, item, Tera type and spread). Building a set by picking each field independently also builds sets **nobody actually brings**, like a Choice Scarf alongside a setup move. The belief then wastes weight on impossible sets.
- **The data:** Foul Play publishes counts of **complete sets seen on the ladder** (`pokemon_full_sets.json` from data.foulplay.cc). Each entry keeps moves, item, ability, Tera type, nature and EVs together, exactly as a real player brought them.
- **How we built it (`data/pipeline/joint_sets.py`):**
  1. Parse every observed set.
  2. Drop any without a Tera type or a full EV spread, because the simulator can't build those.
  3. Weight each set by how often it was seen.
  4. Blend **75% observed sets with 25% usage sets** (Foul Play's own split), so rare sets the ladder data missed still have a chance.
  5. Keep up to 30 sets per species, in the same file format as the default priors, so the belief loads it with no code change.
- **How we use it:**
  - Opt-in for the demo: `--priors data/set_candidates_joint.json`.
  - In the eval: the `mcts8joint` arm, head to head with today's bot and against Foul Play.
- **Why count weights and not equal weights:** Kenar's earlier coherent mixture gave every template equal weight, which piled too much belief onto a few templates. Count weights follow how often players really bring each set.
- **Result so far [10:00]:** 4–7 against Foul Play `fphard` on this laptop. No head-to-head win over today's bot yet, so by our rule it stays off. It's a better-shaped prior that isn't yet shown to win games.

**Q: How is that different from the coherent priors?**
- **Coherent priors:** Showdown's **curated** role sets (what experts recommend), mixed 50/50 with usage.
- **Observed-set priors:** what players **actually brought** on the ladder, weighted by how often, mixed 75/25.
Both fix the same problem (sets that don't hang together), from different data.

**Q: What would improve prediction most?**
**Team-conditioned priors (A6):** predict a Pokémon's set from the other five on its team, because teams are built around each other. Agreed by the team, built after the demo by Nate. Right now each Pokémon is guessed independently. (PRD §0)

---

## 3. Using data to decide

**Q: How does the bot pick a move?**
1. Sample **8 complete guesses** of the opponent's team ("worlds") from the belief.
2. In each world, run **150 ms of Monte Carlo tree search** in `poke-engine`, a fast Rust simulator of the real game.
3. Pool the results: normalise each world's root visit counts, weight the worlds equally, and play the action that wins on average.
It all happens inside a 3-second budget. (PRD §7.1)

**Q: Why search over several sampled worlds instead of one best guess?**
A single guess is overconfident: if the opponent has a Choice Scarf and we assumed Leftovers, the plan fails. Searching across 8 plausible worlds picks moves that hold up whatever the hidden sets turn out to be. This is the approach that made Foul Play strong; we adapted it. (PRD §7.1, Appendix B)

**Q: Why 8 worlds × 150 ms?**
It fits the 3 s turn budget with a safety margin: median ~1.4 s per decision, slowest ~2.0–2.5 s in today's demos **[10:00]**. Fewer, deeper worlds (4 × 300 ms) is an arm we built to test that trade-off. (PRD §7.5, §13)

**Q: Why did you switch from your first design?**
We started with a one-ply search: simulate one turn for each pair of moves and score the result with an HP heuristic. It beat the SimpleHeuristics bot (71.6% over 95 games) but lost badly to Foul Play (5–8%). MCTS looks many turns ahead. Kenar built it, the team agreed to make it the default, and `one_ply` stays as a comparator. (PRD §0, §7.1)

**Q: What stops it from timing out and losing?**
Search runs in a **separate worker process** with a hard deadline. Worlds that would overrun aren't started, a stalled worker is killed and replaced, and any error plays the first legal move. Fallbacks are counted per game, and the smoke test fails above 5%. In the MCTS pilot, 7,863 of 7,863 worlds were usable, with no decision over 3 s. (PRD §7.1, §15)

**Q: Is there an LLM anywhere?**
No. Every decision is search over a real game simulator with a probabilistic belief. (PRD §8)

---

## 4. Measuring it

**Q: How do you know the win rate isn't just a strong team?**
Every game puts the **same team on both sides**, and adjacent games swap sides. So the win rate measures how well the bot plays, not which team it got. (PRD §7.5)

**Q: How do you know it isn't luck?**
We report a **Wilson 95% interval**, which behaves well at small samples, plus a bootstrap over teams. For any change to the bot we set the bar in advance: a new flag turns on only if its arm beats the current bot head to head with the **lower bound above 50%**. (PRD §0, §7.5)

**Q: Who did you play against?**
- **SimpleHeuristics:** poke-env's standard rule-based bot. It's the demo opponent and the headline baseline.
- **Foul Play at `fphard`:** a strong open-source search bot, run at about ladder strength (4 parallel searches, 900–1100 ms per decision). It's the hard test.
- **Our own variants**, head to head.
(PRD §7.5)

**Q: What are the results?** **[10:00]**
- **vs Foul Play `fphard`** (this laptop): today's bot 2–2; observed-set priors 4–7. The research estimate before testing was 25–40%.
- **4 engine threads vs today's bot:** 11–3 on Nate's laptop (Wilson 52.4–92.4%). That passes our bar, but only barely.
- **Demo battles vs SimpleHeuristics:** won all 7 today, in 19–47 turns; the three with `team_6.txt` took 19–23. These are informal; the `mcts-headline` eval is the real number.
- Fill the merged table from `progress.md` → 📊 Latest.

**Q: How did you run hundreds of games in a weekend?**
The eval shards across our laptops. Each machine plays a seeded, shuffled schedule and writes one line per game. Reruns skip finished games, and the report merges every machine's files. A manifest fingerprints the code, priors and teams, and refuses to mix results from different code into one folder. (PRD §5 Flow B)

**Q: You picked the demo team. Isn't that cherry-picking?**
For the live demo, yes, and we say so. We picked `team_6.txt` because, across every source we had, it won most often, finished fastest (most games in 35 turns or less) and had the most accurate set guesses. The win rates we **report** are across all teams, never the best team's. (PRD §2, §20)

---

## 5. System architecture

**Q: Walk me through the architecture.**
Four layers:
- **Data (offline):** 2.5M public replays → cleaned with DuckDB → per-turn Parquet → a shared Postgres database ("Tiger"). Usage stats → candidate sets.
- **Bot:** a poke-env player connects to a local Showdown server and feeds every protocol line to our parser. The parser builds a `BattleState` and calls `agent.choose(request, state)`.
- **Decision:** belief → 8 worlds → MCTS in a worker process → pooled choice.
- **Output:** the choice goes back to the server. Each decision is written to a trace file, printed in the terminal and posted to the battle chat.
(PRD §10)

**Q: Why a local Showdown server?**
No account, no rate limits, and no risk of breaking the public server's bot policy. Playing the public ladder needs a registered bot account, which is our clearest demo-vs-product gap. (PRD §4, §14)

**Q: Why one parser for live play and for training data?**
So that what the model learns from is exactly what the bot sees live. `states_from_log` turns a saved replay into the same `BattleState` the live bot builds; Tiger's `turns` table was built with it. (PRD §7, §11)

**Q: Why Parquet + DuckDB + Postgres?**
DuckDB and Parquet need no server and handle millions of rows on a laptop. Postgres gives the whole team one shared, read-only copy of the training tables. A bigger system like ClickHouse was overkill for this size. (PRD §0, §12)

**Q: Why put search in a separate process?**
So a deadline is truly enforceable. A stuck native search can be killed without taking the battle down, and the belief lives in that worker across turns. (PRD §7.1)

**Q: How do the four of you work without breaking each other?**
Written contracts at each seam (`BattleState`, set candidates, the Tiger turns table), one owner per folder, and a shared progress board where anyone changing someone else's area flags it first. (`contracts/`, `progress.md`)

---

## 6. Layer by layer: what we built, how it works, and why

### One turn, start to finish
1. **Showdown** sends protocol lines (what just happened), then a **request** (our legal options right now).
2. **Bot layer:** our parser has already folded every line into a `BattleState`. The bot hands the request and the state to `agent.choose`.
3. **Decision (strategy) layer:** the search worker updates its belief about the opponent's hidden sets, samples 8 complete opponent teams, searches each for 150 ms, pools the results and returns a choice such as `move 2`.
4. **Bot layer:** sends `/choose move 2` to Showdown, writes the trace, prints the terminal block and posts the chat line.
5. **Data layer** supplied the priors (step 3's starting belief) before the battle began. The **prediction** and **evaluation** layers work afterwards, from saved traces and results.

### Data layer *(Nate; opt-in priors from Kenar and Saliha)*
**What we built**
- **Priors:** Smogon chaos stats (gen9ou-1825, September 2026) → `data/set_candidates.json`: 243 species + 78 forme aliases, up to 30 weighted sets each.
- **Replay pipeline:** 2.5M HolidayOugi replays → `clean_battles` (DuckDB) → `build_turns` (Parquet, built with the live bot's parser) → `load_tiger` (Postgres tables `battles`, `battle_logs`, `turns`). The `turns` table is specified in `contracts/turns.md`.
- **Opt-in priors:**
  - `curated-v1`: Showdown's curated role sets mixed 50/50 with usage (Kenar).
  - Observed-set priors: complete sets observed from Foul Play, blended 75/25 (Saliha).

**How it works, step by step**

*Priors (once per stats month):*
1. Take Smogon's chaos file for gen9ou-1825. For every species it says how often each move, item, ability, Tera type and EV spread is used.
2. `build_set_candidates.py` builds candidate sets from the common options and weights each set by **multiplying the usage shares of its parts**. It keeps the top 30 per species and normalises the weights to sum to 1. Forme aliases point to their base entry (e.g. `keldeoresolute → keldeo`). The raw usage block is kept so the belief can rebuild sets if every candidate is ruled out.
3. A contract test checks the file against `contracts/set-candidates.md` before anyone uses it.

*Replays (once):*
1. `clean_battles.py` cleans the raw replay Parquet files with DuckDB, one cleaned file per input, logs kept.
2. `build_turns.py` runs every game through the **live bot's parser** (`states_from_log`) and writes one row per turn: the public board state, all 12 Pokémon with HP and status, the actions taken, and the winner.
3. `load_tiger.py` loads `battles`, `battle_logs` and `turns` into Postgres. Rows join on battle ID **and** start time, so two games can't be mixed up.
4. Split by time: 15,000 games from 2025-01-01 for training, 5,000 from 2026-05-19 for testing. Teammates read it with read-only logins.

**Why**
- Usage stats are the biggest public signal of what real players run, so they're the prior for every prediction. The 1825+ cutoff favours competent, standard sets.
- DuckDB + Parquet handle millions of rows on a laptop with no server. Postgres gives four laptops one shared, read-only copy.
- Training states are built with the **same parser** the live bot uses, so the model never learns from a different picture than it plays with.
- The split is by time (test games from 2026-05-19 on), so we test on later games than we trained on.

**What we rejected**
- ClickHouse: overkill at this size.
- Scraping Showdown's API: load on public infrastructure.
- Metamon's parsed replays: they back-fill hidden information from the end of the battle, which leaks the answer.

### Bot layer *(Saliha)*
**What we built**
- **`AgentPlayer`,** a poke-env player. It feeds every raw protocol line to **our own parser** (`bot/parser.py` → `BattleState`) *before* handling the request, then calls `agent.choose(request, state)` once per decision, with one `Agent` per battle. A rejected choice is resent as the first legal option, then `default`.
- **Per-battle records:** raw protocol (`.log`), one trace line per decision (`.jsonl`) and a decision log.
- **Demo:** each decision is streamed to the terminal and posted as one line in the battle chat, paced at 1.5 s so a viewer can follow. Replay mode re-runs a saved trace offline.
- **Smoke test:** fails a run if more than 5% of moves are fallbacks.

**How it works, step by step** (one battle)
1. `bot.demo live` creates two poke-env players on the local server, ours ("oxhack demo") and the opponent ("oxhack rival", SimpleHeuristics). Both get the same team, and ours sends the challenge.
2. For every message from the server, our player first feeds each line to `Parser.feed`. The parser tracks HP, status, boosts, hazards, screens, revealed moves and items, and so on. Only then does poke-env handle the message.
3. When a request arrives, the player takes `Parser.snapshot()` (the `BattleState`) and calls `agent.choose(request, state)`, blocking, inside the 3 s budget.
4. It sends the answer as `/choose move 2`, or `/choose team 123456` at team preview. If Showdown rejects it, it resends the first legal option, then `default`.
5. It writes the trace line, the raw log and the decision log. Then it calls the demo hook: print the terminal block, post one chat line to the battle room, wait 1.5 s.
6. At the end it prints a summary: result, turns, fallbacks, and think time p50/p99.

**Why**
- poke-env gives us standard baseline bots and concurrent battles for free.
- Parsing first means the state is up to date when we decide.
- Owning the parser lets the same `BattleState` serve live play and offline training data.
- The traces make every decision auditable after the fact.
- The battle chat puts the bot's reasoning beside the board, for the judge. It replaced a browser side panel we cut for time.
- A local server needs no account and has no rate limits.

**What we rejected**
- A fresh process per turn: it would lose the belief between turns.
- Our own websocket client: a fallback plan we never needed.
- A browser side panel: cut for time.

### Decision (strategy) layer *(Derrick built v1; Kenar built the MCTS that replaced it)*
**What we built**
- **v1, one-ply (Derrick):**
  - Belief → 5 likely scenarios → simulate one turn for every pair of moves in `poke-engine` → score with an HP/alive heuristic → best expected value.
  - Plus a type-matchup lead at team preview, forced-switch handling, and the 3% belief floor.
- **v2, MCTS (Kenar, the default since 07:01):**
  - A worker process keeps the belief and samples **8 whole-team worlds**.
  - It runs **150 ms of native MCTS** in each world, then pools normalised visit shares across worlds.
  - It works under a supervised 3 s deadline.
- **Opt-in experiments:** 4 engine threads, a Tera gate, near-tie mixing, deeper/fewer worlds, observed-set priors.

**How it works, step by step** (one turn, MCTS)
1. **Team preview:** no search. The type-matchup lead (`decision/lead.py`) picks our opening Pokémon from type matchups against the opponent's six.
2. **Every other request:** `Agent.choose` hands the request and the `BattleState` to the battle's **search worker**. That's a separate process that lives for the whole battle and holds the belief.
3. **Update the belief** with what just happened:
   - **Hard filter:** drop any candidate set that contradicts a revealed move, item, ability or Tera type.
   - **Item inference:**
     - Took no Stealth Rock damage on the way in → Heavy-Duty Boots (or Magic Guard).
     - Used a status move → not Assault Vest.
     - Used two different moves since switching in → not a Choice item.
     - Damaged but no Leftovers healing at the end of the turn → not Leftovers.
   - **Replay check:** replay the last turn in poke-engine for each candidate set. Does it explain who moved first and how much damage was dealt? If not, its weight is multiplied by 0.03 rather than set to zero.
   - **`reliable` mode** skips the replay check where it's unreliable: forced moves, item changes, ability suppression.
   - **Nothing survives?** Rebuild from usage, then relax the inferred rules, then reconstruct a set from the revealed facts.
4. **Sample 8 worlds:** for each of the opponent's six Pokémon, draw a set from its belief with a seeded random generator. That gives 8 complete opponent teams. Likely sets appear in more worlds.
5. **Search each world:** build a poke-engine state (our side exactly as the request describes it, theirs from the world) and run **150 ms of MCTS**, which explores both players' choices turn by turn. Results stream back as each world finishes; a world that would run past the deadline isn't started.
6. **Pool:** turn each world's root visit counts into shares, average them across worlds, and map the engine's move names onto the request's legal options. Pick the highest share; ties go to request order. These pooled shares are the "Weighing" line in the chat.
7. *(Opt-in, off by default)*
   - **Tera gate:** keep a Tera move only if it's the outright top choice in at least N worlds; otherwise play the best non-Tera option. Tera is once a game, so averaging shouldn't spend it on a move that's merely everyone's runner-up.
   - **Near-tie mixing:** sample among almost-equal options.
8. **Return** the choice. Any error → the first legal option. A stalled worker is killed and replaced. Both count as fallbacks.

**Budget:** 3 s per decision, with 0.3 s held back to return the answer; typical think time is about 1.4 s.

**The one-ply comparator (v1),** for contrast: take the top 5 sets for the opponent's active Pokémon, simulate one turn for every pair of moves, score each outcome by remaining Pokémon and HP, assume the opponent picks uniformly, and play the best average.

**Why**
- One-ply beat SimpleHeuristics (about 72%) but lost to Foul Play (5–8%), so we needed lookahead.
- `poke-engine`'s native MCTS is fast and handles the real game rules.
- Sampling worlds from the belief is how we turn the prediction into a decision that holds up when we don't know the opponent's sets.
- The worker process makes the deadline enforceable.
- Each experiment ships only if it beats the default head to head with a Wilson lower bound above 50%.

**What we rejected**
- A learned value inside search: native MCTS can't call it without a Rust fork, and our model doesn't beat the HP heuristic yet.
- A maximin LP selector: no gain against fixed bots.
- poke-engine's expectiminimax: its payoff matrix is NaN where pruned, so it can't feed the LP.

### Prediction layer *(Kenar)*
**What we built**
- **`prediction/`:**
  - A logistic win-probability model with Platt calibration on public-state features.
  - Chronological splits grouped by battle, with "unseen player/team" controls.
- **Scoring:** next-reveal log loss for the set belief; action scoring.

**How it works, step by step**

*Win-probability model (`python -m prediction train`):*
1. Turn each game's turns into `BattleState`s with the same parser the bot uses.
2. For each turn, compute **features as differences between the two sides' public board state**: Pokémon alive, total HP, active HP, statused Pokémon, Tera still available, revealed moves, stat boosts, hazards, screens, volatile effects (Substitute, Taunt, …), Wish and Future Sight. Add the turn number and Trick Room. The schema is shared by training and serving, so they can't drift apart.
3. Split **chronologically, grouped by battle**: every turn of a game stays in one split, so the model can't see the end of a game it's tested on. "Unseen" controls hold out players and teams.
4. Fit logistic regression on train, calibrate it with **Platt scaling** on validation, and score on test: log loss, Brier and a reliability diagram, against the HP heuristic and a constant.

*Belief scoring (`python -m prediction score-beliefs`):*
1. Replay games turn by turn through the belief.
2. Just before each new reveal, record the probability the belief gave to what was then revealed.
3. Average the log loss over reveals. Compare the prior, hard-filter-only and the full updated belief.

**Why**
- HRT asks whether predictions are honest, so we built the measurement first: held-out games, a baseline, calibration.
- We kept it **out of the bot**, so a weak model can't cost games.

**Result:** neither the model nor the updated belief beats its baseline yet, and we report that (section 2).

### Evaluation layer *(Saliha)*
**What we built**
- **`bot/eval.py`:**
  - Same team on both sides, with sides swapped.
  - A seeded, shuffled schedule, sharded across laptops; reruns skip finished games.
  - A manifest that refuses to mix results from different code.
  - Wilson 95% intervals plus a team bootstrap, and an internal Bradley–Terry Elo.
- **Opponents:** SimpleHeuristics, Foul Play at four strength levels (up to `fphard`), and our own variants head to head.

**How it works, step by step**
1. A **pairing** is two arms plus a planned game count, e.g. `mcts-headline` = `mcts8` vs SimpleHeuristics.
2. `bot.eval run` lists the games not yet played, shuffles them with the machine's seed and splits them across shard processes.
3. Each game's **team** comes from the seed. Both sides get that team, and adjacent games swap who challenges, which swaps sides.
4. For a Foul Play opponent, it starts a Foul Play process with that game's team, a search time drawn from the level's band (900–1100 ms for `fphard`) and its parallelism.
5. When the game ends, it checks the game really completed and appends one line: arms, team, side, winner, turns, compute settings, fallbacks, think times.
6. `bot.eval report` merges every machine's files and, per pairing, prints wins/games, the Wilson 95% interval, a team bootstrap, the fallback rate, think-time p99 and Elo.
7. Before any run, the **manifest** is compared with the folder's: different code, priors, teams or arms → it refuses to continue.

**Why**
- It measures play rather than team strength.
- The intervals are honest about small samples.
- Foul Play gives a strong, public reference point.
- The pre-set flag rule stops us from shipping a lucky streak.

---

## 7. Data

**Q: How much data, from where, and how did you split it?**
- **Replays:** 2,506,142 public battles (HolidayOugi's Showdown replay dataset).
- **Training turns:** 489,840 turns from 20,000 games: 15,000 games from 2025-01-01 for training, 5,000 games from 2026-05-19 for testing. The split is by time, so the model is tested on later games than it learned from.
- **Usage stats:** Smogon gen9ou-1825, September 2026.
(PRD §9; `DATA-CONTEXT.md`)

**Q: Any leakage?**
We split by time and by battle. To be upfront: 43% of test players also appear in training, so the test isn't player-disjoint. We report that rather than hide it, and the prediction package has an "unseen" subset control. (`DATA-CONTEXT.md`)

**Q: Why only 1825+ rated usage stats?**
Higher-rated players use more consistent, standard sets, which makes better priors for a bot facing competent play. Removing the cutoff was proposed and is a separate rebuild. (PRD §9)

**Q: Licences and privacy?**
Public, pseudonymised replays and public usage stats only. Nothing personal is stored, raw data is never committed, and the database logins live outside git. (PRD §14)

---

## 8. Stats and quant deep-dive

**Q: How many games do you need to trust a difference?**
At 50%, a Wilson 95% interval is about ±10 points at 100 games and about ±5 points at 400. So 100 games can tell 50% from 70%, but not 50% from 55%. That's why we only act on a lower bound above 50%, and why small effects (threads, Tera gate) need longer runs than one morning gave us.

**Q: You tested several variants. Couldn't one pass by chance?**
Yes, and that's the multiple-comparisons risk. Each check is roughly a one-sided 2.5% test. With three candidate flags, the chance that at least one passes by luck is about 7%. We set the rule before the runs, and the one that passed (4 threads, lower bound 52.4%) passed only just, so we'd confirm it with a fresh run before calling it real.

**Q: Did you stop runs when the numbers looked good?**
No. Every slice had a fixed stop time (09:45 UTC) set in advance. One teammate stopped early because of a mix-up in instructions, and we resumed him to the planned time rather than keep a convenient stopping point. Stopping when the result looks good inflates false positives.

**Q: Why Wilson and not the usual ± formula?**
The normal approximation breaks at small samples and near 0% or 100%: it can give intervals below 0 or above 1. Wilson stays inside [0, 1] and has better coverage at the sample sizes we have. The team bootstrap adds a second view: it resamples teams, because some teams favour our bot more than others.

**Q: Why log loss and Brier for the win-probability model?**
- **Log loss** punishes confident wrong predictions hard, which is what you want from a probability you'd act on.
- **Brier** is the mean squared error of the probabilities: less dominated by a few extreme misses.
- **A reliability diagram** shows calibration directly: of the times we said 70%, did we win about 70%?
Accuracy alone would hide all of this.

**Q: Your 8 worlds get equal weight. Shouldn't likelier worlds count more?**
They already do. Worlds are **sampled in proportion to the belief**, so likely sets show up in more worlds. Giving each sample equal weight is ordinary Monte Carlo averaging. Weighting them again by probability would double-count.

**Q: What assumptions are you making that might be wrong?**
- **Each opponent Pokémon is guessed independently.** Real teams are built around each other, so that's the biggest known gap; team-conditioned priors (A6) fix it.
- **The metagame is stable over the month.** We use September's usage stats for October games. They need refreshing monthly.
- **Usage stats represent our opponents.** True for ladder players. Bot opponents like SimpleHeuristics don't care.

**Q: The game has simultaneous moves. How do you handle that game-theoretically?**
Inside each world, the search explores **both** players' choices every turn, so the opponent's best replies are part of the search, not assumed. We don't compute a mixed-strategy equilibrium. A maximin LP was designed and cut: against fixed bots it can't beat taking the best average. Against adaptive humans, mixing would matter more. Near-tie mixing is built and opt-in.

**Q: Why might the updated belief do worse than the prior?**
We don't know yet; these are hypotheses, not findings:
- The damage and speed replay may cut correct sets on noisy evidence; the 3% floor softens this but doesn't remove it.
- Next-reveal scoring only tests what gets revealed, which may be the hardest-to-predict facts.
The fix is to measure each inference rule separately. Kenar's `reliable` mode already skips the unstable cases.

**Q: Is it reproducible?**
Yes. World sampling uses a fixed seed (2026), every eval machine has its own schedule seed, and the eval manifest records the engine version, code hash, priors hash and team hashes for every results folder.

**Q: How does this connect to trading?** *(say it as an analogy, not a claim)*
The shape of the problem is the same:
- **Hidden state:** we build a belief over it from public signals, starting from base rates and updating on evidence.
- **Decisions that hold up under that uncertainty:** we optimise across several plausible scenarios, not one point estimate.
- **A hard latency budget** with a safe fallback.
- **Out-of-sample evaluation** with intervals and a decision rule fixed before looking.
We'd never claim the bot itself says anything about markets.

---

## 9. Demo-time questions

**Q: What am I looking at in the chat?**
Each line is one decision:
- `Turn N · <move> (think ms)`: what it played and how long it thought.
- The HP of both active Pokémon and how many each side has left.
- `Weighing:` our top options by share of search.
- `Expects them:` what it thinks the opponent will do.
- `Guessing their X:` its best guess of the hidden item and Tera type, with how many of the 8 worlds agree.

**Q: Why did it just switch out?**
Because across the 8 worlds, staying in did worse on average than switching. Read it off the `Weighing` line: the switch got the biggest share of search.

**Q: What does "4/8 worlds" mean?**
Search reported back from only 4 of the 8 worlds. Worlds that would have run past the deadline aren't started, so on a slow turn fewer finish. The decision still comes from the worlds that did finish.

**Q: What if it loses this game?**
Then it loses. One game is one sample, which is why we show the eval table. Against SimpleHeuristics it won every demo game today, but the honest number is the interval from the eval.

**Q: Who is it playing?**
SimpleHeuristics, poke-env's standard rule-based bot, with **the same team** on both sides. The team is pinned to `team_6.txt` for the demo (section 4 says why).

**Q: Why does it pause between turns?**
On purpose: a 1.5 s pace after each decision, so the audience can read the chat. Thinking itself takes about 1.4 s.

---

## 10. Engineering and teamwork

**Q: How did four people build this in a weekend without stepping on each other?**
- One owner per folder: bot (Saliha), data (Nate), decision (Derrick, then Kenar's MCTS).
- Written contracts at every seam: `BattleState`, the set-candidates file, the Tiger `turns` table.
- A shared progress board: anyone touching someone else's area posts a flag first.
- Each person works on their own branch, merges one feature at a time, and logs it.

**Q: How do you know the code works?**
- Every layer has a pytest suite with coverage (counts in `progress.md` → 📊 Latest).
- A smoke test plays full games and fails on too many fallbacks.
- The eval checks that every game really completed.
- The parser was tested on public replays: a known turn must equal a hand-checked example.

**Q: What went wrong, and what did you learn?**
- **Our first bot didn't search deep enough.** One-ply beat the easy bot but lost over 90% of games to Foul Play, and the switch to MCTS came from that measurement.
- **Old eval labels hid which bot was measured.** The early `headline` numbers were the one-ply bot; we split the MCTS pairings out so nobody quotes the wrong number.
- **Mixing code versions in one results file is easy.** The manifest guard caught it this morning, and we resumed only after checking the arms we were testing hadn't changed.
- **Live chat for guests needed a small local server patch.** Without it, the judge sees nothing.

**Q: What did each person own?**
- **Saliha:** bot layer, eval harness, demo, docs.
- **Derrick:** decision layer v1 and the belief floor.
- **Nate:** priors, replay pipeline and Tiger.
- **Kenar:** MCTS, prediction studies and the coherent priors.

---

## 11. Hard questions

**Q: Isn't this just Foul Play?**
No. Every line of our bot is our own code. We studied two open-source bots and took **ideas**, not code. The core idea we share with Foul Play is searching several sampled versions of the opponent's team. Everything around that idea is ours, and different (next question).

**Q: How is it different from Foul Play (the `fphard` opponent) and Laplace?**
First, `fphard` isn't a separate system: it's Foul Play at the strongest setting we run, 4 parallel searches at 900–1100 ms each, about ladder strength. It's the opponent we measure against.

| | **Ours** | **Foul Play** | **Laplace** |
|---|---|---|---|
| Code | written by us | its own | its own |
| What it believes about hidden sets | an **explicit weighted belief** per opponent Pokémon, updated every turn: hard filter on reveals, item inference, damage and speed replay with a 3% floor, guarded `reliable` mode, **scored** against the prior | samples whole sets from its team datasets (uniformly, ignoring how often each was seen), then partial team sets, then Smogon sets | — |
| Where the prior comes from | **our own pipeline**: Smogon usage stats → candidate sets; optional observed-set blend **weighted by how often each set was seen** | its own team datasets | — |
| Search per turn | 8 worlds × 150 ms, 1 thread: about **1.2 CPU-seconds** | 4 worlds (8 early in the game) × 900–1100 ms: about **4–8 CPU-seconds** | 8 worlds, **8 engine threads each** |
| Combining worlds | equal weight (worlds are already drawn in proportion to the belief), **top move** | weighted by sample chance, then **samples among near-best moves** | plain average, with a robust "world-winners" vote option; samples among near-ties |
| Tera | searched like any other option; gate is opt-in, off | — | Tera only if it tops **2 of 8 worlds** |
| Deadline | separate **worker process** with a hard 3 s deadline: stalled search is killed and replaced, unfinished worlds aren't started | time per search | — |
| Shows its reasoning | **every decision in the battle chat** + full trace | no | no |
| Measured | same-team eval with Wilson intervals; prediction scored against baselines on held-out games | self-reported ladder results | — |

*"—" = not something we checked; we don't claim either way.*

**What that means in plain words:**
- Our edge is in **knowing what we don't know**: an explicit, measured belief, built from our own data pipeline, which you can watch live.
- Foul Play's edge is **raw compute**: about 3–6× more search per turn than ours.
- Laplace's levers (more threads, the Tera gate) are things we **tested** as opt-in arms under a rule set before the runs, rather than adopted on faith. The thread lever is the only one that has cleared the bar so far, barely.

**Q: So which parts are yours, and where do the borrowed ideas sit?**
One decision, in order. Everything here is our code; the tag says where the **idea** came from.

| Step | What happens | Idea from | Why it's there |
|---|---|---|---|
| 1. Read the game | Parser turns Showdown's protocol into `BattleState` | **ours** | One state for live play and training data |
| 2. Starting guess | Priors from our Smogon pipeline; optional observed-set blend | **ours**; blend uses Foul Play's **published data** | Usage stats are the best public signal of what players run |
| 3. Update the guess | Hard filter, item inference, damage/speed replay with a 3% floor, `reliable` guards, recovery chain | **ours** | Narrow the hidden sets without wiping out the right answer |
| 4. Sample worlds | Draw 8 complete opponent teams from the belief | **Foul Play** (the idea) | Decide against several plausible teams, not one guess |
| 5. Search | 150 ms of poke-engine MCTS per world | **Foul Play** (the idea); `poke-engine` library | Look many turns ahead in each world |
| 6. Combine | Average the normalised visit shares across worlds; top move | **Foul Play** (averaging); our own pooling and legal-action mapping | Monte Carlo estimate of the best move under the belief |
| 7. Optional levers | 4 engine threads; Tera gate; near-tie mixing | **Laplace** (threads, Tera gate); Laplace and Foul Play (mixing) | Each tested head to head, off unless it clears our rule |
| 8. Stay on time | Worker process, hard 3 s deadline, kill and replace, fallback | **ours** | Never lose a game to a timeout |
| 9. Show it | Trace + terminal block + battle-chat line per decision | **ours** | Judges see the belief and the reasoning live |
| 10. Prove it | Same-team eval, Wilson + bootstrap, manifest guard, prediction scoring | **ours**; Foul Play is the **opponent** | Numbers we can defend |

**In one line:** the frame "sample worlds, search each, average" is Foul Play's idea. What goes into it (the belief and its data), what keeps it safe (deadline and fallbacks), what it shows (the chat), and how we know it works (the eval) are ours. Laplace's two levers are experiments we run under our own rule.

**Q: Did you use anything from them directly?**
- **No code.**
- **Data:** our opt-in observed-set priors read Foul Play's **published** counts of sets seen on the ladder, the way we read Smogon's usage stats.
- **Libraries:** the engine, `poke-engine`, is an open-source library (written by Foul Play's author), used the way we use poke-env and Pokémon Showdown.

**Q: Why should we believe any of your numbers?**
- The same team plays both sides.
- Every number has an interval.
- The decision rule was fixed before the runs.
- The negatives are reported, not dropped.
- The code fingerprint is stored with every results folder.
You can check any game: each has a raw log and a trace.

**Q: What's the single most important number?**
The win rate of today's bot against SimpleHeuristics in the same-team eval, with its Wilson interval (`mcts-headline`, in `progress.md` → 📊 Latest). Second: how it does against Foul Play at ladder strength.

**Q: What surprised you?**
- The usage-stats prior predicted reveals better than our updated belief.
- Some teams finish games far faster than others with the same bot (median 24 turns for `team_6.txt` against 40+ for most).
- Beating the easy bot told us nothing about strong ones: one-ply won about 72% against SimpleHeuristics and 5–8% against Foul Play.

**Q: If you had to cut one thing, what?**
The opt-in flags. Every one of them is an unproven experiment. The core (belief → sampled worlds → MCTS, with honest evaluation) is the project.

**Q: Why not reinforcement learning or an LLM?**
Neither fits a 25-hour hackathon and our question. RL needs far more compute and gives no explicit belief to show. An LLM can't play a simultaneous-move game within 3 s reliably, and it wouldn't give a measurable prediction. Search over a real simulator with an explicit belief is testable now.

---

## 12. Limits and next steps

**Q: What doesn't it do?**
- No ladder play: there's no registered bot account, so no Showdown Elo.
- Bot opponents only.
- One format.
- The win-probability model doesn't beat the baseline yet.
- The live view needs internet, because the Showdown client loads its graphics online.
(PRD §4)

**Q: With another week, what would you do?**
1. Team-conditioned priors (A6).
2. Train the win-probability model on the full Tiger turns and only use it if it beats the heuristic.
3. Longer head-to-heads, so small effects (threads, Tera gate) get tight intervals.
4. A registered bot account for real ladder games.

---

## 13. Quick facts

| Fact | Value |
|---|---|
| Decision | 8 worlds × 150 ms native MCTS (`poke-engine` 0.0.48), 1 thread, 3 s budget |
| Belief | usage-stats prior, hard filter on reveals, 3% floor on failed replays, `reliable` mode |
| Priors | 243 species + 78 forme aliases, ≤30 sets each (gen9ou-1825, 2026-09) |
| Data | 2.5M replays; 489,840 turns / 20,000 games (15k train, 5k test from 2026-05-19) |
| Prediction | logistic + Platt: 0.6600 log loss vs HP heuristic 0.6348 (worse); belief: prior 2.71 vs posterior 3.08 (worse) |
| Reliability | 7,863/7,863 worlds usable in the pilot; demo think p50 ~1.4 s **[10:00]** |
| Eval design | same team both sides, sides swapped, Wilson 95% + team bootstrap, manifest guard |

**Ideas, data and libraries (all code is ours):**
- **Ideas:** searching several sampled worlds (Foul Play, `pmariglia/foul-play`); more engine threads per world and a Tera gate, both tested as opt-in (Laplace, `influxtion/Laplace-Pokemon-Showdown-AI`).
- **Data:** Smogon usage stats; HolidayOugi replays; Foul Play's published set counts (opt-in priors only).
- **Libraries:** `poke-engine`, poke-env, Pokémon Showdown.
