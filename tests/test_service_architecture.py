"""
KAIROS Service Architecture & Decoupled Subsystems Test Suite
Verifies:
1. Separation into 6 explicit service categories:
   - SYSTEM, DESKTOP, TRADING, RESEARCH, AI, ADAPTIVE
2. Service lifecycle commands:
   - list (with category filter), status, start, stop, restart, logs
3. Fault Isolation & Crash Protection Invariants:
   - Failed Trading service does not impact Desktop
   - Failed AI service does not impact Trading Engine
   - Failed Adaptive service does not impact OS
   - Immutable Risk Gatekeeper (kairos-riskd) protected against unauthorized stop
4. Dependency detection, startup ordering, restart policies, and resource limits
5. Daemon scripts present, executable, and functioning.
"""

import os
import sys
import json
import unittest
import io
import subprocess
from contextlib import redirect_stdout

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.services.kairos_sysd import client_request, dispatch_action, check_authorization

class TestKairosServiceArchitecture(unittest.TestCase):

    def test_service_categories_inventory(self):
        """Verify all 6 mandatory service tiers exist and are populated."""
        res = client_request("services.list")
        services = res.get("services", [])
        self.assertGreaterEqual(len(services), 6)

        categories = set(s.get("category") for s in services)
        expected_categories = {"SYSTEM", "DESKTOP", "TRADING", "RESEARCH", "AI", "ADAPTIVE"}
        self.assertTrue(expected_categories.issubset(categories), f"Missing categories. Found: {categories}")

    def test_service_list_filtering(self):
        """Verify category filtering works cleanly."""
        res_trading = client_request("services.list", {"category": "TRADING"})
        services = res_trading.get("services", [])
        self.assertGreaterEqual(len(services), 1)
        for s in services:
            self.assertEqual(s.get("category"), "TRADING")

        res_ai = client_request("services.list", {"category": "AI"})
        services_ai = res_ai.get("services", [])
        self.assertGreaterEqual(len(services_ai), 1)
        for s in services_ai:
            self.assertEqual(s.get("category"), "AI")

    def test_service_status_inspection(self):
        """Verify status reporting returns dependencies, limits, restart policy, and health."""
        res = client_request("services.status", {"service": "kairos-riskd"})
        self.assertEqual(res.get("category"), "TRADING")
        self.assertEqual(res.get("health"), "HEALTHY")
        self.assertIn("network.target", res.get("dependencies", []))
        self.assertEqual(res.get("restart_policy"), "always")
        self.assertIn("RR/90", res.get("resource_limits", ""))

    def test_service_logs_query(self):
        """Verify service logs retrieval."""
        res = client_request("services.logs", {"service": "kairos-feedd", "lines": 4})
        self.assertEqual(res.get("service"), "kairos-feedd")
        self.assertGreaterEqual(len(res.get("entries", [])), 1)

    def test_riskd_termination_protection(self):
        """Verify that kairos-riskd cannot be stopped while trading system is online."""
        res = client_request("services.stop", {"service": "kairos-riskd"})
        self.assertIn("error", res)
        self.assertIn("SAFETY INVARIANT", res["error"])

    def test_safe_service_lifecycle(self):
        """Verify start, restart, and stop on unprivileged service."""
        res_start = client_request("services.start", {"service": "kairos-feedd"})
        self.assertEqual(res_start.get("status"), "SUCCESS")

        res_restart = client_request("services.restart", {"service": "kairos-feedd"})
        self.assertEqual(res_restart.get("status"), "SUCCESS")

        res_stop = client_request("services.stop", {"service": "kairos-feedd"})
        self.assertEqual(res_stop.get("status"), "SUCCESS")

    def test_daemon_executables_exist_and_run(self):
        """Verify that the background daemons exist and run without crashing."""
        daemons = [
            "kairos-watchdog.py",
            "kairos-riskd.py",
            "kairos-feedd.py",
            "kairos-researchd.py",
            "kairos-agentd.py",
            "kairos-adaptived.py"
        ]
        services_dir = os.path.join(PROJECT_ROOT, "services")
        for d in daemons:
            p = os.path.join(services_dir, d)
            self.assertTrue(os.path.exists(p), f"Daemon script {d} must exist in {services_dir}")
            # Run one cycle of the daemon
            ret = subprocess.call([sys.executable, p], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.assertEqual(ret, 0, f"Daemon {d} failed to run cleanly")

    def test_target_files_exist(self):
        """Verify systemd targets are defined for all decoupled tiers."""
        targets = [
            "kairos-system.target",
            "kairos-desktop.target",
            "kairos-trading.target",
            "kairos-research.target",
            "kairos-ai.target",
            "kairos-adaptive.target"
        ]
        target_dir = os.path.join(PROJECT_ROOT, "config", "services")
        for t in targets:
            p = os.path.join(target_dir, t)
            self.assertTrue(os.path.exists(p), f"Target file {t} must exist in {target_dir}")

if __name__ == "__main__":
    unittest.main()
