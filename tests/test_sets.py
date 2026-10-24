from decision.sets import PokemonSet, stats


def gholdengo(**kw):
    fields = dict(moves=("makeitrain", "shadowball", "nastyplot", "recover"), item="choicescarf",
                  ability="goodasgold", tera_type="steel", nature="timid", evs=(0, 0, 0, 252, 4, 252))
    return PokemonSet(**{**fields, **kw})


def test_timid_gholdengo_stats():
    # Known values: max-speed Timid Gholdengo hits 293 Speed and 365 SpA at level 100.
    assert stats("gholdengo", 100, gholdengo()) == (315, 140, 226, 365, 219, 293)


def test_adamant_kingambit_stats():
    kingambit = PokemonSet(moves=("ironhead",), item="leftovers", ability="supremeoverlord", tera_type="dark",
                           nature="adamant", evs=(252, 252, 0, 0, 4, 0))
    assert stats("kingambit", 100, kingambit) == (404, 405, 276, 140, 207, 136)


def test_neutral_nature_and_level():
    hp, atk, *_ = stats("gholdengo", 50, gholdengo(nature="serious", evs=(0,) * 6))
    assert (hp, atk) == (162, 80)


def test_ivs_count():
    *_, spe = stats("gholdengo", 100, gholdengo(ivs=(31, 31, 31, 31, 31, 0)))
    assert spe == 259
