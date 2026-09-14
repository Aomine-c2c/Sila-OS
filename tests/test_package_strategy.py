"""
KAIROS Software Layer & Package Strategy Test Suite
Verifies:
1. Separation into 6 explicit package categories:
   - CORE, OPTIONAL, TRADING, RESEARCH, DEVELOPMENT, EXPERIMENTAL
2. Package commands:
   - search, install, remove, update, info, list
3. Critical Security Invariants:
   - Never allow an experimental package to replace a critical system component.
   - Core and immutable packages cannot be removed.
   - Category filtering functions accurately across tiers.
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

class TestKairosPackageStrategy(unittest.TestCase):

    def test_package_catalog_completeness(self):
        """Verify packages.json manifest exists and contains all 6 tiers."""
        res = client_request("package.list")
        pkgs = res.get("packages", [])
        self.assertGreaterEqual(len(pkgs), 10)

        categories = set(p.get("category") for p in pkgs)
        expected_categories = {"CORE", "OPTIONAL", "TRADING", "RESEARCH", "DEVELOPMENT", "EXPERIMENTAL"}
        self.assertTrue(expected_categories.issubset(categories), f"Missing categories. Found: {categories}")

    def test_package_category_filtering(self):
        """Verify filtering packages by category tier."""
        res_core = client_request("package.list", {"category": "CORE"})
        for p in res_core.get("packages", []):
            self.assertEqual(p.get("category"), "CORE")

        res_exp = client_request("package.list", {"category": "EXPERIMENTAL"})
        for p in res_exp.get("packages", []):
            self.assertEqual(p.get("category"), "EXPERIMENTAL")

    def test_package_search(self):
        """Verify search query across names and descriptions."""
        res = client_request("package.search", {"query": "risk"})
        results = res.get("results", [])
        self.assertGreaterEqual(len(results), 1)
        names = [p.get("name") for p in results]
        self.assertIn("kairos-risk-engine", names)

    def test_package_info(self):
        """Verify detailed package info retrieval."""
        res = client_request("package.info", {"package": "kairos-risk-engine"})
        p = res.get("package", {})
        self.assertEqual(p.get("name"), "kairos-risk-engine")
        self.assertEqual(p.get("category"), "TRADING")
        self.assertTrue(p.get("immutable"))

    def test_experimental_replacement_blocked(self):
        """CRITICAL INVARIANT: Experimental package must NOT silently or explicitly replace core components."""
        res = client_request("package.install", {
            "package": "experimental-quantum-annealer",
            "replaces": "kairos-base"
        })
        self.assertIn("error", res)
        self.assertIn("CRITICAL SECURITY INVARIANT VIOLATION", res["error"])

    def test_core_package_removal_blocked(self):
        """CRITICAL INVARIANT: Core immutable packages cannot be uninstalled."""
        res = client_request("package.remove", {"package": "kairos-base"})
        self.assertIn("error", res)
        self.assertIn("PROTECTED SYSTEM INVARIANT", res["error"])

    def test_valid_package_install_and_remove(self):
        """Verify installing and removing a non-core optional package."""
        res_inst = client_request("package.install", {"package": "tradingview-desktop"})
        self.assertEqual(res_inst.get("status"), "SUCCESS")

        res_rem = client_request("package.remove", {"package": "tradingview-desktop"})
        self.assertEqual(res_rem.get("status"), "SUCCESS")

    def test_package_update(self):
        """Verify package update action with signature verification."""
        res = client_request("package.update", {"package": "all"})
        self.assertEqual(res.get("status"), "SUCCESS")
        self.assertIn("ed25519", res.get("verification", ""))

if __name__ == "__main__":
    unittest.main()
