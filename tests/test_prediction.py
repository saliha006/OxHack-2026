import copy
import json
import math
from types import SimpleNamespace

import pytest

from prediction.__main__ import main, train
from prediction.data import read_turns, split_turns
from prediction.evaluation import binary_metrics
from prediction.features import FEATURE_NAMES, featurize, hp_baseline
from prediction.likelihood import reveal_distribution, score_opponent_traces, score_reveals
from prediction.model import WinModel, calibrate, fit_model
from prediction.replays import replay_rows
from tests.turn2 import EXAMPLE


def synthetic_rows():
    rows = []
    for i in range(18):
        date = "2025-01-01" if i < 10 else "2025-02-01" if i < 14 else "2025-03-01"
        winner = "p1" if i % 2 == 0 else "p2"
        for turn in (1, 2):
            state = copy.deepcopy(EXAMPLE)
            state["turn"] = turn
            for side in ("p1", "p2"):
                state["sides"][side]["player"] = f"synthetic-{i}-{side}"
                for mon in state["sides"][side]["pokemon"]:
                    mon["hp_percent"] = 90 if winner == side else 20
            rows.append({"battle_id": f"synthetic-{i}", "started_at": date, "winner": winner, "state": state,
                         "p1_team": f"synthetic-complete-team-{i}-p1", "p2_team": f"synthetic-complete-team-{i}-p2"})
    return rows


def test_one_observed_featurizer_ignores_labels_requests_ratings_and_player_identity():
    state = copy.deepcopy(EXAMPLE)
    before = featurize(state)
    state.update(winner="p2", request={"hidden": "future info"}, p1_action="move:explosion")
    state["sides"]["p1"].update(rating=3000, player="different player")
    assert featurize(state) == before
    assert len(before) == len(FEATURE_NAMES) and all(math.isfinite(x) for x in before)


def test_hp_baseline_matches_the_contract_formula():
    state = copy.deepcopy(EXAMPLE)
    for side in state["sides"].values():
        for mon in side["pokemon"]:
            mon["hp_percent"] = 100
    assert hp_baseline(state) == 0.5
    state["sides"]["p2"]["pokemon"][0]["hp_percent"] = 0
    assert hp_baseline(state) == pytest.approx(0.5 + 2 / 24)


def test_splits_group_entire_battles_by_time_and_keep_test_out_of_validation():
    splits, manifest = split_turns(synthetic_rows(), "2025-02-01", "2025-03-01")
    assert [len(splits[key]) for key in ("train", "validation", "test")] == [20, 8, 8]
    ids = [{r["battle_id"] for r in splits[key]} for key in ("train", "validation", "test")]
    assert not ids[0] & ids[1] and not ids[1] & ids[2] and not ids[0] & ids[2]
    assert manifest["splits"]["test"]["unseen_battle_ids"] == sorted(ids[2])


def test_repeated_players_and_teams_are_removed_from_the_strict_unseen_subset():
    rows = synthetic_rows()
    for row in rows:
        if row["battle_id"] == "synthetic-14":
            row["state"]["sides"]["p1"]["player"] = "synthetic-0-p1"
        if row["battle_id"] == "synthetic-15":
            row["p2_team"] = "synthetic-complete-team-10-p2"  # validation overlap also excluded
    splits, manifest = split_turns(rows, "2025-02-01", "2025-03-01")
    assert len(splits["test_unseen"]) == 4
    assert manifest["splits"]["test"]["shared_player_battles"] == 1
    assert manifest["splits"]["test"]["shared_team_battles"] == 1


def test_missing_exact_teams_use_an_explicitly_labeled_roster_proxy():
    rows = synthetic_rows()
    for row in rows:
        del row["p1_team"], row["p2_team"]
    splits, manifest = split_turns(rows, "2025-02-01", "2025-03-01")
    assert manifest["splits"]["test"]["roster_proxy_battles"] == 4
    assert not splits["test_unseen"]  # shared roster, despite different synthetic player names


def test_inconsistent_battle_dates_cannot_create_turn_level_leakage():
    rows = synthetic_rows()
    rows[1]["started_at"] = "2025-04-01"
    with pytest.raises(ValueError, match="inconsistent"):
        split_turns(rows, "2025-02-01", "2025-03-01")


def test_training_serving_and_saved_model_use_identical_features(tmp_path):
    rows = synthetic_rows()
    splits, _ = split_turns(rows, "2025-02-01", "2025-03-01")
    model = fit_model(splits["train"], epochs=100)
    calibrate(model, splits["validation"], epochs=100)
    model.save(tmp_path / "model.json")
    restored = WinModel.load(tmp_path / "model.json")
    assert restored.predict(rows[-1]["state"]) == model.predict(rows[-1]["state"])
    assert set(model.metadata["calibration_battles"]) == {r["battle_id"] for r in splits["validation"]}
    feature_mean = sum(featurize(r["state"])[0] for r in splits["train"]) / len(splits["train"])
    assert model.means[0] == pytest.approx(feature_mean)
    assert model.predict(splits["test"][0]["state"]) > 0.8
    assert model.predict(splits["test"][2]["state"]) < 0.2


def test_test_labels_do_not_influence_model_or_calibration(tmp_path, monkeypatch):
    from prediction import __main__ as cli
    monkeypatch.setattr(cli, "plot_calibration", lambda *_: None)
    rows = synthetic_rows()
    path = tmp_path / "turns.jsonl"
    def fit(records, output):
        path.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")
        args = SimpleNamespace(turns=path, validation_start="2025-02-01", test_start="2025-03-01",
                               epochs=60, rate=0.2, l2=0.001, source="synthetic", output=output)
        train(args)
        return WinModel.load(output / "model.json")
    before = fit(rows, tmp_path / "before")
    for row in rows:
        if row["started_at"] == "2025-03-01":
            row["winner"] = "p2" if row["winner"] == "p1" else "p1"
    after = fit(rows, tmp_path / "after")
    assert (before.weights, before.means, before.scales, before.calibration_slope, before.calibration_intercept) == (
        after.weights, after.means, after.scales, after.calibration_slope, after.calibration_intercept)


def test_jsonl_accepts_contract_jsonb_or_serialized_state(tmp_path):
    row = synthetic_rows()[0]
    row["state"] = json.dumps(row["state"])
    path = tmp_path / "turns.jsonl"
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert read_turns(path)[0]["state"]["us"] == "p1"


def test_binary_scores_and_calibration_bins():
    metrics = binary_metrics([0, 1], [0.5, 0.5])
    assert metrics["log_loss"] == pytest.approx(math.log(2)) and metrics["brier"] == 0.25
    assert sum(b["count"] for b in metrics["calibration"]) == 2
    assert binary_metrics([], []) is None


def candidates():
    return [{"weight": 0.75, "moves": ["tackle", "protect"], "item": "leftovers", "ability": "pressure",
             "tera_type": "normal", "spread": {"nature": "serious", "evs": [0] * 6}},
            {"weight": 0.25, "moves": ["protect", "recover"], "item": "airballoon", "ability": "pressure",
             "tera_type": "flying", "spread": {"nature": "serious", "evs": [0] * 6}}]


def test_next_new_move_predictions_form_a_distribution_with_stated_policy_assumption():
    distribution = reveal_distribution(candidates(), "move", ["tackle"])
    assert distribution == {"protect": 0.875, "recover": 0.125}
    assert sum(distribution.values()) == 1


def test_reveal_scores_compare_prior_hard_filter_updated_and_only_claim_groundtruth_coverage():
    original = candidates()
    updated = copy.deepcopy(original)
    updated[0]["weight"], updated[1]["weight"] = 0.95, 0.05
    record = {"source": "synthetic", "kind": "item", "revealed": "leftovers", "prior": original,
              "hard_filter": original, "updated": updated}
    result = score_reveals([record])["synthetic"]
    assert result["log_loss"]["updated"] < result["log_loss"]["prior"]
    assert result["full_set_coverage"]["prior"] is None
    record["ground_truth_set"] = original[0]
    result = score_reveals([record])["synthetic"]
    assert result["ground_truth_examples"] == 1 and result["full_set_coverage"]["updated"] == 1


def test_bot_and_human_belief_evidence_are_never_pooled():
    template = {"kind": "item", "revealed": "leftovers", **{k: candidates() for k in ("prior", "hard_filter", "updated")}}
    report = score_reveals([{**template, "source": "bot"}, {**template, "source": "human"}])
    assert set(report) == {"bot", "human"}


def test_opponent_scoring_smooths_zero_visit_options_and_excludes_unobserved_replies():
    decision = {"kind": "move", "decision_id": "b:1", "state": EXAMPLE,
                "opponent_support": {"makeitrain": 1.0},
                "worlds": [{"opponent_visits": [{"choice": "makeitrain", "visits": 10},
                                                 {"choice": "shadowball", "visits": 0}]}]}
    observation = {"kind": "observation", "decision_id": "b:1",
                   "opponent_actions": [{"kind": "move", "move": "shadowball", "slot": 2}]}
    unknown = {"kind": "observation", "decision_id": "b:2", "opponent_actions": None}
    result = score_opponent_traces([decision, observation, unknown], source="synthetic")
    assert result["observed_replies"] == 1 and result["unknown_replies_excluded"] == 1
    assert result["uniform_log_loss"] < result["visit_log_loss"] < math.inf


def test_model_schema_mismatch_is_rejected(tmp_path):
    model = fit_model(synthetic_rows()[:8], epochs=2)
    model.feature_version = -1
    model.save(tmp_path / "bad.json")
    with pytest.raises(ValueError, match="schema"):
        WinModel.load(tmp_path / "bad.json")


def test_opponent_scoring_namespaces_identical_ids_from_two_agent_trace_files():
    records = []
    for account in ("a", "b"):
        records += [{"kind": "move", "decision_id": "same-battle:1", "_trace_namespace": account,
                     "opponent_support": {"protect": 1}, "state": EXAMPLE},
                    {"kind": "observation", "decision_id": "same-battle:1", "_trace_namespace": account,
                     "opponent_actions": [{"kind": "move", "move": "protect"}]}]
    result = score_opponent_traces(records, source="synthetic")
    assert result["observed_replies"] == 2


def test_opponent_scoring_counts_team_preview_separately_from_unknown_root_actions():
    records = [{"kind": "team", "decision_id": "b:1"},
               {"kind": "observation", "decision_id": "b:1", "opponent_actions": None}]
    result = score_opponent_traces(records, source="synthetic")
    assert result["team_preview_excluded"] == 1 and result["unknown_replies_excluded"] == 0


def test_public_replay_importer_keeps_start_of_turn_states_separate_from_eventual_outcome():
    from pathlib import Path
    log = (Path(__file__).parents[1] / "bot/tests/fixtures/gen9ou-2703852247.log").read_text(encoding="utf-8")
    replay = {"id": "fixture-public", "formatid": "gen9ou", "private": 0, "log": log}
    rows, meta = replay_rows(replay)
    changed, _ = replay_rows({**replay, "log": log.replace("|win|Alice", "|win|Bob")})
    assert len(rows) == meta["turns"] == 34
    assert all(r["source"] == "public_ladder" and r["human_status"] == "unverified" for r in rows)
    assert [featurize(r["state"]) for r in rows] == [featurize(r["state"]) for r in changed]
    assert {r["winner"] for r in rows} != {r["winner"] for r in changed}


def test_bot_export_uses_completed_artifacts_true_winner_start_time_and_team_hash(tmp_path):
    from prediction.export import export_bot_turns
    folder = tmp_path / "eval"
    folder.mkdir()
    trace, raw = tmp_path / "trace.jsonl", tmp_path / "raw.log"
    trace.write_text(json.dumps({"kind": "move", "state": EXAMPLE}) + '\n{"kind":"end"}\n', encoding="utf-8")
    raw.write_text("|t:|100\n", encoding="utf-8")
    (tmp_path / "eval-manifest.json").write_text('{"team_hashes":["full-team-hash"]}', encoding="utf-8")
    game = {"winner": "a", "side": "p2", "battle": "battle-1", "team": 0,
            "artifacts": {"a": {"external_log": "foul-play.log", "searches": []},
                          "b": {"trace": str(trace), "raw_log": str(raw)}}}
    (folder / "a.jsonl").write_text(json.dumps(game) + "\n", encoding="utf-8")
    rows = export_bot_turns(tmp_path, both_perspectives=True)
    assert len(rows) == 2 and {r["state"]["us"] for r in rows} == {"p1", "p2"}
    assert {r["winner"] for r in rows} == {"p2"}
    assert rows[0]["started_at"] == "1970-01-01T00:01:40+00:00"
    assert rows[0]["p1_team"] == rows[0]["p2_team"] == "full-team-hash"
    trace.write_text(json.dumps({"kind": "move", "state": EXAMPLE}) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete"):
        export_bot_turns(tmp_path)


def test_belief_export_scores_the_previous_posterior_before_updating_on_target_reveal(tmp_path):
    from pathlib import Path
    from dataclasses import asdict
    from decision.belief import Belief
    from prediction.belief_export import export_belief_records
    from tests.test_belief import PRIORS
    first = copy.deepcopy(EXAMPLE)
    second = copy.deepcopy(first)
    second["turn"] += 1
    second["sides"]["p2"]["pokemon"][2]["item"] = "leftovers"
    belief = Belief(PRIORS, first)
    def snapshot():
        return [{"species": first["sides"]["p2"]["pokemon"][i]["species"],
                 "sets": [{"weight": w, **asdict(s)} for s, w in slot]} for i, slot in enumerate(belief.candidates)]
    before = snapshot()
    belief.update(second)
    after = snapshot()
    trace, raw = tmp_path / "trace.jsonl", tmp_path / "raw.log"
    trace.write_text("".join(json.dumps(record) + "\n" for record in [
        {"kind": "move", "decision_id": "b:1", "state": first, "belief_candidates": before},
        {"kind": "move", "decision_id": "b:2", "state": second, "belief_candidates": after}]), encoding="utf-8")
    raw.write_text((Path(__file__).parents[1] / "bot/tests/fixtures/gen9ou-2703852247.log").read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "eval").mkdir()
    (tmp_path / "eval/a.jsonl").write_text(json.dumps({"battle": "b", "artifacts": {
        "a": {"trace": str(trace), "raw_log": str(raw)},
        "b": {"external_log": "foul-play.log", "searches": []}}}) + "\n", encoding="utf-8")
    records, summary = export_belief_records(tmp_path, PRIORS)
    [item] = [r for r in records if r["decision_id"] == "b:1" and r["kind"] == "item"]
    assert item["updated"] == json.loads(json.dumps(before[2]["sets"]))
    assert item["updated"] != json.loads(json.dumps(after[2]["sets"]))
    assert item["revealed"] == "leftovers" and summary["revelations"] > 0
    assert summary["external_roles_without_trace"] == 1
