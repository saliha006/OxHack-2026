"""Optional seeded sampling between a mature pair of supported legal moves.

This helper changes selection only. It does not change pooled support, native
search, sampled world mass or Tera selection, and makes no equilibrium claim.
The caller supplies the authoritative legal deterministic choice and a separate
persistent Random instance. The default Agent policy keeps this helper off.
"""
import math
from random import Random

from decision.actions import Action, our_actions
from decision.search_policy import map_choice

CONFIG = {"eligible_count": 2, "min_usable_worlds": 4, "min_root_visits": 1000,
          "min_support": .25, "max_absolute_gap": .03, "min_relative_support": .9,
          "min_combined_mass": .65, "min_world_share": .05,
          "min_world_support_fraction": .5, "min_supporting_worlds": 2}
EPSILON = 1e-12  # Inclusive decimal thresholds should not fail from floating roundoff.


def _positive(value):
    return (not isinstance(value, bool) and isinstance(value, (int, float)) and
            math.isfinite(value) and value > 0)


def mix_near_ties(original: Action, pooled: dict, request: dict, worlds: list[dict],
                  rng: Random, seed: int, *, excluded=()) -> tuple[Action, dict]:
    """Use one draw only when exactly two supported non-Tera moves pass all gates.

    Per-world maturity counts each successful sampled occurrence once, after
    normalising its native OUR root visits. A large tree never counts as extra
    worlds. An invalid/missing evidence path preserves the caller's choice.
    """
    diagnostic = {"policy": "seeded_supported_pair_v1", "config": dict(CONFIG), "seed": seed,
                  "original_choice": original.to_choice(), "final_choice": original.to_choice(),
                  "sampled": False, "selection_changed": False, "reason": None,
                  "eligible_choices": [], "probabilities": {}, "draw": None,
                  "candidate_choices": [], "support_maturity": [], "usable_worlds": 0,
                  "total_root_visits": 0, "required_supporting_worlds": 0, "ignored_worlds": [],
                  "interpretation": "heuristic mixed policy; support is not calibrated win probability; native MCTS remains unseeded"}

    def decline(reason):
        diagnostic["reason"] = reason
        return original, diagnostic

    if original.kind != "move":
        return decline("original_is_not_move")
    if original.tera:
        return decline("original_is_tera")
    try:
        legal = our_actions(request)
    except (KeyError, TypeError, ValueError):
        return decline("invalid_request")
    if original not in legal:
        return decline("original_not_legal")
    excluded = set(excluded)
    if original in excluded:
        return decline("original_excluded")
    if pooled.get("fallback_reason") or "action" in pooled and pooled["action"] is None:
        return decline("deterministic_fallback")
    if pooled.get("mapping_failures"):
        return decline("pooled_mapping_failures")
    if pooled.get("aggregation", "sampled") != "sampled":
        return decline("unsupported_pooling_mode")

    allowed = set(legal)
    distributions = []
    visits = 0
    derived_mapping_failures = []
    for index, world in enumerate(worlds):
        tag = world.get("index", index)
        if world.get("error") is not None:
            diagnostic["ignored_worlds"].append({"index": tag, "reason": "failed_world"})
            continue
        counts, total = {}, 0
        for row in world.get("our_visits", []):
            count = row.get("visits", 0)
            if not _positive(count):
                continue
            total += count
            choice = row.get("choice", row.get("move_choice", ""))
            action = map_choice(choice, request)
            if action is None or action not in allowed:
                derived_mapping_failures.append({"index": tag, "choice": choice})
            else:
                counts[action] = counts.get(action, 0) + count
        if total <= 0 or not counts:
            diagnostic["ignored_worlds"].append({"index": tag, "reason": "no_supported_root_visits"})
            continue
        distributions.append({action: count / total for action, count in counts.items()})
        visits += total
    usable = len(distributions)
    diagnostic["usable_worlds"] = usable
    diagnostic["total_root_visits"] = visits
    required = max(CONFIG["min_supporting_worlds"], math.ceil(usable * CONFIG["min_world_support_fraction"]))
    diagnostic["required_supporting_worlds"] = required
    if derived_mapping_failures:
        diagnostic["derived_mapping_failures"] = derived_mapping_failures
        return decline("native_mapping_failures")
    if pooled.get("usable_worlds", usable) != usable:
        return decline("usable_world_count_mismatch")
    if usable < CONFIG["min_usable_worlds"]:
        return decline("insufficient_usable_worlds")
    if visits < CONFIG["min_root_visits"]:
        return decline("insufficient_root_visits")

    raw_support = pooled.get("search_support", {})
    if not isinstance(raw_support, dict) or any(
            isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1
            for value in raw_support.values()):
        return decline("invalid_pooled_support")
    if any(value > 0 and choice not in {action.to_choice() for action in legal} for choice, value in raw_support.items()):
        return decline("unsupported_pooled_choice")
    if not math.isclose(sum(raw_support.values()), 1.0, rel_tol=1e-6, abs_tol=1e-6):
        return decline("unnormalised_pooled_support")
    original_support = raw_support.get(original.to_choice(), 0)
    if original_support + EPSILON < CONFIG["min_support"]:
        return decline("original_support_below_floor")
    candidates = []
    for action in legal:  # Request order fixes the sampling intervals and tie behavior.
        if action.kind != "move" or action.tera or action in excluded:
            continue
        support = raw_support.get(action.to_choice(), 0)
        if (support + EPSILON >= CONFIG["min_support"] and
                abs(original_support - support) <= CONFIG["max_absolute_gap"] + EPSILON and
                support + EPSILON >= CONFIG["min_relative_support"] * original_support):
            count = sum(distribution.get(action, 0) + EPSILON >= CONFIG["min_world_share"]
                        for distribution in distributions)
            candidates.append((action, support, count))
            diagnostic["support_maturity"].append({"choice": action.to_choice(), "pooled_support": support,
                                                   "supporting_worlds": count, "required_worlds": required})
    diagnostic["candidate_choices"] = [action.to_choice() for action, _, _ in candidates]
    if len(candidates) > CONFIG["eligible_count"]:
        return decline("diffuse_root")
    if len(candidates) != CONFIG["eligible_count"] or original not in {action for action, _, _ in candidates}:
        return decline("not_exactly_two_supported_moves")
    mass = sum(support for _, support, _ in candidates)
    diagnostic["combined_mass"] = mass
    if mass + EPSILON < CONFIG["min_combined_mass"]:
        return decline("insufficient_combined_mass")
    if any(count < required for _, _, count in candidates):
        return decline("insufficient_world_support")

    probabilities = [(action, support / mass) for action, support, _ in candidates]
    draw = rng.random()
    cumulative = 0.0
    final = probabilities[-1][0]
    for action, probability in probabilities:
        cumulative += probability
        if draw < cumulative:
            final = action
            break
    diagnostic.update(eligible_choices=[action.to_choice() for action, _ in probabilities],
                      probabilities={action.to_choice(): probability for action, probability in probabilities},
                      draw=draw, sampled=True, selection_changed=final != original,
                      final_choice=final.to_choice(), reason="sampled_supported_pair")
    return final, diagnostic
