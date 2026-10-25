# Elevator pitch

*About 85 seconds spoken (~220 words). Draft 3, 2026-10-25 ~10:45 UTC, revised after an independent critique.*

---

Turn four. Our Dragonite is down to a fifth of its health, facing a Great Tusk we can only half see. What's it holding? What will it Terastallize into? You can't tell from the screen.

So the bot guesses, from data: what rated ladder players actually bring, narrowed by every move it watches. Take no Stealth Rock damage on the way in, and it pencils you in for Heavy-Duty Boots.

Then it has three seconds. It builds eight versions of the opponent's team from those guesses, simulates each one forward for 150 milliseconds, and plays the move that got the most search across all eight: here, Ice Spinner, with 48% of it. A separate process holds it to the clock. In eight demo battles it never once fell back to a default move.

We also built a replay pipeline, 2.5 million games split by date, for prediction models. The first one still loses to a plain HP count, so it isn't in the bot.

The opponent that matters is Foul Play at full strength, which searches several times harder than we do every turn. Same team on both sides, pass mark written down before the first game. Our first bot won 3 of 44 against weaker settings of it. This one is two games all at full strength. Four games don't prove much.

Three in forty-four did.

---

**Where each line comes from** (for Q&A):
- Turn 4, Dragonite at 21% vs Great Tusk, Ice Spinner with 48% of the search: rehearsal battle `battle-gen9ou-594`.
- The Boots rule (or Magic Guard), 8 worlds × 150 ms, a 3 s deadline enforced by a worker process: PRD v4 §7.1–7.2; question bank §6.
- 0 fallbacks across 8 demo battles; chat shows the pick and guesses: README results; `progress.md` 📊 Latest.
- 2.5M replays, split by date (train from 2025-01-01, test from 2026-05-19): PRD §9. The first win-probability model (0.6600 vs HP 0.6348 log loss) came from a smaller public study: PRD §7.3.
- Foul Play `fphard` = 4 parallel searches at 900–1100 ms per decision, about 3–6× our search per turn: PRD §7.5; question bank §11.
- Same team both sides, rule fixed in advance: PRD §0, §7.5.
- One-ply: 3 of 44 against Foul Play's three weaker levels (fplow, fpmid, fphigh). Today's bot: 2–2 against `fphard`, Wilson 15–85%. README results table.
