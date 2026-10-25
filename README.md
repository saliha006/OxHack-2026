# OxHack-2026: a Pokémon battle agent that shows its working

Pokémon Showdown is a game of hidden information. You can see the opponent's six Pokémon, but not their items, abilities, exact moves or the type each one will Terastallize into. Good players guess those things from experience and from what they've seen so far, then choose moves that still work if the guess is a bit off.

This project does the same thing with data. Before a battle it starts from usage statistics of real players. During the battle it narrows those guesses with every move it sees, then searches eight different versions of the game that fit what it believes and plays the move that does best across them. Every decision is posted to the battle chat, so you can watch what it expects the opponent to have, what it's weighing up and why it chose what it did.

We built it in 25 hours at OxHack 26 (Oxford Mathematical Institute, 24–25 October 2026) for the HRT prize, **Best Use of Data for Predictions & Decision Making**.

```
Turn 4 · Ice Spinner (1351 ms) | dragonite 21% (6 left) vs greattusk 100% (5 left)
| Weighing: Ice Spinner 48% · switch to Moltres 20% · Earthquake 12% (8/8 worlds)
| Expects them: icespinner 25% · rapidspin 17% · headlongrush 13%
| Guessing their greattusk: rockyhelmet (4/8 worlds) · Tera ste…
```
*One real chat line from a rehearsal battle. Showdown cuts chat messages at 300 characters; the terminal shows the full version.*

## How it works

A battle runs through three parts that were built by different people and meet at small, written contracts.

The **data layer** runs before any battle. It turns Smogon's monthly usage statistics into a list of likely builds ("sets") for every Pokémon in the format: 243 species, up to 30 weighted sets each. It also loads 2.5 million public replays into a shared Postgres database and cuts them into 489,840 turn-by-turn positions for training and testing prediction models.

The **bot layer** connects to a Pokémon Showdown server. Every message the server sends goes through our own parser, which keeps a precise picture of the battle: HP, status, stat boosts, hazards, every move and item revealed so far. When the server asks for a move, the bot passes that picture and the list of legal options to the strategy layer, sends back the answer, logs everything and posts the reasoning to the chat.

The **strategy layer** decides. It keeps a belief about each opposing Pokémon's hidden set, starting from the data layer's usage statistics and updating it every turn:

- Anything revealed rules sets out.
- Small clues narrow it further. For example, a Pokémon that switched into Stealth Rock without taking damage is holding Heavy-Duty Boots, or has Magic Guard.
- The last turn is replayed in a simulator for each candidate set. A set that can't explain the damage or move order we saw keeps only 3% of its weight.

From that belief it draws eight complete guesses of the opponent's team ("worlds"), runs 150 ms of Monte Carlo tree search in each using the `poke-engine` simulator, and averages how much each option was favoured across the worlds. The search runs in a separate process with a hard three-second deadline, so a slow turn can never time out a game.

```
 usage stats ──► candidate sets ──────────────────────┐
 2.5M replays ──► DuckDB ──► Parquet ──► Postgres      │ prior
                                   └─► prediction study │
                                                       ▼
 Showdown ──► parser ──► BattleState + request ──► belief ──► 8 worlds ──► MCTS × 8 ──► pooled choice
    ▲                                                                                       │
    └────────────── /choose ◄───────────────────────────────────────────────────────────────┤
                     battle chat · terminal · trace file ◄───────────────────────────────────┘
```

## Using data to predict and to decide

The HRT brief is about using data to predict and to decide. We tried to do both and to measure both separately.

**Predicting.** The bot predicts what it can't see, and the prior for every prediction comes from data: Smogon's usage statistics from rated ladder games. We scored those predictions on held-out games. Before each reveal, how much probability had the belief put on what turned out to be true? We also built a calibrated win-probability model (logistic regression with Platt scaling) on public board features, and tested it on games played after its training data.

**Deciding.** Every decision is taken against the belief rather than against one guess. Sampling worlds in proportion to the belief and averaging over them is a Monte Carlo approximation of picking the move with the best expected outcome, given what we know and what we don't.

**Measuring.** Win rates come from head-to-head games where both sides play the same team and swap sides between games, so we measure play, not team strength. Every number gets a Wilson 95% interval. Before running anything we fixed a rule: a change ships only if it beats the current bot with the interval's lower bound above 50%.

**Reporting the misses.** The win-probability model is currently *worse* than a simple "who has more HP left" heuristic (log loss 0.660 vs 0.635 on held-out games). The in-battle belief updates haven't yet beaten the usage-stats prior at predicting the next reveal. We report both, keep the model out of the bot until it earns a place, and treat the gap as the next thing to fix.

## Time

Time runs through the whole design:
- **Every decision has a deadline.** Three seconds per move. The search spends its time across eight worlds and stops starting new ones when the clock gets close.
- **The belief is built over time.** Each turn adds evidence, so the guesses at turn 20 rest on far more than the guesses at turn 1.
- **The data is split by time.** Models train on games from 2025 onwards and are tested only on games from 19 May 2026 onwards, so a prediction never benefits from the future.
- **The prior has a date on it.** Usage statistics change month to month as the metagame moves; ours are from September 2026.

## Results so far

| Matchup | Games | Win rate | Wilson 95% |
|---|---|---|---|
| Demo bot vs SimpleHeuristics (live demo battles) | 8 | 8–0 | 68–100% |
| Demo bot vs Foul Play at ladder strength (`fphard`) | 4 | 2–2 | 15–85% |
| Observed-set priors vs Foul Play `fphard` | 11 | 4–7 | 15–65% |
| 4 engine threads vs the demo bot, head to head (reported by one laptop) | 14 | 11–3 | 52–92% |
| Earlier one-ply bot vs SimpleHeuristics (eval) | 95 | 72% | 62–80% |
| Earlier one-ply bot vs Foul Play (three strength levels) | 44 | 3–41 | 2–18% |

What these numbers do and don't say:
- The demo battles are informal; the same-team eval against SimpleHeuristics (`mcts-headline`) is the real headline, and we're merging it from four laptops.
- Against Foul Play the samples are too small to call either way. Our estimate before testing was 25–40%.
- The 4-thread result clears our bar, but only just, so we'd confirm it before switching it on.
- The one-ply rows explain why we moved to tree search: it beat the easy bot and lost almost everything to the strong one.

Bot reliability: in the MCTS pilot, all 7,863 searched worlds returned in time and no decision took over three seconds. Across all eight demo battles today the median decision took about 1.4 s, and not one move fell back to the safe default.

## Running it

You need Python with [`uv`](https://docs.astral.sh/uv/), a Rust toolchain (`poke-engine` builds from source) and Node 22.18 or newer for the Showdown server.

```sh
uv sync

# Local Showdown server, in a separate terminal
git clone https://github.com/smogon/pokemon-showdown.git
cd pokemon-showdown && npm install && node pokemon-showdown start --no-security

# One live battle against SimpleHeuristics; open the printed link,
# or type /join battle-gen9ou-N in the Showdown lobby
uv run python -m bot.demo live --teams bot/teams/standin/team_6.txt

# Play it yourself: the bot waits for a challenge. In the Showdown client, import a
# gen9ou team (bot/teams/standin/team_6.txt for a mirror match), then type
#   /challenge oxhack demo, gen9ou
uv run python -m bot.demo live --opponent human --teams bot/teams/standin/team_6.txt

# Replay a saved battle's reasoning without a server
uv run python -m bot.demo replay runs/<battle>.jsonl

# Evaluation: each laptop plays its share, then one machine merges the files
uv run python -m bot.eval run --pairings mcts-headline --games 60 --seed 1 --machine laptop1 --shards 2
uv run python -m bot.eval report

# Tests
uv run pytest --cov=decision
```

A few practical notes:
- On Windows, set `PYTHONUTF8=1` first (in PowerShell: `$env:PYTHONUTF8=1`). The bot tests are best run one file at a time there.
- The Showdown web client loads its graphics from the internet, so watching a battle needs a connection.
- Out of the box, Showdown only lets registered users chat. We run a small local change so the bot's guest account can post its reasoning to the battle chat; without it the terminal still shows everything.

## What's in the repo

| Path | What it is |
|---|---|
| `bot/` | Showdown connection, protocol parser, demo, eval harness, smoke test |
| `decision/` | The strategy layer: belief, world sampling, MCTS worker, pooling, fallbacks |
| `data/` | Prior builders, the replay pipeline (DuckDB, Parquet, Postgres), the set files themselves |
| `prediction/` | Win-probability model and belief scoring, run offline |
| `evaluation/`, `analysis/` | Offline studies of the search and its losses |
| `contracts/` | The interfaces between layers: `BattleState`, set candidates, the turns table |
| `progress.md` | The team's build log |

## Design choices worth arguing about

- **Tree search instead of one-turn lookahead.** Our first version simulated one turn ahead and scored the result. It beat the easy baseline 72% of the time and lost about 93% of games to Foul Play. Searching several turns ahead was the fix.
- **Eight worlds of 150 ms rather than one long search.** One long search commits to a single guess about the opponent's team. Spreading the time across eight sampled teams makes decisions that hold up when the guess is wrong. We built a 4 × 300 ms variant to test the trade-off.
- **Equal weight per world.** Worlds are already drawn in proportion to the belief, so likely builds appear more often. Weighting them again would double-count.
- **A soft floor instead of hard elimination.** Damage rolls and unusual builds make the replay check noisy. A set that fails keeps 3% of its weight and can come back when later turns fit it.
- **Search in its own process.** The only way to make a deadline real is to be able to kill the thing that's running late. The worker also keeps the belief between turns.
- **Prediction kept out of the decision loop.** A model that loses to its baseline shouldn't steer the bot. It stays offline until it wins on held-out games.
- **Same-team evaluation with a rule fixed in advance.** Otherwise a good team, or a lucky streak, looks like a better bot.

## Limits

- **No public ladder games.** That needs a registered bot account, so there's no Showdown rating to quote.
- **Bot opponents only.** Our opponents are SimpleHeuristics and Foul Play, which don't adapt the way people do.
- **One format:** Gen 9 OU.
- **Guesses are independent.** Each opposing Pokémon is guessed on its own. Real teams are built around each other, and predicting sets from the rest of the team is the next piece of work.
- **The demo pins one team.** `team_6.txt` had the best record, the shortest games and the most accurate guesses in our runs. The win rates above are across all teams.

## Where ideas and data come from

All code in this repository is ours.
- **Ideas:**
  - Searching several sampled versions of the opponent's team comes from [Foul Play](https://github.com/pmariglia/foul-play).
  - Two levers we test as options, more engine threads per world and a rule for when to Terastallize, come from [Laplace](https://github.com/influxtion/Laplace-Pokemon-Showdown-AI).
- **Data:**
  - Smogon usage statistics.
  - Public Showdown replays from the HolidayOugi dataset.
  - For an optional prior, Foul Play's published counts of complete sets seen on the ladder.
- **Libraries:** [`poke-engine`](https://github.com/pmariglia/poke-engine), [`poke-env`](https://github.com/hsahovic/poke-env), [Pokémon Showdown](https://github.com/smogon/pokemon-showdown).

## Team

- **Saliha Shoaib** ([`saliha006`](https://github.com/saliha006)): bot layer, evaluation, demo.
- **Kenar Narayaka** ([`kxnar`](https://github.com/kxnar)): tree search, belief, prediction studies.
- **Derrick Lim Yong Hao** ([`RandomGeeb`](https://github.com/RandomGeeb)): first decision layer, belief floor, team-preview lead.
- **Nate Banas** ([`aldrichbanas07`](https://github.com/aldrichbanas07)): usage priors, replay pipeline, the shared database.
