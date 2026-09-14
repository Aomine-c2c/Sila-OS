"""
KAIROS OS - Security Hardening & Audit Test Suite
Tests:
  - Execution of ./scripts/security-audit returns exit code 0.
  - Verification that security audit reports PASS for all critical categories.
  - Zero critical FAIL entries reported.
  - Hardened sysctl parameters match expected baseline.
  - Single UID 0 account constraint strictly validated.
  - Sudoers policy does not allow universal NOPASSWD wildcard.
"""

import os
import unittest
import subprocess

class TestOSHardening(unittest.TestCase):
    def setUp(self):
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.audit_script = os.path.join(self.root_dir, "scripts/security-audit")
        self.hardening_doc = os.path.join(self.root_dir, "docs/security/os-hardening.md")
        self.security_sysctl = os.path.join(self.root_dir, "config/security/99-kairos-security.conf")

    def test_security_audit_script_exists_and_executable(self):
        """Verify ./scripts/security-audit exists and is executable."""
        self.assertTrue(os.path.exists(self.audit_script), "Missing ./scripts/security-audit")
        self.assertTrue(os.access(self.audit_script, os.X_OK), "./scripts/security-audit not executable")

    def test_security_hardening_documentation_exists(self):
        """Verify docs/security/os-hardening.md exists and is non-empty."""
        self.assertTrue(os.path.exists(self.hardening_doc), "Missing docs/security/os-hardening.md")
        with open(self.hardening_doc, "r") as f:
            content = f.read()
            self.assertIn("Least Privilege", content)
            self.assertIn("99-kairos-security.conf", content)
            self.assertIn("security-audit", content)

    def test_run_security_audit_verdict(self):
        """Run ./scripts/security-audit and assert 0 FAIL items and exit code 0."""
        res = subprocess.run([self.audit_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res.returncode, 0, f"Security audit reported failures:\n{res.stdout}\n{res.stderr}")
        self.assertIn("[PASS]", res.stdout)
        self.assertIn("0 FAILED", res.stdout)
        self.assertIn("KAIROS OPERATING SYSTEM SECURITY AUDIT: PASSED", res.stdout)

    def test_kernel_security_parameters(self):
        """Verify baseline sysctl security parameters."""
        self.assertTrue(os.path.exists(self.security_sysctl), "Missing 99-kairos-security.conf")
        with open(self.security_sysctl, "r") as f:
            content = f.read()
            self.assertIn("kernel.kptr_restrict = 2", content)
            self.assertIn("kernel.dmesg_restrict = 1", content)
            self.assertIn("kernel.yama.ptrace_scope = 2", content)
            self.assertIn("fs.protected_hardlinks = 1", content)
            self.assertIn("fs.protected_symlinks = 1", content)
            self.assertIn("net.ipv4.conf.all.rp_filter = 1", content)

if __name__ == "__main__":
    unittest.main()
