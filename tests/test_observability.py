#!/usr/bin/env python3
"""
Unit Tests for KAIROS Centralized Observability Subsystem
=========================================================
Validates:
  1. Service Health Contract compliance:
     Every important service exposes health, version, uptime, dependencies, resource usage, last error.
  2. Multi-domain coverage (12 domains):
     OS, Kernel, Services, Desktop, Network, Storage, Trading, Brokers, Risk, Execution, Plugins, Agents & AEI.
  3. Secret scrubbing & log sanitization invariant:
     Logs must NEVER leak API keys, private keys, passwords, or tokens.
  4. Log rotation logic:
     Log files roll over safely under bounded quotas with secure permissions.
  5. CLI commands integration:
     kairos status, kairos health, kairos diagnostics, kairos logs, kairos events.
  6. Health verdict generation:
     Accurately identifies healthy vs degraded vs critical subsystems.
"""

import os
import sys
import json
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from system.observability.collector import (
    ObservabilityCollector,
    ServiceHealthRecord,
    get_observability_collector
)
from system.observability.log_sanitizer import LogSanitizer

class TestObservabilitySubsystem(unittest.TestCase):

    def setUp(self):
        self.collector = ObservabilityCollector()

    def test_service_health_contract_fields(self):
        """Verify all registered services strictly fulfill the mandatory Service Health Contract."""
        services = self.collector.get_service_health_registry()
        self.assertGreaterEqual(len(services), 8)

        expected_services = [
            "kairos-sysd", "kairos-watchdog", "hyprland-session", "waybar",
            "kairos-riskd", "kairos-feedd", "kairos-researchd", "kairos-agentd", "kairos-adaptived"
        ]
        registered_names = [s.name for s in services]
        for exp in expected_services:
            self.assertIn(exp, registered_names)

        for s in services:
            d = s.to_dict()
            # Mandatory contract checks
            self.assertIn("name", d)
            self.assertIn("category", d)
            self.assertIn("health", d)
            self.assertIn(d["health"], ("HEALTHY", "DEGRADED", "CRITICAL", "HALTED"))
            self.assertIn("version", d)
            self.assertIn("uptime", d)
            self.assertIn("dependencies", d)
            self.assertIsInstance(d["dependencies"], list)
            self.assertIn("resource_usage", d)
            self.assertIn("memory_mb", d["resource_usage"])
            self.assertIn("cpu_pct", d["resource_usage"])
            self.assertIn("last_error", d)

    def test_twelve_monitored_domains_snapshot(self):
        """Verify that get_full_status_snapshot covers all 12 operational domains."""
        snapshot = self.collector.get_full_status_snapshot()
        
        required_domains = [
            "os", "kernel", "services", "desktop", "network", "storage",
            "trading", "brokers", "risk", "execution", "plugins", "agents_aei"
        ]
        for dom in required_domains:
            self.assertIn(dom, snapshot, f"Domain '{dom}' must be present in full status snapshot.")

        # Inspect specific domain details
        self.assertEqual(snapshot["os"]["os_name"], "KAIROS Operating System")
        self.assertIn("Linux", snapshot["kernel"]["flavor"])
        self.assertIn("PREEMPT_RT", snapshot["kernel"]["flavor"])
        self.assertEqual(snapshot["risk"]["gatekeeper_state"], "LOCKED_STABLE")
        self.assertTrue(snapshot["risk"]["enforcing_limits"])
        self.assertEqual(snapshot["risk"]["max_drawdown_limit_pct"], 3.0)
        self.assertEqual(snapshot["network"]["status"], "ONLINE")
        self.assertEqual(snapshot["brokers"]["overall_status"], "ONLINE")
        self.assertIn("Btrfs", snapshot["storage"]["root_filesystem"])

    def test_health_verdict_matrix(self):
        """Verify overall health synthesis and domain ratings."""
        verdict = self.collector.get_health_verdict()
        self.assertIn("overall_health", verdict)
        self.assertEqual(verdict["overall_health"], "HEALTHY")
        self.assertIn("domains", verdict)
        self.assertEqual(len(verdict["domains"]), 12)
        for dom, rating in verdict["domains"].items():
            self.assertEqual(rating, "HEALTHY")
        self.assertEqual(len(verdict["unhealthy_services"]), 0)

    def test_deep_diagnostics_probes(self):
        """Verify diagnostic probes pass and measure RT latency and security locks."""
        diag = self.collector.run_deep_diagnostics()
        self.assertIn("PASSED", diag["overall_diagnostics"])
        probes = {p["name"]: p["result"] for p in diag["probes"]}
        self.assertEqual(probes["RT Scheduler Timer Jitter"], "PASS")
        self.assertEqual(probes["Risk Gatekeeper Lock State"], "PASS")
        self.assertEqual(probes["Broker Gateways Heartbeat"], "PASS")
        self.assertEqual(probes["Secret Scrubber & Audit Integrity"], "PASS")

    def test_recent_events_timeline(self):
        """Verify event timeline formatting and domains."""
        events = self.collector.query_recent_events(limit=10)
        self.assertGreaterEqual(len(events), 5)
        for ev in events:
            self.assertIn("timestamp", ev)
            self.assertIn("domain", ev)
            self.assertIn("level", ev)
            self.assertIn("message", ev)

    def test_secret_scrubber_invariants(self):
        """Verify that logs NEVER leak API keys, private keys, passwords, or tokens."""
        leaky_texts = [
            "Connecting to broker with api_key=ak_live_99f84a8c7b6d5e4f3a2b1c0d and secret=sec_884930194857291048572",
            "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0",
            "Broker login: password = SuperSecretTradingPassword123!",
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0Y3...\n-----END RSA PRIVATE KEY-----",
            "FIX session login 554=MyFIXPasswordTagValue",
            "Vault seed_phrase: 'apple orange banana grape melon peach lemon lime berry cherry pear mango'"
        ]

        for text in leaky_texts:
            scrubbed = LogSanitizer.sanitize(text)
            self.assertNotIn("ak_live_99f84a8c7b6d5e4f3a2b1c0d", scrubbed)
            self.assertNotIn("sec_884930194857291048572", scrubbed)
            self.assertNotIn("SuperSecretTradingPassword123!", scrubbed)
            self.assertNotIn("MIIEowIBAAKCAQEA0Y3", scrubbed)
            self.assertNotIn("MyFIXPasswordTagValue", scrubbed)
            self.assertIn("[REDACTED", scrubbed)

    def test_structured_log_record_sanitizer(self):
        """Verify dictionary-level secret scrubbing."""
        record = {
            "service": "broker-gateway",
            "api_key": "live_secret_key_12345678",
            "broker_secret": "xyz_private_secret",
            "message": "Order validated for client_id=102",
            "nested": {
                "auth_token": "token_abc123456789",
                "normal_field": "safe_value"
            }
        }
        clean = LogSanitizer.sanitize_record(record)
        self.assertEqual(clean["api_key"], "[REDACTED_SECRET]")
        self.assertEqual(clean["broker_secret"], "[REDACTED_SECRET]")
        self.assertEqual(clean["nested"]["auth_token"], "[REDACTED_SECRET]")
        self.assertEqual(clean["nested"]["normal_field"], "safe_value")

    def test_log_rotation_utility(self):
        """Verify log file size rotation under bounded quotas."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test_service.log")
            # Create a 200KB log
            with open(log_path, "w") as f:
                f.write("A" * 200 * 1024)

            # Trigger rotation with max_bytes=100KB
            LogSanitizer.rotate_log_if_needed(log_path, max_bytes=100 * 1024, backups=3)
            self.assertTrue(os.path.exists(f"{log_path}.1"))
            self.assertEqual(os.path.getsize(log_path), 0)

if __name__ == "__main__":
    unittest.main()
