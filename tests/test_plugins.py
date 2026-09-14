"""
KAIROS Capability-Based Plugin Platform Unit Tests
Validates categories, manifest schema, cryptographic signature/verification,
lifecycle state machine, and hard security invariants prohibiting unrestricted privileges.
"""

import unittest
import os
import tempfile
import shutil
from plugins.plugin_host import KairosPlugin, PluginManager, Capability
from plugins.manager import (
    PluginCategory,
    SecurityLevel,
    PluginLifecycleState,
    PluginManifest,
    PluginVerifier,
    PluginPlatformManager,
    ABSOLUTE_DENIED_PERMISSIONS
)

class SampleStrategyPlugin(KairosPlugin):
    @property
    def name(self) -> str:
        return "sma_cross_strategy"

    @property
    def required_capabilities(self):
        return {Capability.READ_MARKET_DATA, Capability.EMIT_SIGNAL}

    def on_market_tick(self, tick):
        return {"signal": "BUY", "confidence": 0.85}

class TestPluginHost(unittest.TestCase):
    def test_authorized_plugin_registration(self):
        manager = PluginManager(allowed_capabilities={
            Capability.READ_MARKET_DATA,
            Capability.COMPUTE_FEATURES,
            Capability.EMIT_SIGNAL
        })
        plugin = SampleStrategyPlugin()
        self.assertTrue(manager.register(plugin))
        self.assertIn("sma_cross_strategy", manager.registered_plugins)

    def test_unauthorized_capability_denied(self):
        strict_manager = PluginManager(allowed_capabilities={Capability.READ_MARKET_DATA})
        plugin = SampleStrategyPlugin()
        with self.assertRaises(PermissionError):
            strict_manager.register(plugin)

class TestPluginPlatformPlatform(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.platform = PluginPlatformManager(storage_dir=self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_all_12_plugin_categories_supported(self):
        """Verify all 12 requested plugin categories exist and can be parsed."""
        expected = [
            "Market Data",
            "Broker",
            "Strategy",
            "Indicator",
            "Research",
            "AI",
            "Analytics",
            "News",
            "Sentiment",
            "Charts",
            "Workspace",
            "System Automation"
        ]
        categories = [c.value for c in PluginCategory]
        for exp in expected:
            self.assertIn(exp, categories)
            cat_obj = PluginCategory.from_string(exp)
            self.assertIsInstance(cat_obj, PluginCategory)

    def test_manifest_structure_and_serialization(self):
        """Verify plugin manifest contains all required fields."""
        manifest_data = {
            "id": "kairos.regime-detector",
            "name": "Market Regime Detector",
            "version": "1.0.0",
            "category": "Analytics",
            "type": "capability-module",
            "permissions": ["market.read", "strategy.read", "telemetry.read"],
            "denied": ["order.execute", "risk.modify", "credential.read"],
            "provides": ["regime.classification", "volatility.forecast"],
            "dependencies": {"kairos.core": ">=1.0.0"},
            "security_level": "SANDBOXED_RESTRICTED",
            "description": "Real-time statistical market regime identification",
            "signer": "KAIROS Certified Publisher"
        }
        sig = PluginVerifier.compute_signature(manifest_data)
        manifest_data["signature"] = sig
        manifest = PluginManifest.from_dict(manifest_data)

        self.assertEqual(manifest.id, "kairos.regime-detector")
        self.assertEqual(manifest.name, "Market Regime Detector")
        self.assertEqual(manifest.version, "1.0.0")
        self.assertEqual(manifest.category, PluginCategory.ANALYTICS)
        self.assertEqual(manifest.type, "capability-module")
        self.assertIn("market.read", manifest.permissions)
        self.assertIn("order.execute", manifest.denied)
        self.assertIn("regime.classification", manifest.provides)
        self.assertIn("kairos.core", manifest.dependencies)
        self.assertEqual(manifest.security_level, SecurityLevel.SANDBOXED_RESTRICTED)
        self.assertTrue(manifest.signature.startswith("sha256:"))

    def test_cryptographic_signature_and_tamper_detection(self):
        """Verify signature validation succeeds on authentic manifests and rejects tampered ones."""
        p_def = {
            "id": "kairos.test-plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "category": "Strategy",
            "permissions": ["market.read"],
            "denied": ["order.execute", "risk.modify", "credential.read"],
            "provides": ["test.signal"],
            "security_level": "CAPABILITY_GATED"
        }
        sig = PluginVerifier.compute_signature(p_def)
        p_def["signature"] = sig
        manifest = PluginManifest.from_dict(p_def)

        # Authentic manifest verification
        is_valid, msg = PluginVerifier.verify_manifest(manifest)
        self.assertTrue(is_valid)
        self.assertEqual(msg, "VERIFIED_AUTHENTIC")

        # Tampered manifest (attacker stealthily added unauthorized permission)
        manifest.permissions.append("network.raw")
        is_valid, msg = PluginVerifier.verify_manifest(manifest)
        self.assertFalse(is_valid)
        self.assertIn("TAMPER_DETECTED", msg)

    def test_hard_security_invariants_rejected(self):
        """
        Hard Invariants:
        Plugins must NEVER automatically receive unrestricted privileges.
        Plugins can NEVER acquire order.execute, risk.modify, or credential.read.
        """
        for forbidden in ["order.execute", "risk.modify", "credential.read", "vault.access"]:
            malicious_def = {
                "id": "kairos.malicious-exploit",
                "name": "Trojan Plugin",
                "version": "1.0.0",
                "category": "Analytics",
                "permissions": [forbidden],
                "denied": ["order.execute", "risk.modify", "credential.read"],
                "provides": ["exploit"],
                "security_level": "SANDBOXED_RESTRICTED"
            }
            sig = PluginVerifier.compute_signature(malicious_def)
            malicious_def["signature"] = sig
            manifest = PluginManifest.from_dict(malicious_def)

            is_valid, msg = PluginVerifier.verify_manifest(manifest)
            self.assertFalse(is_valid)
            self.assertIn("SECURITY VIOLATION", msg)

    def test_missing_denied_declarations_rejected(self):
        """Manifests failing to explicitly declare critical denied privileges must be rejected."""
        def_missing_denied = {
            "id": "kairos.incomplete",
            "name": "Incomplete Plugin",
            "version": "1.0.0",
            "category": "Indicator",
            "permissions": ["market.read"],
            "denied": [], # Missing required order.execute / risk.modify / credential.read
            "provides": ["calc"],
            "security_level": "SANDBOXED_RESTRICTED"
        }
        sig = PluginVerifier.compute_signature(def_missing_denied)
        def_missing_denied["signature"] = sig
        manifest = PluginManifest.from_dict(def_missing_denied)

        is_valid, msg = PluginVerifier.verify_manifest(manifest)
        self.assertFalse(is_valid)
        self.assertIn("must explicitly deny", msg)

    def test_plugin_lifecycle_state_machine(self):
        """Test full plugin lifecycle: search -> install -> verify -> enable -> disable -> remove."""
        # 1. Search catalog
        search_res = self.platform.search_plugins("sentiment")
        self.assertGreaterEqual(len(search_res), 1)
        plugin_id = search_res[0]["id"]
        self.assertEqual(plugin_id, "kairos.news-sentiment-nlp")

        # 2. Install plugin
        inst_res = self.platform.install_plugin(plugin_id, auto_enable=True)
        self.assertEqual(inst_res["status"], "SUCCESS")
        self.assertEqual(inst_res["state"], "ENABLED")

        # Verify listed in installed plugins
        installed = self.platform.list_plugins()
        ids = [p["id"] for p in installed]
        self.assertIn(plugin_id, ids)

        # 3. Get info
        info = self.platform.get_plugin_info(plugin_id)
        self.assertIsNotNone(info)
        self.assertEqual(info["state"], "ENABLED")
        self.assertTrue(info["security_audit"]["verified"])
        self.assertTrue(info["security_audit"]["unrestricted_privileges_prohibited"])

        # 4. Disable plugin
        dis_res = self.platform.disable_plugin(plugin_id)
        self.assertEqual(dis_res["status"], "SUCCESS")
        self.assertEqual(dis_res["state"], "DISABLED")

        # Verify disabled state
        info_disabled = self.platform.get_plugin_info(plugin_id)
        self.assertEqual(info_disabled["state"], "DISABLED")

        # 5. Enable plugin
        en_res = self.platform.enable_plugin(plugin_id)
        self.assertEqual(en_res["status"], "SUCCESS")
        self.assertEqual(en_res["state"], "ENABLED")

        # 6. Remove plugin
        rm_res = self.platform.remove_plugin(plugin_id)
        self.assertEqual(rm_res["status"], "SUCCESS")

        # Verify removed
        installed_after = self.platform.list_plugins()
        ids_after = [p["id"] for p in installed_after]
        self.assertNotIn(plugin_id, ids_after)


if __name__ == "__main__":
    unittest.main()
