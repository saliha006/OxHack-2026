from dataclasses import dataclass

from decision.state import DEX

STAT_ORDER = ("hp", "atk", "def", "spa", "spd", "spe")

# Nature -> (boosted stat, lowered stat). The five neutral natures aren't listed.
NATURES = {
    "lonely": ("atk", "def"), "brave": ("atk", "spe"), "adamant": ("atk", "spa"), "naughty": ("atk", "spd"),
    "bold": ("def", "atk"), "relaxed": ("def", "spe"), "impish": ("def", "spa"), "lax": ("def", "spd"),
    "timid": ("spe", "atk"), "hasty": ("spe", "def"), "jolly": ("spe", "spa"), "naive": ("spe", "spd"),
    "modest": ("spa", "atk"), "mild": ("spa", "def"), "quiet": ("spa", "spe"), "rash": ("spa", "spd"),
    "calm": ("spd", "atk"), "gentle": ("spd", "def"), "sassy": ("spd", "spe"), "careful": ("spd", "spa"),
}


@dataclass(frozen=True)
class PokemonSet:
    """One guess at a Pokémon's hidden details, in the form Smogon's usage data gives them."""
    moves: tuple[str, ...]
    item: str
    ability: str
    tera_type: str
    nature: str
    evs: tuple[int, int, int, int, int, int]  # STAT_ORDER
    ivs: tuple[int, int, int, int, int, int] = (31,) * 6


def stats(species: str, level: int, pokemon_set: PokemonSet) -> tuple[int, int, int, int, int, int]:
    """(max HP, atk, def, spa, spd, spe), using the game's stat formula."""
    base = DEX[species]["baseStats"]
    up, down = NATURES.get(pokemon_set.nature, (None, None))
    result = []
    for stat, iv, ev in zip(STAT_ORDER, pokemon_set.ivs, pokemon_set.evs):
        raw = (2 * base[stat] + iv + ev // 4) * level // 100
        if stat == "hp":
            result.append(raw + level + 10)
        else:
            # Integer maths throughout, as the games do: 1.1 as a float can round 405.9 differently.
            result.append((raw + 5) * (110 if stat == up else 90 if stat == down else 100) // 100)
    return tuple(result)
