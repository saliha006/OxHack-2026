# MCTS state adapter audit

Verified against the locally built `poke-engine==0.0.48` with the repository's
`terastallization` feature and no default generation features. The native binding
is immutable; conversion supplies constructor fields rather than mutating a
constructed `Side` or `Pokemon`.

## Verified conversion

`tests/test_mcts_adapter.py` exercises native root choices and saved protocol
fragments. Tests check the legal action set, not repeatable native visit counts.

- Root move strings are move IDs, with `-tera` for Tera, and switches are
  `switch <species-id>`. Replacement searches produce switches for the replacing
  side and `No Move` for the other side. Both a fainted active and a living pivot
  with `force_switch=True` were exercised. The MCTS backend can directly search
  replacement states; the one-ply backend retains its previous workaround.
- Our moves retain request order, disabled flags and remaining PP. Empty PP is
  excluded by both Python legality and native search. The raw request supplies
  our exact current Choice/Encore restriction; opponent disabled flags are
  derived from known last move, Choice item, Encore and Taunt. Native Encore is
  given `last_used_move=move:<zero-based-index>`.
- Our team follows request order and the opponent follows preview order. Delayed
  effect source indices are resolved by species against the constructed order.
  This assumes Species Clause, as in OU.
- `force_trapped` retains authoritative `trapped` and conservative `maybeTrapped`
  at the root. Native mechanics model trapping in later simulated turns.
- A fainted Pokémon retains identity, stats and its transformed flag. Native
  Tera availability scans **every** team slot, including fainted Pokémon. Losing
  this flag would erroneously permit a second Tera. Details-based Tera reveals
  also update the parser's side resource. An inconsistent opponent observation
  saying Tera is spent without identifying a transformed slot raises a structured
  world-conversion error instead of inventing a slot or resource.
- Known moves are inserted before guessed moves, known items/abilities/Tera
  override guesses, and consumed/removed items become `none`.
- Screens, hazards, weather, terrain and Trick Room retain their elapsed counts
  and are converted to remaining durations. Toxic counters remain slot aware.
- Optional `volatile_turns`, `wish`, `future_sight` and `substitute_hp` extensions
  preserve existing BattleState consumers. Wish survives switches, uses half the
  source's max HP unless an exact `hp` is supplied, and counts down from two.
  Future Sight is stored on the **attacking** side with the source slot and counts
  down from three. Replay tests run native delayed-effect countdowns and Wish
  healing. A failed attempt does not create a pending effect.
- Optional `sleep_turns` counts observed sleeping action attempts rather than
  upkeeps. Rest starts at native counter three and decrements on those attempts;
  a value of one means it wakes on its next attempt. Existing states without
  this extension retain the older elapsed-status approximation.

## Binding documentation mismatch

The installed `.pyi` describes volatile counters as remaining turns. Reading the
installed Rust source and executing native simulation showed different semantics:
Taunt, Encore and locked moves use elapsed counters zero through two; Yawn uses
zero through one. Slow Start uses a countdown. Passing Taunt=3 or Yawn=2 can panic
inside native instruction generation. The adapter maps and clamps observed
elapsed counts to the valid native ranges; tests execute these cases. Encore and
Taunt count actions in native code, while protocol `upkeep` is only an
approximation when a Pokémon loses an action.

## Explicit estimates and remaining limitations

`adapter_diagnostics(request, battle)` returns these approximations for decision
traces. They are not treated as observed facts.

- Opponent PP and our bench PP are not present in the current contract/request.
  The baseline assumes the native default of 16 PP for each reconstructed move.
  PP Ups, Pressure, previously used bench PP and revealed PP depletion are not
  inferred. Our active PP is authoritative.
- The opponent's max HP and hidden stats come from the sampled set. Percent HP is
  rounded; a Wish amount from an opponent source is consequently estimated too.
  Our fainted request slot no longer includes exact max HP, so it uses a safe
  positive placeholder; revival and a pending Wish from that source can be
  inaccurate unless its exact heal amount is supplied.
- A visible Substitute with unknown remaining HP is estimated at a quarter of
  sampled max HP. Supplying `substitute_hp` overrides that estimate. Damage to
  Substitute is not reconstructed from hidden public information.
- Durations use normal lengths; hidden Light Clay, weather rocks and Terrain
  Extender are not inferred. Some counters, including lost-action Encore/Taunt
  timing, may differ by a turn. Effects still visible beyond normal duration can
  be underestimated. Unsupported side conditions are explicitly reported.
- Stock engine Gen 9 does not expire confusion using its exported confusion
  counter. It fixes locked-move duration instead of branching over two/three
  turns. These are native model limitations, recorded when relevant.
- Protect success streak, exact confusion duration, Illusion ambiguities,
  transformed/copied moves, complex item/ability changes and every uncommon
  volatile effect have not been fully audited. Future Sight is supported;
  Doom Desire is not mapped to an equivalent psychic attack.
- A slow-pivot saved opposing move is not in BattleState. Replacement state uses
  native `No Move` for the other side; a known move still waiting to execute
  cannot currently be reconstructed.
- The existing native Struggle implementation is known to differ from Showdown
  (Normal type/recoil handling). The adapter preserves the move for legal action
  mapping; it does not patch native battle mechanics.

These limitations qualify integration/strength results. Further adapter coverage
and better observation metadata should be measured separately from search tuning.

The replay fixture `tests/fixtures/delayed_effects_showdown.log` and its turn-3 request were generated with the local Showdown simulator at commit `c0845f33d381402dfcb18ce324c20a94f18af075`. The fixture verifies that Future Sight starts on the source, resolves against the opposing target after two further turns, and that Wish survives switching and heals on the next turn. It is a mechanics fixture, not a strength-evaluation battle.
