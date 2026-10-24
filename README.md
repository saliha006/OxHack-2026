# OxHack-2026

Hackathon project for **OxHack 26** (Oxford Mathematical Institute, 24–25 Oct 2026). *Last updated 2026-10-24.*

## Tracks we are targeting

| Priority | Prize | Why |
|---|---|---|
| **1 (main)** | **HRT: Best use of Data for Predictions & Decision Making** | A calibrated forecast, a decision rule built on it, and a backtest that shows the decision beating a simple baseline |
| **2** | **Best Handmade Project** (thanks to Citadel; judged by Tom 7) | A hand-built physical piece next to the software |
| Optional | General prizes (First Place, Runner Up) | Use the theme **TIME** (turns, tempo, rewind) |
| Optional | MLH: Gemini API, ElevenLabs, Tiger Data | Only if there is time left over |

The TIME theme applies to the general prizes and Best Handmade. The HRT prize is judged on its own brief.

## The idea (direction, not yet locked)

**Momentum**: paste a Pokémon Showdown replay and get a calibrated win probability for every turn, the turn that decided the game, and a coach-style walkthrough of the weaker and stronger decisions the player could have made.

Directions we are also exploring:

- **Elo from decisions.** Estimate a player's rating from how they play, to compare against top-500 ladder players. This needs a reliable dataset with ratings across *all* levels, not only high Elo.
- **Honest Clock**: live Oxford bus arrival probabilities, as the fallback idea.

Decisions in force and open choices are in the project's shared docs (kept off `main`); the build history is in [`progress.md`](progress.md).

## Team

- Saliha Shoaib ([`saliha006`](https://github.com/saliha006))
- Nate Banas ([`aldrichbanas07`](https://github.com/aldrichbanas07))
- Derrick Lim Yong Hao ([`RandomGeeb`](https://github.com/RandomGeeb))

## Repo layout

- `main`: this README, [`progress.md`](progress.md), `contracts/` and the code.
- `sali`: Saliha's working branch.
- `context`: the team's shared planning docs (no code).

Secrets stay in a local `.env`; it is never committed.
