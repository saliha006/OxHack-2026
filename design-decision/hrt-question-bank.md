# HRT question bank: what we built, and why

*For the judging table (HRT: Best Use of Data for Predictions & Decision Making). Each answer is what to say in about 20 seconds, then where the detail lives. Written 2026-10-25 ~10:00 UTC from `main` @ `abf0e19`; the full spec is the PRD (v4). Numbers marked **[10:00]** are a snapshot: the merged eval table goes in `progress.md` → 📊 Latest and the README.*

---

## 1. The 30-second pitch

"Our agent plays Pokémon Showdown, a game with hidden information: you can't see the opponent's items, abilities or Tera types. Every turn it **predicts** what's hidden, using usage statistics from real players and what it has seen so far. It then **decides** by searching 8 different versions of the game that fit its prediction and picking the move that does best across all of them. We show both halves live in the battle chat, and we measured both: the decisions head to head against other bots with confidence intervals, the predictions against simple baselines on held-out games."

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
- **Joint priors** (Saliha): complete sets actually observed from Foul Play, blended 75/25 with usage. Being tested today (`mcts8joint`).
(PRD §9; `coherent-sets.md`)

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
A single guess is overconfident: if the opponent has a Choice Scarf and we assumed Leftovers, the plan fails. Searching across 8 plausible worlds picks moves that are robust to what we don't know. This is the approach that made Foul Play strong; we adapted it. (PRD §7.1, Appendix B)

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
- **vs Foul Play `fphard`** (this laptop): today's bot 2–2; joint priors 4–7. The research estimate before testing was 25–40%.
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

## 6. Data

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

## 7. Limits and next steps

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

## 8. Quick facts

| Fact | Value |
|---|---|
| Decision | 8 worlds × 150 ms native MCTS (`poke-engine` 0.0.48), 1 thread, 3 s budget |
| Belief | usage-stats prior, hard filter on reveals, 3% floor on failed replays, `reliable` mode |
| Priors | 243 species + 78 forme aliases, ≤30 sets each (gen9ou-1825, 2026-09) |
| Data | 2.5M replays; 489,840 turns / 20,000 games (15k train, 5k test from 2026-05-19) |
| Prediction | logistic + Platt: 0.6600 log loss vs HP heuristic 0.6348 (worse); belief: prior 2.71 vs posterior 3.08 (worse) |
| Reliability | 7,863/7,863 worlds usable in the pilot; demo think p50 ~1.4 s **[10:00]** |
| Eval design | same team both sides, sides swapped, Wilson 95% + team bootstrap, manifest guard |

**Credits:** ideas adapted from **Foul Play** (`pmariglia/foul-play`: one MCTS per sampled world, observed complete sets) and **Laplace** (more engine threads per world, the Tera gate). Built on `poke-engine`, poke-env and Pokémon Showdown.
