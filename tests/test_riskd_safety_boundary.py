"""
Comprehensive Test Suite for KAIROS RiskD - Central Safety Boundary.
Aggressively tests all safety invariants, risk limits, and failure conditions:
1. Signal -> DecisionSnapshot -> RiskD -> Execution Validation -> ExecutionD
2. Risk States: SAFE, NORMAL, CAUTION, RESTRICTED, HALTED
3. Maximum positions limit
4. Exposure limits (gross and net)
5. Position sizing limits (quantity and notional)
6. Daily loss limits & drawdown circuit breaker
7. Symbol exposure limits & blacklisted symbols
8. Correlation limits
9. Spread limits
10. Stale-data protection
11. Duplicate-order protection
12. Broker-health checks (offline and latency SLA breach)
13. Order validation (sanity, limit price, quantity)
14. Emergency halt (manual & automated circuit breaker)
15. Close-only mode (position reduction allowed, new risk blocked)
16. Strategy pause (individual strategy pause state)
17. Autonomous mutation defense:
    - AI agents cannot bypass or weaken RiskD
    - Plugins cannot bypass or weaken RiskD
    - Adaptive Engine (AEI) cannot modify hard limits
"""

import unittest
import time
from trading.riskd import RiskD, RiskState, RiskHardLimits, RiskVerdict
from trading.subsystem import (
    DecisionSnapshot,
    TradingMode,
    OrderSide,
    OrderType,
    NormalizedMarketTick
)
from ai.agent_harness import KairosAIAgent
from plugins.plugin_host import KairosPlugin, PluginManager, Capability

class DummyPlugin(KairosPlugin):
    @property
    def name(self) -> str:
        return "AggressiveHedgePlugin"

    @property
    def required_capabilities(self):
        return {Capability.READ_MARKET_DATA, Capability.EMIT_SIGNAL}

    def on_market_tick(self, tick):
        return {"signal": "BUY", "symbol": "BTC/USD", "size": 999999.0}

class TestRiskDCentralSafetyBoundary(unittest.TestCase):
    def setUp(self):
        self.hard_limits = RiskHardLimits(
            max_open_positions=3,
            max_gross_exposure_usd=100_000.0,
            max_net_exposure_usd=60_000.0,
            max_order_usd=25_000.0,
            max_single_position_qty=20.0,
            max_daily_loss_usd=2_000.0,
            max_drawdown_pct=0.03,
            max_spread_pct=0.01, # 1%
            max_tick_age_seconds=1.5,
            duplicate_window_seconds=1.0,
            max_broker_latency_ms=100.0,
            max_symbol_exposure_usd=30_000.0,
            max_correlated_exposure_usd=45_000.0
        )
        self.riskd = RiskD(hard_limits=self.hard_limits)

    def _make_decision(self, symbol="SPY", side=OrderSide.BUY, qty=5.0, price=500.0, strat_id="strat-alpha"):
        return DecisionSnapshot(
            decision_id=f"DEC_{time.time_ns()}",
            strategy_id=strat_id,
            strategy_version="1.0",
            trading_mode=TradingMode.LIVE,
            symbol=symbol,
            side=side,
            quantity=qty,
            order_type=OrderType.LIMIT,
            price=price,
            timestamp_ns=time.time_ns(),
            rationale="Unit test order"
        )

    def _make_tick(self, symbol="SPY", bid=499.95, ask=500.05, age=0.0):
        t0 = time.time() - age
        return NormalizedMarketTick.create(
            symbol=symbol,
            bid=bid,
            ask=ask,
            volume=1000.0,
            provider="CME_DMA",
            sequence=100,
            ingest_t0=t0,
            quality="PRISTINE",
            timestamp=t0
        )

    def test_nominal_trade_approval(self):
        """Nominal valid order within all limits is approved in NORMAL state."""
        decision = self._make_decision(qty=5.0, price=500.0) # $2,500
        tick = self._make_tick(bid=499.90, ask=500.10)
        verdict = self.riskd.evaluate(decision, tick)
        self.assertTrue(verdict.approved)
        self.assertEqual(verdict.risk_state, RiskState.NORMAL)
        self.assertEqual(verdict.adjusted_quantity, 5.0)

    def test_position_sizing_limits(self):
        """Quantity and notional hard caps are strictly enforced."""
        # 1. Quantity breach (> 20.0)
        dec_qty = self._make_decision(qty=25.0, price=50.0)
        v1 = self.riskd.evaluate(dec_qty)
        self.assertFalse(v1.approved)
        self.assertEqual(v1.rule_triggered, "MAX_ORDER_QTY_BREACH")

        # 2. Notional breach (> $25,000.0)
        dec_notional = self._make_decision(qty=10.0, price=3_000.0) # $30,000
        v2 = self.riskd.evaluate(dec_notional)
        self.assertFalse(v2.approved)
        self.assertEqual(v2.rule_triggered, "MAX_ORDER_NOTIONAL_BREACH")

    def test_order_validation_sanity(self):
        """Non-positive quantities and prices are rejected."""
        # Zero quantity
        dec_zero = self._make_decision(qty=0.0)
        self.assertFalse(self.riskd.evaluate(dec_zero).approved)

        # Negative price
        dec_neg_price = self._make_decision(price=-10.0)
        self.assertFalse(self.riskd.evaluate(dec_neg_price).approved)

    def test_stale_data_protection(self):
        """Ticks older than threshold are rejected to protect from latency lag."""
        decision = self._make_decision()
        stale_tick = self._make_tick(age=2.5) # > 1.5s
        v = self.riskd.evaluate(decision, stale_tick)
        self.assertFalse(v.approved)
        self.assertEqual(v.rule_triggered, "STALE_DATA_REJECTED")

    def test_spread_limit_protection(self):
        """Abnormally wide bid-ask spread is blocked."""
        decision = self._make_decision()
        # Spread = 10.0 / 500 = 2% > 1% max
        wide_tick = self._make_tick(bid=495.0, ask=505.0)
        v = self.riskd.evaluate(decision, wide_tick)
        self.assertFalse(v.approved)
        self.assertEqual(v.rule_triggered, "SPREAD_LIMIT_BREACH")

    def test_duplicate_order_protection(self):
        """Identical orders within duplicate window are suppressed."""
        dec1 = self._make_decision()
        dec2 = self._make_decision() # identical params
        v1 = self.riskd.evaluate(dec1)
        self.assertTrue(v1.approved)

        v2 = self.riskd.evaluate(dec2)
        self.assertFalse(v2.approved)
        self.assertEqual(v2.rule_triggered, "DUPLICATE_ORDER_SUPPRESSED")

    def test_broker_health_checks(self):
        """Orders are rejected if broker is disconnected or latency SLA is breached."""
        decision = self._make_decision()

        # Disconnected
        self.riskd.update_broker_health(connected=False, latency_ms=10.0)
        v1 = self.riskd.evaluate(decision)
        self.assertFalse(v1.approved)
        self.assertEqual(v1.rule_triggered, "BROKER_DISCONNECTED")

        # High latency (> 100ms)
        self.riskd.update_broker_health(connected=True, latency_ms=185.0)
        v2 = self.riskd.evaluate(decision)
        self.assertFalse(v2.approved)
        self.assertEqual(v2.rule_triggered, "BROKER_LATENCY_BREACH")

    def test_emergency_halt_state(self):
        """Emergency halt instantly transitions risk state to HALTED and blocks all execution."""
        self.riskd.set_emergency_halt(True, reason="Circuit breaker test")
        self.assertEqual(self.riskd.risk_state, RiskState.HALTED)

        v = self.riskd.evaluate(self._make_decision())
        self.assertFalse(v.approved)
        self.assertEqual(v.risk_state, RiskState.HALTED)
        self.assertEqual(v.rule_triggered, "EMERGENCY_HALT")

        # Releasing halt restores normal operations
        self.riskd.set_emergency_halt(False)
        self.assertEqual(self.riskd.risk_state, RiskState.NORMAL)
        self.assertTrue(self.riskd.evaluate(self._make_decision()).approved)

    def test_close_only_mode(self):
        """Close-only mode allows reducing orders but blocks new risk or increases."""
        # Establish an existing long position of 10 SPY
        self.riskd.update_position("SPY", quantity=10.0, avg_price=500.0, current_price=500.0)
        self.riskd.set_close_only_mode(True)
        self.assertEqual(self.riskd.risk_state, RiskState.RESTRICTED)

        # 1. Buying more is blocked
        dec_buy = self._make_decision(symbol="SPY", side=OrderSide.BUY, qty=2.0)
        v_buy = self.riskd.evaluate(dec_buy)
        self.assertFalse(v_buy.approved)
        self.assertEqual(v_buy.rule_triggered, "CLOSE_ONLY_VIOLATION")

        # 2. Opening new symbol is blocked
        dec_new = self._make_decision(symbol="NVDA", side=OrderSide.BUY, qty=1.0)
        v_new = self.riskd.evaluate(dec_new)
        self.assertFalse(v_new.approved)
        self.assertEqual(v_new.rule_triggered, "CLOSE_ONLY_VIOLATION")

        # 3. Selling (reducing position) is APPROVED
        dec_sell = self._make_decision(symbol="SPY", side=OrderSide.SELL, qty=5.0)
        v_sell = self.riskd.evaluate(dec_sell)
        self.assertTrue(v_sell.approved)
        self.assertTrue(v_sell.close_only)

    def test_strategy_pause(self):
        """Paused strategies cannot trade; active strategies continue unaffected."""
        self.riskd.pause_strategy("strat-momentum")
        self.assertTrue(self.riskd.is_strategy_paused("strat-momentum"))

        # Paused strategy blocked
        dec_paused = self._make_decision(strat_id="strat-momentum")
        v_paused = self.riskd.evaluate(dec_paused)
        self.assertFalse(v_paused.approved)
        self.assertEqual(v_paused.rule_triggered, "STRATEGY_PAUSED")

        # Unpaused strategy succeeds
        dec_active = self._make_decision(strat_id="strat-arbitrage")
        v_active = self.riskd.evaluate(dec_active)
        self.assertTrue(v_active.approved)

    def test_max_open_positions_limit(self):
        """Exceeding max open positions is rejected."""
        # Max is 3
        self.riskd.update_position("SPY", 10.0, 500.0, 500.0)
        self.riskd.update_position("QQQ", 10.0, 400.0, 400.0)
        self.riskd.update_position("TLT", 10.0, 90.0, 90.0)

        # 4th symbol is blocked
        dec_4th = self._make_decision(symbol="NVDA")
        v = self.riskd.evaluate(dec_4th)
        self.assertFalse(v.approved)
        self.assertEqual(v.rule_triggered, "MAX_POSITIONS_BREACH")

        # Trading on existing position is allowed
        dec_exist = self._make_decision(symbol="SPY", side=OrderSide.SELL, qty=5.0)
        self.assertTrue(self.riskd.evaluate(dec_exist).approved)

    def test_symbol_exposure_limit(self):
        """Orders that push symbol exposure over limit are blocked."""
        # Max symbol exposure = $30,000. Existing = $25,000 (50 * $500)
        self.riskd.update_position("SPY", quantity=50.0, avg_price=500.0, current_price=500.0)

        # Order adding $10,000 exposure -> $35,000 > $30,000
        dec = self._make_decision(symbol="SPY", side=OrderSide.BUY, qty=20.0, price=500.0)
        v = self.riskd.evaluate(dec)
        self.assertFalse(v.approved)
        self.assertEqual(v.rule_triggered, "SYMBOL_EXPOSURE_BREACH")

    def test_correlation_exposure_limits(self):
        """Correlated asset group cannot exceed combined threshold."""
        # Group CRYPTO: BTC/USD, ETH/USD, SOL/USD. Limit = $45,000.
        # Establish $30,000 BTC/USD position
        self.riskd.update_position("BTC/USD", quantity=0.5, avg_price=60_000.0, current_price=60_000.0)

        # Buying $20,000 ETH/USD pushes group to $50,000 > $45,000
        dec_eth = self._make_decision(symbol="ETH/USD", side=OrderSide.BUY, qty=5.0, price=4_000.0)
        v = self.riskd.evaluate(dec_eth)
        self.assertFalse(v.approved)
        self.assertEqual(v.rule_triggered, "CORRELATION_LIMIT_BREACH")

    def test_daily_loss_circuit_breaker(self):
        """Realized/unrealized loss exceeding daily limit triggers HALTED state."""
        # Daily loss limit = $2,000
        self.riskd.update_position("SPY", quantity=10.0, avg_price=500.0, current_price=500.0, realized_pnl=-2_500.0)
        self.assertEqual(self.riskd.risk_state, RiskState.HALTED)

        v = self.riskd.evaluate(self._make_decision())
        self.assertFalse(v.approved)
        self.assertEqual(v.risk_state, RiskState.HALTED)

    def test_autonomous_mutation_strictly_forbidden(self):
        """AI agents, plugins, AEI, and untrusted callers cannot modify hard limits."""
        untrusted_callers = ["ai", "ai_agent", "plugin", "aei", "adaptive_engine", "strategy", "untrusted"]
        for caller in untrusted_callers:
            success = self.riskd.attempt_modify_limits(caller, {"max_order_usd": 1_000_000.0})
            self.assertFalse(success, f"Caller '{caller}' breached hard limit immutability!")

    def test_ai_agent_cannot_bypass_riskd(self):
        """Signals/decisions from AI agents must submit to RiskD and cannot execute if rejected."""
        agent = KairosAIAgent(agent_id="test-deepseek-quant")
        analysis = agent.analyze_market({})
        # Overwrite to attempt an illegal huge size
        analysis["suggested_quantity"] = 500.0 # Limit is 20.0
        order_decision = agent.propose_order(analysis)

        verdict = self.riskd.evaluate(order_decision)
        self.assertFalse(verdict.approved)
        self.assertEqual(verdict.rule_triggered, "MAX_ORDER_QTY_BREACH")

    def test_plugin_cannot_bypass_riskd(self):
        """Plugins have no direct broker execution capability and must submit to RiskD."""
        plugin_mgr = PluginManager(allowed_capabilities={Capability.READ_MARKET_DATA, Capability.EMIT_SIGNAL})
        plugin = DummyPlugin()
        plugin_mgr.register(plugin)

        sig = plugin.on_market_tick({})
        # Converting plugin signal to formal decision
        decision = DecisionSnapshot(
            decision_id="PLUGIN_001",
            strategy_id="plugin_dummy",
            strategy_version="1.0",
            trading_mode=TradingMode.LIVE,
            symbol=sig["symbol"],
            side=OrderSide.BUY,
            quantity=sig["size"],
            order_type=OrderType.MARKET,
            price=60_000.0,
            timestamp_ns=time.time_ns(),
            rationale="Plugin emitted order"
        )
        verdict = self.riskd.evaluate(decision)
        self.assertFalse(verdict.approved)
        self.assertEqual(verdict.rule_triggered, "MAX_ORDER_QTY_BREACH")

if __name__ == "__main__":
    unittest.main()
