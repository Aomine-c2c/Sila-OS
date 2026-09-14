"""
KAIROS Application Isolation & Security Sandbox Test Suite
Verifies:
1. Confinement profiles across all 5 tiers:
   - TRUSTED_SYSTEM, NORMAL_APP, UNTRUSTED_APP, PLUGIN, AI_TOOL
2. Five Core Invariants:
   - Plugins cannot access broker credentials / private vault keys
   - Plugins cannot access protected filesystem paths (/etc/kairos/vault, /etc/shadow)
   - AI tools cannot modify Risk Gatekeeper configuration
   - Plugins cannot access raw network sockets (Total network isolation)
   - Untrusted apps & plugins run with NoNewPrivileges / No setuid
3. Bubblewrap command generation and Seccomp-BPF policy construction
4. CLI integration via `kairos sandbox`
"""

import os
import sys
import unittest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from security.app_isolation import (
    IsolationTier,
    SandboxEnforcer,
    SANDBOX_PROFILES,
    BLOCKED_SYSCALLS,
    PROTECTED_PATHS
)
from scripts.services.kairos_sysd import client_request

class TestKairosApplicationIsolation(unittest.TestCase):

    def test_all_tiers_defined(self):
        """Verify all 5 application classification tiers are properly configured."""
        self.assertEqual(len(SANDBOX_PROFILES), 5)
        expected = {
            IsolationTier.TRUSTED_SYSTEM,
            IsolationTier.NORMAL_APP,
            IsolationTier.UNTRUSTED_APP,
            IsolationTier.PLUGIN,
            IsolationTier.AI_TOOL
        }
        self.assertEqual(set(SANDBOX_PROFILES.keys()), expected)

    def test_plugin_credential_denial(self):
        """CRITICAL INVARIANT 1: Plugins must be blocked from broker credentials."""
        res = SandboxEnforcer.validate_access(IsolationTier.PLUGIN, request_secret=True)
        self.assertFalse(res["allowed"])
        self.assertIn("denied access to broker credentials", res["reason"])

    def test_ai_tool_credential_denial(self):
        """CRITICAL INVARIANT 1: AI tools must be blocked from broker credentials."""
        res = SandboxEnforcer.validate_access(IsolationTier.AI_TOOL, request_secret=True)
        self.assertFalse(res["allowed"])
        self.assertIn("denied access to broker credentials", res["reason"])

    def test_plugin_risk_config_write_denial(self):
        """CRITICAL INVARIANT 2: Plugins cannot modify risk configuration."""
        res = SandboxEnforcer.validate_access(IsolationTier.PLUGIN, request_risk_config=True)
        self.assertFalse(res["allowed"])
        self.assertIn("cannot modify immutable Risk Gatekeeper", res["reason"])

    def test_ai_tool_risk_config_write_denial(self):
        """CRITICAL INVARIANT 2: AI tools cannot modify risk configuration."""
        res = SandboxEnforcer.validate_access(IsolationTier.AI_TOOL, request_risk_config=True)
        self.assertFalse(res["allowed"])
        self.assertIn("cannot modify immutable Risk Gatekeeper", res["reason"])

    def test_protected_filesystem_paths_denial(self):
        """CRITICAL INVARIANT 3: Protected paths denied to plugins, AI tools, and untrusted apps."""
        for path in PROTECTED_PATHS:
            res_plugin = SandboxEnforcer.validate_access(IsolationTier.PLUGIN, target_path=path)
            self.assertFalse(res_plugin["allowed"], f"Path {path} must be denied to PLUGIN")

            res_ai = SandboxEnforcer.validate_access(IsolationTier.AI_TOOL, target_path=path)
            self.assertFalse(res_ai["allowed"], f"Path {path} must be denied to AI_TOOL")

            res_untrusted = SandboxEnforcer.validate_access(IsolationTier.UNTRUSTED_APP, target_path=path)
            self.assertFalse(res_untrusted["allowed"], f"Path {path} must be denied to UNTRUSTED_APP")

    def test_plugin_network_denial(self):
        """CRITICAL INVARIANT 4: Plugins run with total network isolation."""
        res = SandboxEnforcer.validate_access(IsolationTier.PLUGIN, request_network=True)
        self.assertFalse(res["allowed"])
        self.assertIn("total network isolation", res["reason"])

    def test_trusted_system_allowed_access(self):
        """Verify trusted system tier can perform authorized operations."""
        res = SandboxEnforcer.validate_access(IsolationTier.TRUSTED_SYSTEM, target_path="/etc/kairos/risk", request_secret=True, request_risk_config=True)
        self.assertTrue(res["allowed"])

    def test_bubblewrap_command_construction(self):
        """Verify bubblewrap generation includes --nosuid and --unshare-net for plugins."""
        cmd = SandboxEnforcer.generate_bwrap_command(IsolationTier.PLUGIN, "/usr/bin/python3", ["strategy.py"])
        self.assertIn("bwrap", cmd)
        self.assertIn("--nosuid", cmd)
        self.assertIn("--unshare-net", cmd)
        self.assertIn("/usr/bin/python3", cmd)
        self.assertIn("strategy.py", cmd)

    def test_seccomp_strict_policy(self):
        """Verify strict seccomp profile blocks hazardous syscalls."""
        policy = SandboxEnforcer.generate_seccomp_policy(IsolationTier.PLUGIN)
        self.assertEqual(policy["default_action"], "SCMP_ACT_ERRNO")
        for sc in ["ptrace", "bpf", "reboot", "mount", "init_module"]:
            self.assertIn(sc, policy["blocked_syscalls"])

    def test_sysd_client_sandbox_profiles(self):
        """Verify sysd client request for sandbox profiles."""
        res = client_request("security.sandbox_profiles")
        self.assertEqual(res.get("total"), 5)
        tiers = [p.get("tier") for p in res.get("profiles", [])]
        self.assertIn("PLUGIN", tiers)
        self.assertIn("AI_TOOL", tiers)

if __name__ == "__main__":
    unittest.main()
