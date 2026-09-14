import unittest
import time
from trading.risk_gatekeeper import (
    RiskGatekeeper,
    OrderDecision,
    ExecutionEngine
)

class TestTradingRiskGatekeeper(unittest.TestCase):
    def setUp(self):
        self.risk = RiskGatekeeper(max_position_size=10.0, max_drawdown_pct=0.02)
        self.engine = ExecutionEngine(self.risk)

    def test_nominal_order_approved(self):
        decision = OrderDecision(
            timestamp_ns=time.time_ns(),
            symbol="SPY",
            side="BUY",
            quantity=5.0,
            order_type="LIMIT",
            price=500.0,
            strategy_id="strat_stat_arb_01"
        )
        result = self.engine.execute_decision(decision)
        self.assertEqual(result["status"], "SENT_TO_BROKER")
        self.assertTrue(result["verdict"].approved)

    def test_oversized_order_rejected(self):
        decision = OrderDecision(
            timestamp_ns=time.time_ns(),
            symbol="SPY",
            side="BUY",
            quantity=50.0, # Exceeds limit of 10.0
            order_type="LIMIT",
            price=500.0,
            strategy_id="strat_rogue_ai_01"
        )
        result = self.engine.execute_decision(decision)
        self.assertEqual(result["status"], "REJECTED_BY_RISK")
        self.assertFalse(result["verdict"].approved)
        self.assertIn("exceeds hard limit", result["verdict"].reason)

    def test_circuit_breaker_on_drawdown(self):
        self.risk.current_drawdown_pct = 0.05 # Exceeds 0.02
        decision = OrderDecision(
            timestamp_ns=time.time_ns(),
            symbol="BTC-USD",
            side="BUY",
            quantity=1.0,
            order_type="MARKET",
            price=None,
            strategy_id="strat_momentum_01"
        )
        result = self.engine.execute_decision(decision)
        self.assertEqual(result["status"], "REJECTED_BY_RISK")
        self.assertFalse(result["verdict"].approved)
        self.assertIn("drawdown exceeded", result["verdict"].reason)

if __name__ == "__main__":
    unittest.main()
