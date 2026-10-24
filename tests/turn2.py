import json
from pathlib import Path

from decision.sets import PokemonSet

ROOT = Path(__file__).parent.parent
REQUEST = json.loads((ROOT / "tests" / "fixtures" / "move_request.json").read_text())
EXAMPLE = json.loads((ROOT / "contracts" / "examples" / "battle_state_turn2.json").read_text())


def guess(*moves, item="leftovers", ability="pressure", tera="normal"):
    return PokemonSet(moves=moves, item=item, ability=ability, tera_type=tera, nature="serious", evs=(84,) * 6)


# One guess per opponent slot, in team-preview order (dragonite, samurotthisui, gholdengo, pecharunt, walkingwake, tinglu).
SETS = [
    guess("extremespeed", "earthquake", "dragondance", "roost", item="heavydutyboots", ability="multiscale"),
    guess("ceaselessedge", "razorshell", "suckerpunch", "knockoff", item="focussash", ability="sharpness"),
    guess("shadowball", "nastyplot", "makeitrain", "recover", item="choicescarf", ability="goodasgold", tera="fairy"),
    guess("malignantchain", "partingshot", "recover", "shadowball", item="heavydutyboots", ability="poisonpuppeteer"),
    guess("hydrosteam", "dracometeor", "flamethrower", "flipturn", item="boosterenergy", ability="protosynthesis"),
    guess("ruination", "spikes", "whirlwind", "earthquake", item="leftovers", ability="vesselofruin"),
]
