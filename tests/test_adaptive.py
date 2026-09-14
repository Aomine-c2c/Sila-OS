"""
KAIROS Adaptive Evolution Intelligence (AEI) Unit Tests
Validates the 11-stage adaptation loop, candidate lifecycle states,
permitted mutation targets, strict prohibition of risk/credential mutation,
and episodic rollback memory ('Rollback is memory. A failed adaptation becomes knowledge').
"""

import unittest
import os
import shutil
import tempfile
from adaptive.evolution_engine import AdaptiveEvolutionEngine, TelemetryFrame
from adaptive.aei import (
    CandidateLifecycle,
    MonitoredSignal,
    PermittedTarget,
    PROHIBITED_MUTATION_TARGETS,
    AdaptationRecord,
    AEISecurityGate,
    AEIMemoryBank,
    AdaptiveEvolutionSystem
)


class TestAdaptiveEvolutionLegacy(unittest.TestCase):
    def setUp(self):
        self.engine = AdaptiveEvolutionEngine()

    def test_optimal_state_no_unnecessary_changes(self):
        frame = TelemetryFrame(avg_packet_latency_us=5.0, cpu_jitter_us=0.5, memory_pressure_pct=40.0)
        result = self.engine.evaluate_and_adapt(frame)
        self.assertEqual(result["status"], "OPTIMAL")
        self.assertEqual(self.engine.current_poll_budget, 50)

    def test_latency_adaptation_within_bounds(self):
        frame = TelemetryFrame(avg_packet_latency_us=25.0, cpu_jitter_us=1.5, memory_pressure_pct=50.0)
        result = self.engine.evaluate_and_adapt(frame)
        self.assertEqual(result["status"], "ADAPTED")
        self.assertEqual(self.engine.current_poll_budget, 60)
        self.assertIn("Adjusted net.core.busy_poll to 60", result["actions"][0])


class TestAdaptiveEvolutionIntelligence(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.aei = AdaptiveEvolutionSystem(storage_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_all_11_stages_executed_in_order(self):
        """
        Verify the complete 11-stage loop:
        OBSERVE -> DIAGNOSE -> MEASURE -> GENERATE -> TEST ->
        VALIDATE -> SHADOW -> DEPLOY -> MONITOR -> ACCEPT -> MEMORIZE
        """
        expected_stages = [
            "OBSERVE", "DIAGNOSE", "MEASURE", "GENERATE", "TEST",
            "VALIDATE", "SHADOW", "DEPLOY", "MONITOR", "ACCEPT", "MEMORIZE"
        ]
        telemetry = {
            "rolling_sharpe": 1.05,
            "slippage_bps": 3.1,
            "orderbook_drift_ks": 0.45,
            "regret_metric": 0.22,
            "volatility_regime": "HIGH_VOLATILITY_EXPANSION"
        }
        res = self.aei.run_adaptation_cycle(telemetry=telemetry)
        self.assertEqual(res["status"], "SUCCESS_DEPLOYED")
        self.assertEqual(res["stages_completed"], expected_stages)

    def test_all_8_monitored_signals(self):
        """
        AEI must monitor:
        - performance deterioration
        - market regime changes
        - drift
        - regret
        - novelty
        - uncertainty
        - execution degradation
        - fitness deterioration
        """
        expected_signals = [
            "performance deterioration",
            "market regime changes",
            "drift",
            "regret",
            "novelty",
            "uncertainty",
            "execution degradation",
            "fitness deterioration"
        ]
        signal_values = [s.value for s in MonitoredSignal]
        for exp in expected_signals:
            self.assertIn(exp, signal_values)

        # Trigger cycles with each signal
        for sig in MonitoredSignal:
            res = self.aei.run_adaptation_cycle(forced_signal=sig)
            self.assertIn(res["status"], ("SUCCESS_DEPLOYED", "NOMINAL"))

    def test_all_8_permitted_targets(self):
        """
        AEI may propose changes to:
        - indicator parameters
        - strategy thresholds
        - strategy weights
        - strategy routing
        - feature selection
        - confidence thresholds
        - execution timing
        - position-size multipliers
        """
        expected_targets = [
            "indicator parameters",
            "strategy thresholds",
            "strategy weights",
            "strategy routing",
            "feature selection",
            "confidence thresholds",
            "execution timing",
            "position-size multipliers"
        ]
        target_values = [t.value for t in PermittedTarget]
        for exp in expected_targets:
            self.assertIn(exp, target_values)
            is_safe, msg = AEISecurityGate.validate_mutation_target(exp, {})
            self.assertTrue(is_safe)
            self.assertEqual(msg, "TARGET_PERMITTED")

    def test_hard_security_invariants_prohibited_targets(self):
        """
        AEI MUST NOT modify:
        - risk hard limits
        - credentials
        - permissions
        - security policies
        - audit integrity
        - kill switch
        - core execution safety
        """
        prohibited_tests = [
            "risk hard limits",
            "credentials",
            "permissions",
            "security policies",
            "audit integrity",
            "kill switch",
            "core execution safety",
            "max_position_size",
            "max_drawdown_pct",
            "vault_keys"
        ]
        for bad_target in prohibited_tests:
            is_safe, reason = AEISecurityGate.validate_mutation_target(bad_target, {})
            self.assertFalse(is_safe)
            self.assertIn("SECURITY VIOLATION", reason)

    def test_every_adaptation_has_required_schema(self):
        """
        Every adaptation must have:
        adaptation_id, reason, baseline, candidate, evidence,
        validation_result, deployment_scope, performance, rollback_state.
        """
        res = self.aei.run_adaptation_cycle(
            telemetry={"rolling_sharpe": 0.95, "volatility_regime": "HIGH_VOLATILITY_EXPANSION"}
        )
        adapt = res["adaptation"]
        self.assertIn("adaptation_id", adapt)
        self.assertIn("reason", adapt)
        self.assertIn("baseline", adapt)
        self.assertIn("candidate", adapt)
        self.assertIn("evidence", adapt)
        self.assertIn("validation_result", adapt)
        self.assertIn("deployment_scope", adapt)
        self.assertIn("performance", adapt)
        self.assertIn("rollback_state", adapt)

    def test_candidate_lifecycle_states(self):
        """
        Candidate lifecycle:
        BASELINE, CANDIDATE, VALIDATED, SHADOW, DEPLOYED, ROLLED_BACK.
        """
        expected_states = [
            "BASELINE",
            "CANDIDATE",
            "VALIDATED",
            "SHADOW",
            "DEPLOYED",
            "ROLLED_BACK"
        ]
        lifecycle_values = [s.value for s in CandidateLifecycle]
        for exp in expected_states:
            self.assertIn(exp, lifecycle_values)

    def test_failed_adaptation_becomes_knowledge_rollback_is_memory(self):
        """
        Core Axiom:
        'A failed adaptation becomes knowledge. Rollback is memory.'
        Verify rollback restores baseline and records lesson in memory bank.
        """
        # 1. Run successful cycle
        res = self.aei.run_adaptation_cycle(
            telemetry={"rolling_sharpe": 1.05},
            target_override=PermittedTarget.STRATEGY_WEIGHTS
        )
        adapt_id = res["adaptation"]["adaptation_id"]

        # Check deployed state
        self.assertEqual(self.aei.active_config["strategy_weights"]["strat_orderflow"], 0.40)

        # 2. Trigger rollback
        rb_res = self.aei.rollback_adaptation(adapt_id, reason="Performance degradation in paper test")
        self.assertEqual(rb_res["status"], "ROLLED_BACK")
        self.assertTrue(rb_res["memorized_knowledge"])

        # Check baseline was restored
        self.assertEqual(self.aei.active_config["strategy_weights"]["strat_orderflow"], 0.20)

        # 3. Verify rollback committed into episodic memory
        knowledge = self.aei.get_memory_log()
        self.assertGreaterEqual(len(knowledge), 1)
        latest_lesson = knowledge[0]
        self.assertEqual(latest_lesson["outcome"], "ROLLED_BACK")
        self.assertEqual(latest_lesson["adaptation_id"], adapt_id)
        self.assertIn("Preserving negative knowledge", latest_lesson["lesson"])


if __name__ == "__main__":
    unittest.main()
