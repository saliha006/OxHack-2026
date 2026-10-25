# Reserved OU evaluation teams

Four public, author-sourced teams were locked at **2026-10-25 03:44:29 UTC**, before running evaluation games on these files. They span offense, bulky offense, balance and stall. The choices were made by archetype, without trying either backend on the teams or changing their sets.

The source is the first post of the [staff-hosted Smogon SV OU sample-team thread](https://www.smogon.com/forums/threads/sv-ou-sample-teams-new-samples-added-post-spl-and-tera-blast-ban.3712513/), retrieved on 25 October 2026. The post displayed an update of 13 July 2026 and a last moderator edit of 16 August 2026. The exact import text was retrieved from each linked author's public PokéPaste JSON endpoint using HTTP. No moves, items, spreads, Tera types, nicknames, team order or other set details were edited.

| File under `bot/teams/held-out/` | Sample and credited builder | Public import |
|---|---|---|
| `01-vert-dragonite-deoxys-ho.txt` | Dragonite + Deoxys-S offense — Vert | [PokéPaste](https://pokepast.es/57780b9afe26d51b) |
| `02-ewin-kyurem-cinderace-bo.txt` | Kyurem + Cinderace bulky offense — Ewin | [PokéPaste](https://pokepast.es/02b19c79ad13bbdd) |
| `03-ctc-darkrai-ogerpon-balance.txt` | Darkrai + Ogerpon balance — CTC | [PokéPaste](https://pokepast.es/b1c94db7a26e6e90) |
| `04-jb291-talonflame-mandibuzz-stall.txt` | Talonflame + Mandibuzz stall — jb291 | [PokéPaste](https://pokepast.es/056ce7c40fa545c6) |

The forum credits the balance team to CTC; that paste's own author field reads `noonemorebased`. Both attributions are preserved in [the provenance manifest](mcts-heldout-provenance.json), rather than assuming the uploader and builder are the same person. Titles, author fields and ladder peaks in the original sources are provenance information, not results measured by this project.

Every team imported as six Pokémon and passed the local Showdown `TeamValidator.get("gen9ou").validateTeam()` with `null` problems. The validator checkout was `c0845f33d381402dfcb18ce324c20a94f18af075`. Exact file hashes and canonical set hashes are recorded in the manifest. None matched any of the ten `bot/teams/standin/` files by either hash. Canonical comparison ignores nicknames, team order and move order while retaining actual set details.

Reproduce integrity, disjointness and legality checks after building the local Showdown checkout:

```sh
node docs/validate-mcts-heldout.cjs
```

The script reports the current validator commit alongside the original one; legality can change with later format updates. It never edits a team.

These files are **held out from this branch's earlier integration and tuning games**. They are public samples and may have contributed battles or sets to the aggregate September 2026 Smogon priors. No claim of disjointness from those underlying public battles is possible from aggregate priors. They are also a small, purposefully varied sample rather than a random draw from all OU teams.

Keep these file bytes and the evaluation settings locked when using this pool for comparisons. Record any fixes prompted by its games; after such fixes, this pool becomes regression/evaluation history, and a fresh untouched pool is needed for a confirmatory strength claim. Do not change a set to improve either backend's result. Use the real priors file, rather than reconstructing priors from these reserved teams.
