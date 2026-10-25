# Elevator pitch

*Long version: about 3 minutes to read. The 90-second spoken version is at the bottom. Draft 5, 2026-10-25 ~10:55 UTC, revised after two independent critiques.*

---

## Half the board is hidden

Turn four of a Pokémon battle. Our Dragonite is down to a fifth of its health. Facing it is a Great Tusk, and we can see its name and its health bar, but not its held item, not its exact moves, and not the type it can switch into once per game (a mechanic called Terastallizing). You never see the other side's full hand, so every good move starts as a guess.

We wanted that guess to come from data, and we wanted to be able to see it.

## What we built

A bot for Pokémon Showdown's main competitive format that predicts what the opponent is hiding, decides under that uncertainty in under three seconds, and writes both into the battle chat as it plays. Four of us built it, in three layers.

Our first version lost 41 of 44 games to Foul Play, a strong open-source bot, and that was on Foul Play's easier settings. This version has played Foul Play on hard mode four times and won two. Four games can't rank it yet. The old bot would have been lucky to win one.

## Step 1: guess what's hidden (data layer)

The starting point is real usage. Smogon publishes monthly statistics on what rated players bring into battle, and we turn them into up to 30 likely builds for each of 243 Pokémon, each with a weight.

Then the battle narrows it down. Anything revealed rules builds out, and small clues count too. Stealth Rock is a trap that chips anything switching in, so a Pokémon that switches in unhurt is almost certainly wearing Heavy-Duty Boots, an item that blocks it. After every turn the bot also replays what just happened against each remaining build. A build that can't explain the damage keeps 3% of its weight instead of being thrown out, in case the dice rolled strangely.

Alongside that, we loaded 2.5 million public replays into a shared database, split by date, so prediction models learn from older games and are tested on newer ones.

## Step 2: decide in three seconds (strategy layer)

From that belief the bot draws eight complete versions of the opponent's team, eight "what if" worlds. In each one it runs Monte Carlo tree search (playing out many possible futures and keeping score) on a fast game simulator for 150 milliseconds, then plays the move it spent the most search on across all eight.

Back on turn four, 48% of that search went to Ice Spinner, an Ice attack that Great Tusk takes double damage from. Switching out came second at 20%. It attacked. The 48% is a share of search effort, not a chance of winning, and we keep those two apart.

The search runs in its own process under a hard deadline. If it stalls, we kill it and play a safe move. In eight demo battles that never once happened.

## Step 3: play it out loud (bot layer)

The bot layer talks to the Showdown server and runs every message through our own parser, which keeps an exact record of the battle. The same parser built the training data from those replays, so training and live play see a battle the same way. Each decision goes into the chat beside the board, so you can read the reasoning while it plays.

## The test: Foul Play on hard mode

Hard mode means roughly the settings Foul Play plays the public ladder with: about 3 to 6 times our search per turn. Both sides always play the same team, so we're measuring play rather than team-building. Every win rate gets a 95% confidence interval, and the bar for switching on any new feature was written down before a single game.

That's why the numbers up top come with ranges. The old bot's 3 in 44 means 18% at the very best; the new one's 2 in 4 could be anywhere from about 15% to 85%. Narrowing that range is the next run.

## Why this isn't just Pokémon

Start from a prior built on history, narrow it as evidence arrives, then commit to a decision before the clock runs out. That's close to how a trader deals with hidden information. Pokémon is a clean place to test the loop, with millions of public games and an exact simulator. We're not claiming the bot knows anything about markets, only that the shape of the problem is the same.

## What we got wrong, and what's next

Our first win-probability model, trained on a small public sample, does worse than simply counting who has more health left: log loss 0.660 against 0.635, where lower is better and a coin flip scores 0.693. It stays out of the bot until it earns a place. And for now each opposing Pokémon is guessed on its own, when real teams are built around each other. Guessing a build from the five teammates beside it is the next thing we'd build, and the one we expect to matter most.

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
- Log loss of a coin flip = ln 2 ≈ 0.693.
- One-ply vs SimpleHeuristics 72% (95 games, Wilson 62–80%); vs Foul Play's three weaker levels 3/44 (Wilson 2–18%); today's bot vs `fphard` 2–2 (Wilson 15–85%): README results table.
