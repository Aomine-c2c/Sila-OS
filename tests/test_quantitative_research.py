"""
KAIROS Quantitative Research Environment Unit Tests
Validates isolation, experiment manifest recording, metrics calculation,
validation methods, and strict live broker credential prohibition.
"""

import unittest
import os
import shutil
import tempfile
from research.environment import (
    ResearchEnvironment,
    ExecutionTier,
    ValidationMethod,
    ExperimentConfig,
    DatasetMetadata,
    FeatureEngine,
    BacktestSimulator
)


class TestQuantitativeResearchEnvironment(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.env = ResearchEnvironment(storage_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_datasets_available(self):
        datasets = self.env.list_datasets()
        self.assertGreaterEqual(len(datasets), 3)
        ds_ids = [d["dataset_id"] for d in datasets]
        self.assertIn("ds_spy_5m_2024", ds_ids)
        self.assertIn("ds_btc_1m_2024", ds_ids)
        self.assertIn("ds_nvda_1m_2024", ds_ids)

    def test_feature_engineering_pipeline(self):
        # Generate sample price series
        bars = [
            {
                "timestamp": 1704067200 + i * 300,
                "open": 100.0 + i * 0.5,
                "high": 101.0 + i * 0.5,
                "low": 99.5 + i * 0.5,
                "close": 100.5 + i * 0.5,
                "volume": 1000.0
            }
            for i in range(50)
        ]
        enriched = FeatureEngine.compute_features(
            bars=bars,
            feature_list=["returns", "sma_fast", "sma_slow", "volatility_20", "orderbook_imbalance"]
        )
        self.assertEqual(len(enriched), 50)
        sample = enriched[-1]
        self.assertIn("returns", sample)
        self.assertIn("sma_fast", sample)
        self.assertIn("sma_slow", sample)
        self.assertIn("volatility_20", sample)
        self.assertIn("orderbook_imbalance", sample)
        self.assertGreater(sample["sma_slow"], 0.0)

    def test_backtest_simulation_deterministic(self):
        bars = [
            {
                "timestamp": 1704067200 + i * 300,
                "open": 100.0 + (i % 5),
                "high": 102.0 + (i % 5),
                "low": 98.0 + (i % 5),
                "close": 100.5 + (i % 5),
                "volume": 1000.0
            }
            for i in range(60)
        ]
        config = ExperimentConfig(
            experiment_id="exp_test_sim",
            strategy_id="EMA_Cross",
            strategy_version="1.4.0",
            dataset_id="ds_spy_5m_2024",
            start_date="2024-01-01",
            end_date="2024-06-30",
            parameters={"fast_period": 9, "slow_period": 21},
            features=["returns", "sma_fast", "sma_slow"],
            model_version="rule_v1",
            random_seed=42,
            transaction_costs_bps=1.5,
            slippage_bps=1.0,
            validation_method=ValidationMethod.BACKTEST,
            source_commit="e8f49a1c"
        )
        metrics = BacktestSimulator.run_simulation(bars, config)
        self.assertIsInstance(metrics.cagr_pct, float)
        self.assertIsInstance(metrics.sharpe_ratio, float)
        self.assertIsInstance(metrics.max_drawdown_pct, float)
        self.assertGreaterEqual(metrics.total_trades, 0)
        self.assertGreaterEqual(metrics.win_rate_pct, 0.0)
        self.assertLessEqual(metrics.win_rate_pct, 100.0)

    def test_all_11_manifest_fields_recorded(self):
        """
        Verify every experiment records:
        1. dataset
        2. time period
        3. strategy version
        4. parameters
        5. features
        6. model version
        7. random seed
        8. transaction costs
        9. slippage assumptions
        10. results (metrics)
        11. source commit/version
        """
        config = ExperimentConfig(
            experiment_id="exp_manifest_001",
            strategy_id="StatArb_MeanRevert",
            strategy_version="2.1.0",
            dataset_id="ds_btc_1m_2024",
            start_date="2024-01-01",
            end_date="2024-03-31",
            parameters={"zscore_entry": 2.0, "zscore_exit": 0.5},
            features=["returns", "volatility_20", "orderbook_imbalance"],
            model_version="xgb_regressor_v2",
            random_seed=1337,
            transaction_costs_bps=2.0,
            slippage_bps=1.5,
            validation_method=ValidationMethod.WALK_FORWARD,
            source_commit="7b91df02"
        )
        record = self.env.run_experiment(config, synthetic_bars_count=100, tier=ExecutionTier.RESEARCH)

        # 1. Dataset
        self.assertEqual(record.config.dataset_id, "ds_btc_1m_2024")
        # 2. Time period
        self.assertEqual(record.config.start_date, "2024-01-01")
        self.assertEqual(record.config.end_date, "2024-03-31")
        # 3. Strategy version
        self.assertEqual(record.config.strategy_version, "2.1.0")
        # 4. Parameters
        self.assertEqual(record.config.parameters["zscore_entry"], 2.0)
        # 5. Features
        self.assertIn("orderbook_imbalance", record.config.features)
        # 6. Model version
        self.assertEqual(record.config.model_version, "xgb_regressor_v2")
        # 7. Random seed
        self.assertEqual(record.config.random_seed, 1337)
        # 8. Transaction costs
        self.assertEqual(record.config.transaction_costs_bps, 2.0)
        # 9. Slippage assumptions
        self.assertEqual(record.config.slippage_bps, 1.5)
        # 10. Results
        self.assertIsNotNone(record.metrics)
        self.assertIsInstance(record.metrics.sharpe_ratio, float)
        # 11. Source commit/version
        self.assertEqual(record.config.source_commit, "7b91df02")

        # Provenance hash verification
        self.assertTrue(record.provenance_hash.startswith("sha256:"))

        # Verification of disk persistence
        experiments = self.env.list_experiments()
        self.assertEqual(len(experiments), 1)
        self.assertEqual(experiments[0]["manifest_id"], record.manifest_id)

    def test_validation_methods_supported(self):
        """
        Verify all validation modes:
        backtest, walk-forward, out-of-sample, paper trading, shadow deployment
        """
        for method in [
            ValidationMethod.BACKTEST,
            ValidationMethod.WALK_FORWARD,
            ValidationMethod.OUT_OF_SAMPLE,
            ValidationMethod.PAPER_TRADING,
            ValidationMethod.SHADOW_DEPLOYMENT
        ]:
            tier = ExecutionTier.RESEARCH
            if method == ValidationMethod.PAPER_TRADING:
                tier = ExecutionTier.PAPER
            elif method == ValidationMethod.SHADOW_DEPLOYMENT:
                tier = ExecutionTier.SHADOW

            config = ExperimentConfig(
                experiment_id=f"exp_val_{method.value.lower()}",
                strategy_id=f"Test_{method.value}",
                strategy_version="1.0.0",
                dataset_id="ds_spy_5m_2024",
                start_date="2024-01-01",
                end_date="2024-06-30",
                parameters={"lookback": 20},
                features=["returns"],
                model_version="v1",
                random_seed=42,
                transaction_costs_bps=1.0,
                slippage_bps=1.0,
                validation_method=method,
                source_commit="abc12345"
            )
            record = self.env.run_experiment(config, synthetic_bars_count=80, tier=tier)
            self.assertEqual(record.config.validation_method, method)
            self.assertEqual(record.execution_tier, tier)

    def test_hard_security_invariant_broker_credential_isolation(self):
        """
        Hard Security Invariant:
        Research environments must NEVER automatically receive live broker credentials.
        """
        policy = self.env.get_tier_security_policy(ExecutionTier.RESEARCH)
        self.assertFalse(policy["broker_credentials_provided"])
        self.assertFalse(policy["allow_direct_execution"])
        self.assertEqual(policy["network_access"], "OFFLINE_LOCAL")

        # Run experiment in RESEARCH tier
        config = ExperimentConfig(
            experiment_id="exp_sec_test",
            strategy_id="TrendFollowing",
            strategy_version="1.0.0",
            dataset_id="ds_nvda_1m_2024",
            start_date="2024-01-01",
            end_date="2024-06-30",
            parameters={"period": 14},
            features=["returns"],
            model_version="linear_v1",
            random_seed=99,
            transaction_costs_bps=1.0,
            slippage_bps=0.5,
            validation_method=ValidationMethod.BACKTEST,
            source_commit="commit_safe"
        )
        record = self.env.run_experiment(config, synthetic_bars_count=80, tier=ExecutionTier.RESEARCH)
        # Must be strictly False!
        self.assertFalse(record.broker_credentials_provided)

    def test_tier_separation_policies(self):
        paper_policy = self.env.get_tier_security_policy(ExecutionTier.PAPER)
        self.assertFalse(paper_policy["broker_credentials_provided"])
        self.assertFalse(paper_policy["allow_direct_execution"])
        self.assertEqual(paper_policy["network_access"], "STREAMING_FEED_ONLY")

        shadow_policy = self.env.get_tier_security_policy(ExecutionTier.SHADOW)
        self.assertFalse(shadow_policy["broker_credentials_provided"])
        self.assertFalse(shadow_policy["allow_direct_execution"])

        live_policy = self.env.get_tier_security_policy(ExecutionTier.LIVE)
        self.assertTrue(live_policy["broker_credentials_provided"])
        self.assertTrue(live_policy["allow_direct_execution"])
        self.assertEqual(live_policy["network_access"], "FILTERED_DMA_TLS")


if __name__ == "__main__":
    unittest.main()
