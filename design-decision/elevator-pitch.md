# Elevator pitch

*Long version: about 3½ minutes to read. The 90-second spoken version is at the bottom. Draft 6, 2026-10-25 ~11:00 UTC, revised after two critiques and a cold read by someone given only this page.*

---

## Half the board is hidden

Turn four of a Pokémon battle. Our Dragonite is down to a fifth of its health. Facing it is a Great Tusk, and we can see its name and its health bar, but not its held item, not its exact moves, and not the type it can switch to once per game (a mechanic called Terastallizing, which changes what it's weak to). You never see the other side's full hand, so every good move starts as a guess.

We wanted that guess to come from data, and we wanted to be able to see it.

## What we built

A bot for Pokémon Showdown's main competitive format. It predicts what the opponent is hiding, decides under that uncertainty in under three seconds, and writes both into the battle chat as it plays. Four of us built it, in three layers.

To test it we use Foul Play, a strong open-source bot, on hard mode: roughly the search it uses on the public ladder, three to six times more than ours every turn. Our first version won 3 of 44 games against Foul Play's weaker settings, about 7%. This one has played hard mode four times and won two. Four games can't tell you which bot is stronger (the plausible range is roughly 15% to 85%), but they do tell you this is a different bot.

## Step 1: guess what's hidden (data layer)

It starts from real usage. Smogon publishes monthly statistics on what rated players bring into battle, and we turn them into up to 30 likely builds for each of 243 Pokémon, each with a probability.

Then the battle narrows it down. Anything revealed rules builds out, and small clues count too. Stealth Rock is a trap that chips anything switching in, so a Pokémon that comes in unhurt is almost certainly wearing Heavy-Duty Boots, the item that blocks it. After every turn the bot also replays what just happened against each remaining build. A build that can't explain the damage is down-weighted to 3% rather than deleted, so one unlucky damage roll can't rule out the truth.

How good are the guesses? In today's demo battles, between half and two-thirds of its guesses about hidden items were right, depending on the team.

We've also loaded 2.5 million public replays, split by date, to train the next prediction models on older games and test them on newer ones.

## Step 2: decide in three seconds (strategy layer)

From that belief the bot draws eight complete versions of the opponent's team, eight "what if" worlds. In each one it runs Monte Carlo tree search, playing out many possible futures and keeping score, on a fast game simulator for 150 milliseconds. Then it pools the eight searches and plays the move they visited most, the usual robust choice in tree search.

Back on turn four, 48% of all that search went to Ice Spinner, an Ice attack that Great Tusk takes double damage from. Switching out came second at 20%. It attacked. The 48% is a share of search effort, not a chance of winning, and we keep the two apart.

The search runs in its own process under a hard deadline. If it stalls, we kill it and play a safe move. In all eight demo battles today, that never once happened.

## Step 3: play it out loud (bot layer)

The bot layer talks to the Showdown server through our own parser, which keeps an exact record of every battle. The same parser turned those replays into training data, so training and live play see a battle the same way. Each decision goes into the chat beside the board.

## How we keep score

Every test game gives both bots the identical team, then they swap sides, so the luck of the team draw cancels out. Every win rate comes with a 95% confidence interval, and the bar for switching on any new feature was written down before a single game.

Changes have to beat the current bot head to head. Mixing in curated builds didn't: 25 wins, 35 losses, so it stays off. Giving the search four processor threads instead of one did, 11 wins in 14, which clears the bar but only just, so we want more games before switching it on.

## Why this isn't just Pokémon

Start with a prior built on history, narrow it as evidence arrives, then commit before the clock runs out. That's close to how a trader handles hidden information. Pokémon is a clean place to test the loop, with millions of public games and an exact simulator to check against. We're not claiming the bot knows anything about markets, only that the shape of the problem is the same.

## What we got wrong, and what's next

Two things don't work yet, and we'd rather say so. Our first win-probability model, trained on a small public sample of 96 games, does worse than simply counting who has more health left: log loss 0.660 against 0.635, where lower is better and a coin flip scores 0.693. It stays out of the bot. And on held-out games, the turn-by-turn narrowing doesn't yet predict the next reveal better than the usage statistics alone. It stays in, because it's what rules out impossible builds, but it hasn't yet shown it makes the guesses better on average.

The next thing we'd build is guessing each Pokémon's build from the five teammates beside it, since real teams are built around each other. That's where we expect the prediction side to start paying off.

---

## 90-second spoken version

Turn four. Our Dragonite is down to a fifth of its health, facing a Great Tusk we can only half see. What's it holding? What will it Terastallize into? You can't tell from the screen.

So the bot guesses, from data: what rated ladder players actually bring, narrowed by every move it watches. Take no Stealth Rock damage on the way in, and it pencils you in for Heavy-Duty Boots.

Then it has three seconds. It builds eight versions of the opponent's team from those guesses, simulates each one forward for 150 milliseconds, and plays the move that got the most search across all eight: here, Ice Spinner, with 48% of it. A separate process holds it to the clock. In eight demo battles it never once fell back to a default move.

We also built a replay pipeline, 2.5 million games split by date, for prediction models. The first one still loses to a plain HP count, so it isn't in the bot.

The opponent that matters is Foul Play on hard mode, which searches several times harder than we do every turn. Same team on both sides, pass mark written down before the first game. Our first bot won 3 of 44 against weaker settings of it. This one is two games all on hard mode. Four games don't prove much.

Three in forty-four did.

---

**Where each line comes from** (for Q&A):
- Turn 4, Dragonite at 21% vs Great Tusk, Ice Spinner 48%, switch to Moltres 20%: rehearsal battle `battle-gen9ou-594`. Great Tusk is Ground/Fighting, so Ice hits it for double damage.
- 243 species, up to 30 builds each; the Boots rule (or Magic Guard); 3% floor: PRD v4 §7.2, §9; question bank §6.
- 8 worlds × 150 ms, 3 s deadline enforced by a worker process; 0 fallbacks across 8 demo battles: PRD §7.1; README results.
- 2.5M replays, split by date (train from 2025-01-01, test from 2026-05-19): PRD §9. The win-probability numbers (0.6600 vs HP 0.6348) come from a smaller public study, not from those replays: PRD §7.3.
- Foul Play hard mode (`fphard`) = 4 parallel searches at 900–1100 ms per decision, about 3–6× our search, roughly its ladder settings: PRD §7.5. "Lucky to win one": at the old bot's 3/44 rate, the chance of 1+ wins in 4 games is about 25%, and of 2+ about 3%.
- Log loss of a coin flip = ln 2 ≈ 0.693. The win-probability study used 96 public games (PRD §7.3; CURRENT-STATUS).
- Item guesses right 48–65% of the time: demo traces 577–594, one battle per team, spot check (question bank §2). Narrowing vs usage alone: next-reveal log loss, prior 2.71 vs updated belief 3.08 (PRD §17).
- Curated builds (coherent priors) 25–35 in a 60-game screen; four engine threads 11–3 vs the demo bot (Nate's slice, reported, Wilson 52–92%): PRD §0; question bank §4.
- Most-visited move at the root is MCTS's standard "robust child" choice.
- One-ply vs SimpleHeuristics 72% (95 games, Wilson 62–80%); vs Foul Play's three weaker levels 3/44 (Wilson 2–18%); today's bot vs `fphard` 2–2 (Wilson 15–85%): README results table.
