"""
Unit tests for the KAIROS Trading Subsystem Architecture.
Verifies:
1. MarketD normalization (symbol, bid, ask, mid, spread, volume, timestamp, provider, sequence, quality, latency)
2. BrokerD normalized execution interface and order execution
3. StrategyD registration, versioning, parameters, toggling, and modes (SIMULATION, PAPER, LIVE)
4. RiskD non-bypassable pre-trade evaluation and limits
5. ExecutionD non-bypassable pipeline (Market Data -> Strategy -> Decision Snapshot -> RiskD -> ExecutionD -> BrokerD)
6. JournalD audit logging of decisions and execution results
7. Subsystem isolation (operates independently of desktop shell / compositor)
"""

import unittest
import os
import tempfile
import shutil
import time

from trading.subsystem import (
    MarketD,
    BrokerD,
    RiskD,
    ExecutionD,
    StrategyD,
    JournalD,
    TradingMode,
    OrderSide,
    OrderType,
    NormalizedMarketTick,
    DecisionSnapshot,
    RiskEvaluation,
    BrokerExecutionReport,
    StrategyRegistration
)

class TestTradingSubsystem(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.journal_path = os.path.join(self.test_dir, "test_trading_journal.log")
        
        self.marketd = MarketD()
        self.brokerd = BrokerD(default_broker="InteractiveBrokers_FIX")
        self.riskd = RiskD(max_position_size=50.0, max_drawdown_pct=0.03)
        self.journald = JournalD(log_path=self.journal_path)
        self.executiond = ExecutionD(riskd=self.riskd, brokerd=self.brokerd, journald=self.journald)
        self.strategyd = StrategyD(executiond=self.executiond, journald=self.journald)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_marketd_normalization(self):
        """Verify MarketD produces normalized ticks with all 11 required fields."""
        t0 = time.time()
        tick = self.marketd.ingest_raw(
            raw_symbol="SPY",
            raw_bid=504.10,
            raw_ask=504.20,
            raw_vol=1500.0,
            provider="CME_DMA"
        )
        
        self.assertIsInstance(tick, NormalizedMarketTick)
        self.assertEqual(tick.symbol, "SPY")
        self.assertEqual(tick.bid, 504.10)
        self.assertEqual(tick.ask, 504.20)
        self.assertAlmostEqual(tick.mid, 504.15, places=4)
        self.assertAlmostEqual(tick.spread, 0.10, places=4)
        self.assertEqual(tick.volume, 1500.0)
        self.assertGreaterEqual(tick.timestamp, t0)
        self.assertEqual(tick.provider, "CME_DMA")
        self.assertEqual(tick.sequence, 1)
        self.assertEqual(tick.quality, "PRISTINE")
        self.assertGreater(tick.latency, 0.0)

        # Confirm get_latest
        latest = self.marketd.get_latest("SPY")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.symbol, "SPY")

    def test_brokerd_interface(self):
        """Verify BrokerD exposes a normalized interface and processes orders."""
        decision = DecisionSnapshot(
            decision_id="DEC-001",
            strategy_id="strat-alpha",
            strategy_version="1.0.0",
            trading_mode=TradingMode.PAPER,
            symbol="BTC/USD",
            side=OrderSide.BUY,
            quantity=2.0,
            order_type=OrderType.MARKET,
            price=68000.0,
            timestamp_ns=time.time_ns(),
            rationale="Test market buy"
        )
        report = self.brokerd.send_order(decision, approved_qty=2.0)
        self.assertIsInstance(report, BrokerExecutionReport)
        self.assertEqual(report.status, "FILLED")
        self.assertEqual(report.filled_quantity, 2.0)
        self.assertEqual(report.fill_price, 68000.0)
        self.assertEqual(report.symbol, "BTC/USD")
        self.assertEqual(report.side, "BUY")
        self.assertTrue(report.order_id.startswith("ORD_BTC/USD_"))
        self.assertTrue(report.execution_id.startswith("EXEC_"))

    def test_strategyd_lifecycle(self):
        """Verify StrategyD registration, versioning, parameters, toggling, and modes."""
        # 1. Register
        reg = self.strategyd.register(
            strategy_id="strat_stat_arb_nvda",
            version="2.1.0",
            name="Semiconductor Stat-Arb",
            parameters={"threshold": 2.0, "max_inventory": 10},
            mode=TradingMode.SIMULATION
        )
        self.assertEqual(reg.strategy_id, "strat_stat_arb_nvda")
        self.assertEqual(reg.version, "2.1.0")
        self.assertEqual(reg.mode, TradingMode.SIMULATION)
        self.assertTrue(reg.enabled)

        # 2. Toggle enable/disable
        self.strategyd.set_enabled("strat_stat_arb_nvda", False)
        self.assertFalse(self.strategyd.strategies["strat_stat_arb_nvda"].enabled)

        self.strategyd.set_enabled("strat_stat_arb_nvda", True)
        self.assertTrue(self.strategyd.strategies["strat_stat_arb_nvda"].enabled)

        # 3. Mode switching: SIMULATION -> PAPER -> LIVE
        self.strategyd.set_mode("strat_stat_arb_nvda", TradingMode.PAPER)
        self.assertEqual(self.strategyd.strategies["strat_stat_arb_nvda"].mode, TradingMode.PAPER)

        self.strategyd.set_mode("strat_stat_arb_nvda", TradingMode.LIVE)
        self.assertEqual(self.strategyd.strategies["strat_stat_arb_nvda"].mode, TradingMode.LIVE)

        # 4. Parameter updating
        self.strategyd.update_parameters("strat_stat_arb_nvda", {"threshold": 2.5, "stop_loss": 0.01})
        self.assertEqual(self.strategyd.strategies["strat_stat_arb_nvda"].parameters["threshold"], 2.5)
        self.assertEqual(self.strategyd.strategies["strat_stat_arb_nvda"].parameters["stop_loss"], 0.01)

    def test_riskd_pre_trade_enforcement(self):
        """Verify RiskD gates order decisions before execution."""
        # Case A: Valid order
        decision_valid = DecisionSnapshot(
            decision_id="DEC-VAL",
            strategy_id="strat-alpha",
            strategy_version="1.0.0",
            trading_mode=TradingMode.LIVE,
            symbol="SPY",
            side=OrderSide.BUY,
            quantity=10.0, # <= max 50.0
            order_type=OrderType.LIMIT,
            price=504.15,
            timestamp_ns=time.time_ns(),
            rationale="Test valid"
        )
        eval_valid = self.riskd.evaluate(decision_valid)
        self.assertTrue(eval_valid.approved)
        self.assertEqual(eval_valid.adjusted_quantity, 10.0)

        # Case B: Exceeding max position size
        decision_oversized = DecisionSnapshot(
            decision_id="DEC-BIG",
            strategy_id="strat-alpha",
            strategy_version="1.0.0",
            trading_mode=TradingMode.LIVE,
            symbol="SPY",
            side=OrderSide.BUY,
            quantity=100.0, # > max 50.0
            order_type=OrderType.LIMIT,
            price=504.15,
            timestamp_ns=time.time_ns(),
            rationale="Test oversized"
        )
        eval_oversized = self.riskd.evaluate(decision_oversized)
        self.assertFalse(eval_oversized.approved)
        self.assertIn("exceeds single position hard limit", eval_oversized.reason)

        # Case C: Drawdown limit breach
        self.riskd.current_drawdown_pct = 0.04 # 4.0% > max 3.0%
        eval_dd = self.riskd.evaluate(decision_valid)
        self.assertFalse(eval_dd.approved)
        self.assertTrue("HALTED" in eval_dd.reason or "drawdown" in eval_dd.reason.lower())

    def test_executiond_pipeline_integrity(self):
        """Verify complete pipeline: Market Data -> Strategy -> Decision Snapshot -> RiskD -> ExecutionD -> BrokerD."""
        def mock_eval_fn(tick: NormalizedMarketTick, params: dict):
            if tick.symbol == "SPY":
                return DecisionSnapshot(
                    decision_id=f"DEC_{int(time.time()*1000)}",
                    strategy_id="strat_test",
                    strategy_version="1.0",
                    trading_mode=TradingMode.LIVE,
                    symbol=tick.symbol,
                    side=OrderSide.BUY,
                    quantity=params.get("qty", 5.0),
                    order_type=OrderType.LIMIT,
                    price=tick.ask,
                    timestamp_ns=time.time_ns(),
                    rationale="Spread capture signal"
                )
            return None

        self.strategyd.register(
            strategy_id="strat_test",
            version="1.0.0",
            name="Spread Capturer",
            parameters={"qty": 5.0},
            mode=TradingMode.LIVE,
            eval_fn=mock_eval_fn
        )

        # Feed market tick
        tick = self.marketd.ingest_raw("SPY", 504.10, 504.20, 1000.0, "CME_DMA")
        
        # Strategy processes tick
        results = self.strategyd.on_tick(tick)
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res["status"], "EXECUTED")
        self.assertEqual(res["execution_report"].status, "FILLED")
        self.assertEqual(res["execution_report"].filled_quantity, 5.0)
        self.assertEqual(res["execution_report"].fill_price, 504.20)

        # Verify JournalD has recorded all stages
        self.assertTrue(os.path.exists(self.journal_path))
        with open(self.journal_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]
        
        import json
        json_events = [json.loads(l)["event_type"] for l in lines]
        self.assertIn("STRATEGY_REGISTERED", json_events)
        self.assertIn("RISK_EVALUATION", json_events)
        self.assertIn("BROKER_EXECUTION", json_events)

    def test_risk_rejection_halts_broker_execution(self):
        """Verify that when RiskD rejects an order, BrokerD is never called."""
        # Register a strategy that creates an order exceeding max_position_size
        def mock_greedy_strat(tick: NormalizedMarketTick, params: dict):
            return DecisionSnapshot(
                decision_id="DEC_GREEDY",
                strategy_id="strat_greedy",
                strategy_version="1.0",
                trading_mode=TradingMode.LIVE,
                symbol="SPY",
                side=OrderSide.BUY,
                quantity=200.0, # Max allowed is 50.0
                order_type=OrderType.LIMIT,
                price=tick.ask,
                timestamp_ns=time.time_ns(),
                rationale="Greedy massive size"
            )

        self.strategyd.register(
            strategy_id="strat_greedy",
            version="1.0.0",
            name="Greedy Scalper",
            parameters={},
            mode=TradingMode.LIVE,
            eval_fn=mock_greedy_strat
        )

        initial_broker_orders = len(self.brokerd.executions)
        tick = self.marketd.ingest_raw("SPY", 504.10, 504.20, 1000.0, "CME_DMA")
        results = self.strategyd.on_tick(tick)
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "REJECTED_BY_RISK")
        self.assertIsNone(results[0]["execution_report"])
        self.assertEqual(len(self.brokerd.executions), initial_broker_orders, "Broker executed rejected order!")

    def test_trading_services_isolated_from_desktop_shell(self):
        """Verify Trading subsystem runs headlessly without compositor or Wayland variables."""
        saved_wayland = os.environ.pop("WAYLAND_DISPLAY", None)
        saved_display = os.environ.pop("DISPLAY", None)
        try:
            m = MarketD()
            b = BrokerD()
            r = RiskD()
            j = JournalD(log_path=os.path.join(self.test_dir, "isolated_journal.log"))
            e = ExecutionD(r, b, j)
            s = StrategyD(e, j)

            tick = m.ingest_raw("ETH/USD", 3500.0, 3501.0, 50.0)
            self.assertEqual(tick.symbol, "ETH/USD")
            self.assertEqual(tick.mid, 3500.5)
        finally:
            if saved_wayland:
                os.environ["WAYLAND_DISPLAY"] = saved_wayland
            if saved_display:
                os.environ["DISPLAY"] = saved_display

if __name__ == "__main__":
    unittest.main()
