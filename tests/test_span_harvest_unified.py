import json
import unittest
from dataclasses import replace

from span_harvest_unified import (
    ClockReference,
    ExecutionObservation,
    Gate,
    Profile,
    ShadowFillRecord,
    Tape,
    Trade,
    clustered_lower_bound_95,
    cluster_bootstrap_lower_bound_95,
    calibrated_rate,
    evaluate_execution_gate,
    execution_observation_at,
    exit_surface_library,
    familywise_lower_bound_95,
    group_key,
    profile_hash,
    profile_library,
    replay_unified,
    reconcile_shadow_fill,
    run_cost_stress,
    select_profile,
    shock_coordinates,
    simulate_profile,
    summarize_trades,
    normal_lower_bound,
    wilson_lower_bound,
)


def tape(prices, *, opening=None, result="won", end_recorded=True, match_id="m", sport="tennis", cohort="tp_only_fav"):
    values = tuple(float(value) for value in prices)
    opening = values[0] if opening is None else float(opening)
    return Tape(
        match_id=match_id,
        sport=sport,
        cohort=cohort,
        opening=opening,
        prices=values,
        times=tuple(float(i * 60) for i in range(len(values))),
        result=result,
        start_ts=0.0,
        settlement_i=None,
        end_recorded=end_recorded,
    )


CLOCK = ClockReference({"tennis": 120.0}, 120.0)


class SpanHarvestUnifiedTests(unittest.TestCase):
    def test_r1_uses_first_crossing_price_and_no_same_print_exit(self):
        result = simulate_profile(tape([0.25, 0.70, 0.80, 1.0], opening=0.50), Profile("base"), CLOCK)
        self.assertEqual(result.entry_i, 0)
        self.assertAlmostEqual(result.entries[0]["price"], 0.25)
        self.assertTrue(all(row["i"] > result.entry_i for row in result.exits))

    def test_r1_later_crossing_uses_resting_limit(self):
        result = simulate_profile(tape([0.40, 0.30, 0.80, 1.0], opening=0.60), Profile("base"), CLOCK)
        self.assertEqual(result.entry_i, 1)
        self.assertAlmostEqual(result.entries[0]["price"], 0.33)

    def test_conditional_add_requires_bounce(self):
        result = simulate_profile(tape([0.25, 0.18, 0.20, 0.21, 0.80, 1.0], opening=0.50), Profile("base"), CLOCK)
        self.assertEqual([row["rung"] for row in result.entries], [1, 2, 3])
        self.assertEqual(result.entries[1]["i"], 2)
        self.assertEqual(result.entries[2]["i"], 3)

    def test_unknown_end_is_not_awarded(self):
        result = simulate_profile(tape([0.25, 0.70, 0.80], opening=0.50, result="won", end_recorded=False), Profile("base"), CLOCK)
        self.assertEqual(result.status, "UNRESOLVED")
        self.assertIsNone(result.pnl)

    def test_unknown_pending_entry_is_unresolved(self):
        result = simulate_profile(tape([0.50, 0.50], opening=0.50, result="lost", end_recorded=False), Profile("base"), CLOCK)
        self.assertEqual(result.status, "UNRESOLVED")
        self.assertIsNone(result.pnl)

    def test_fee_stress_reduces_net(self):
        clean = simulate_profile(tape([0.25, 0.80, 1.0], opening=0.50), Profile("base"), CLOCK, fee_per_share=0.0)
        stressed = simulate_profile(tape([0.25, 0.80, 1.0], opening=0.50), Profile("base"), CLOCK, fee_per_share=0.01)
        self.assertLess(stressed.pnl, clean.pnl)

    def test_shock_coordinate_is_finite_and_causal(self):
        result = shock_coordinates(tape([0.50, 0.40, 0.30, 0.35]), 3, CLOCK, 2.0)
        self.assertIsNotNone(result)
        self.assertTrue(all(abs(value) < 100.0 for value in result))

    def test_hierarchy_uses_concrete_current_keys(self):
        current = tape([0.50, 1.0], match_id="current")
        other_sport = tape([0.50, 1.0], match_id="other", sport="mlb")
        self.assertEqual(group_key(current, "sport_cohort"), ("tennis", "tp_only_fav"))
        self.assertNotEqual(group_key(other_sport, "sport_cohort"), group_key(current, "sport_cohort"))

    def test_selector_ignores_current_outcome(self):
        prior = [tape([0.25, 0.80, 1.0], opening=0.50, match_id=f"p{i}") for i in range(3)]
        current_won = tape([0.25, 0.80, 1.0], opening=0.50, match_id="current", result="won")
        current_lost = tape([0.25, 0.80, 0.0], opening=0.50, match_id="current", result="lost")
        gate = Gate(minimum_prior_matches=2, minimum_prior_fills=1, minimum_coverage=0.5)
        first, first_receipt = select_profile(current_won, prior, CLOCK, [Profile("candidate")], gate)
        second, second_receipt = select_profile(current_lost, prior, CLOCK, [Profile("candidate")], gate)
        self.assertIsNotNone(first)
        self.assertEqual(first.profile_id, second.profile_id)
        self.assertEqual(first_receipt["group"], second_receipt["group"])

    def test_selector_abstains_when_lower_bound_is_not_positive(self):
        prior = [tape([0.25, 0.20, 0.18, 0.15, 0.0], opening=0.50, result="lost", match_id=f"p{i}") for i in range(3)]
        current = tape([0.25, 0.80, 1.0], opening=0.50, match_id="current")
        gate = Gate(minimum_prior_matches=2, minimum_prior_fills=1, minimum_coverage=0.5)
        profile, receipt = select_profile(current, prior, CLOCK, [Profile("candidate")], gate)
        self.assertIsNone(profile)
        self.assertEqual(receipt["reason"], "NO_PROFILE_CLEARS_GATE")

    def test_selector_does_not_count_unresolved_fills_as_valid_history(self):
        prior = [tape([0.25, 0.20], opening=0.50, result="won", end_recorded=False, match_id="p0")]
        current = tape([0.25, 0.80, 1.0], opening=0.50, match_id="current")
        gate = Gate(minimum_prior_matches=1, minimum_prior_fills=1, minimum_coverage=0.0)
        profile, receipt = select_profile(current, prior, CLOCK, [Profile("candidate")], gate)
        self.assertIsNone(profile)
        self.assertEqual(receipt["reason"], "NO_PROFILE_CLEARS_GATE")
        self.assertEqual(receipt["candidates"][0]["filled"], 1)
        self.assertEqual(receipt["candidates"][0]["resolved_filled"], 0)

    def test_embargo_excludes_recent_history_from_profile_selection(self):
        prior = replace(tape([0.25, 0.80, 1.0], opening=0.50, match_id="p0"), start_ts=0.0)
        current = replace(tape([0.25, 0.80, 1.0], opening=0.50, match_id="current"), start_ts=60.0)
        gate = Gate(minimum_prior_matches=1, minimum_prior_fills=1, minimum_coverage=0.5, embargo_seconds=120.0)
        profile, receipt = select_profile(current, [prior], CLOCK, [Profile("candidate")], gate)
        self.assertIsNone(profile)
        self.assertEqual(receipt["reason"], "INSUFFICIENT_HISTORY")

    def test_clustered_bound_penalizes_regime_concentration(self):
        trades = [
            Trade("a", "tennis", "p", "RESOLVED", 0, 0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.20, "X", start_ts=0.0),
            Trade("b", "tennis", "p", "RESOLVED", 0, 0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.20, "X", start_ts=0.0),
            Trade("c", "tennis", "p", "RESOLVED", 0, 0, 1.0, 1.0, 1.0, 0.0, 0.0, -0.10, "X", start_ts=86400.0),
            Trade("d", "tennis", "p", "RESOLVED", 0, 0, 1.0, 1.0, 1.0, 0.0, 0.0, -0.10, "X", start_ts=86400.0),
        ]
        self.assertLess(clustered_lower_bound_95(trades), normal_lower_bound([trade.pnl for trade in trades]))
        self.assertEqual(summarize_trades(trades)["cluster_count"], 2)

    def test_execution_gate_requires_positive_costed_ev(self):
        observation = ExecutionObservation(0.49, 0.50, 500.0, 500.0, 20.0, 100.0, 100.2)
        decision = evaluate_execution_gate(
            observation,
            target_bid=0.80,
            fill_probability=0.80,
            target_hit_probability=0.90,
            fallback_return=-0.05,
            fee_per_share=0.01,
            slippage_per_share=0.005,
            queue_penalty=0.01,
            latency_penalty=0.01,
            ev_uncertainty=0.02,
        )
        self.assertEqual(decision["state"], "EDGE_OK")
        self.assertGreater(decision["ev_lower_bound"], 0.0)

    def test_execution_gate_fails_closed_on_stale_or_missing_book(self):
        missing = ExecutionObservation(None, 0.50, 500.0, 500.0, 20.0, 100.0, 100.2)
        self.assertEqual(evaluate_execution_gate(missing, target_bid=0.80, fill_probability=0.8, target_hit_probability=0.9, fallback_return=0.0)["reason"], "MISSING_EXECUTION_DATA")
        stale = ExecutionObservation(0.49, 0.50, 500.0, 500.0, 20.0, 100.0, 104.0)
        self.assertEqual(evaluate_execution_gate(stale, target_bid=0.80, fill_probability=0.8, target_hit_probability=0.9, fallback_return=0.0)["reason"], "STALE_EXECUTION_DATA")

    def test_optional_execution_book_is_parsed_and_used_as_of_event(self):
        record = {
            "id": "booked",
            "sport": "tennis",
            "open": 0.50,
            "p": [0.50, 0.30, 0.80, 1.0],
            "t": [0, 60, 120, 180],
            "result": "won",
            "end_recorded": True,
            "book_snapshots": [
                {"event_ts": 60, "best_bid": 0.29, "best_ask": 0.30, "bid_depth": 100, "ask_depth": 100, "queue_ahead": 5},
            ],
        }
        parsed = Tape.from_record(record)
        self.assertIsNotNone(parsed)
        self.assertEqual(len(parsed.execution_observations), 1)
        self.assertEqual(execution_observation_at(parsed, 59), None)
        self.assertAlmostEqual(execution_observation_at(parsed, 60).best_ask, 0.30)
        result = simulate_profile(parsed, Profile("book", early_multiplier=0.70), CLOCK, require_execution_book=True)
        self.assertEqual(result.entry_i, 1)
        self.assertAlmostEqual(result.entries[0]["price"], 0.30)

    def test_strict_execution_book_fails_closed_without_observations(self):
        result = simulate_profile(tape([0.25, 0.80, 1.0]), Profile("book"), CLOCK, require_execution_book=True)
        self.assertIsNone(result.entry_i)
        self.assertEqual(result.exit_reason, "NO_FILL")

    def test_causal_features_include_acceleration_and_drawdown(self):
        from span_harvest_unified import prepare_features
        features = prepare_features(tape([0.50, 0.40, 0.45, 0.80]), CLOCK)
        self.assertEqual(len(features.slope_2m), 4)
        self.assertEqual(len(features.slope_acceleration), 4)
        self.assertEqual(len(features.drawdown_from_causal_peak), 4)
        self.assertGreaterEqual(features.drawdown_from_causal_peak[1], 0.0)

    def test_calibration_and_multiple_testing_bounds_are_conservative(self):
        self.assertLess(familywise_lower_bound_95([0.1, 0.2, 0.3], 10), normal_lower_bound([0.1, 0.2, 0.3]))
        self.assertLess(wilson_lower_bound(2, 10), 0.2)
        bins = calibrated_rate([0.1, 0.1, 0.9, 0.9], [False, True, True, True], bins=2)
        self.assertEqual(len(bins), 2)
        self.assertEqual(bins[0]["count"], 2)

    def test_exit_surface_is_bounded_and_distinct_from_production_registry(self):
        surface = exit_surface_library()
        self.assertEqual(len(surface), 12)
        self.assertEqual(len({profile.profile_id for profile in surface}), 12)
        self.assertNotEqual({profile.profile_id for profile in surface}, {profile.profile_id for profile in profile_library()})

    def test_cluster_bootstrap_is_deterministic(self):
        trades = [
            Trade("a", "tennis", "p", "RESOLVED", 0, 0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.20, "X", start_ts=0.0),
            Trade("b", "tennis", "p", "RESOLVED", 0, 0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.10, "X", start_ts=86400.0),
        ]
        self.assertEqual(cluster_bootstrap_lower_bound_95(trades), cluster_bootstrap_lower_bound_95(trades))

    def test_shadow_reconciliation_is_fail_closed_and_auditable(self):
        pending = reconcile_shadow_fill(ShadowFillRecord("d1", "EDGE_OK", 0.30, 3.0, 100.0))
        self.assertEqual(pending["status"], "PENDING_OBSERVATION")
        matched = reconcile_shadow_fill(ShadowFillRecord("d1", "EDGE_OK", 0.30, 3.0, 100.0, 0.305, 3.0, 100.4))
        self.assertEqual(matched["status"], "RECONCILED")
        rejected = reconcile_shadow_fill(ShadowFillRecord("d2", "NO_TRADE", 0.30, 3.0, 100.0, 0.30, 3.0, 100.1))
        self.assertEqual(rejected["status"], "NOT_ACTIONABLE")

    def test_cost_stress_reuses_same_replay_contract(self):
        tapes = [tape([0.25, 0.80, 1.0], opening=0.50, match_id=f"m{i}") for i in range(4)]
        gate = Gate(minimum_prior_matches=1, minimum_prior_fills=1, minimum_coverage=0.5, warmup_matches=1)
        stressed = run_cost_stress(tapes, CLOCK, fee_levels=(0.0, 0.01), profiles=[Profile("candidate")], gate=gate)
        self.assertEqual(len(stressed), 2)
        self.assertLessEqual(stressed[1]["summary"]["total_net"], stressed[0]["summary"]["total_net"])

    def test_replay_is_deterministic_and_has_warmup(self):
        tapes = [tape([0.25, 0.80, 1.0], opening=0.50, match_id=f"m{i}") for i in range(5)]
        gate = Gate(minimum_prior_matches=2, minimum_prior_fills=1, minimum_coverage=0.5, warmup_matches=2)
        first = replay_unified(tapes, CLOCK, profiles=[Profile("candidate")], gate=gate)
        second = replay_unified(tapes, CLOCK, profiles=[Profile("candidate")], gate=gate)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertEqual(first["decisions"][0]["reason"], "WALK_FORWARD_WARMUP")

    def test_profile_registry_is_frozen_and_has_expected_count(self):
        profiles = profile_library()
        self.assertEqual(len(profiles), 14)
        self.assertEqual(profile_hash(profiles), profile_hash(tuple(profiles)))

    def test_shock_profile_requires_recovery_before_entry(self):
        result = simulate_profile(tape([0.50, 0.45, 0.40, 0.45, 0.80, 1.0]), Profile("shock", shock_required=True), CLOCK)
        self.assertIn(result.status, {"NO_TRADE", "UNRESOLVED", "RESOLVED"})
        self.assertTrue(result.entry_i is None or result.entry_i >= 3)


if __name__ == "__main__":
    unittest.main()
