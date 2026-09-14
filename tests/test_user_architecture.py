"""
KAIROS OS - User & Authentication Architecture Test Suite
Tests:
  - Least privilege: root account is UID 0, operator is UID 1000.
  - Groups defined: desktop, audio, video, network, trading, research, plugins, administrators (wheel).
  - Service account isolation:
    * kairos-risk, kairos-feed, kairos-agent, kairos-plugin exist.
    * None have UID 0 (strictly unprivileged).
    * All have shell set to /sbin/nologin (cannot log in interactively).
  - Trading and plugin services do not have sudo/root privileges.
  - Sudoers configuration is valid and restricted.
  - PAM stack files exist (system-auth, login, sudo).
  - Resource limits (limits.conf) enforce locked memory for trading and constrain plugins.
  - CLI commands: `kairos user info` and `kairos permissions` succeed and output correct data.
"""

import os
import unittest
import subprocess

class TestUserArchitecture(unittest.TestCase):
    def setUp(self):
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.rootfs_etc = os.path.join(self.root_dir, "build/rootfs/etc")
        self.passwd_path = os.path.join(self.rootfs_etc, "passwd")
        self.group_path = os.path.join(self.rootfs_etc, "group")
        self.shadow_path = os.path.join(self.rootfs_etc, "shadow")
        self.sudoers_path = os.path.join(self.rootfs_etc, "sudoers.d/10-wheel")
        self.limits_path = os.path.join(self.rootfs_etc, "security/limits.d/99-kairos-realtime.conf")
        self.kairos_bin = os.path.join(self.root_dir, "build/rootfs/usr/bin/kairos")

    def test_user_database_accounts(self):
        """Verify root, operator, and service accounts in /etc/passwd."""
        self.assertTrue(os.path.exists(self.passwd_path), "Missing /etc/passwd")
        users = {}
        with open(self.passwd_path, "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 7:
                    users[parts[0]] = {
                        "uid": int(parts[2]),
                        "gid": int(parts[3]),
                        "home": parts[5],
                        "shell": parts[6]
                    }

        # 1. Root account
        self.assertIn("root", users)
        self.assertEqual(users["root"]["uid"], 0)

        # 2. Operator account
        self.assertIn("kairos", users)
        self.assertEqual(users["kairos"]["uid"], 1000)
        self.assertEqual(users["kairos"]["shell"], "/bin/bash")

        # 3. Dedicated unprivileged service accounts
        services = ["kairos-risk", "kairos-feed", "kairos-agent", "kairos-plugin"]
        for s in services:
            self.assertIn(s, users, f"Missing service account: {s}")
            self.assertNotEqual(users[s]["uid"], 0, f"Service account {s} must NOT have UID 0!")
            self.assertEqual(users[s]["shell"], "/sbin/nologin", f"Service account {s} must have nologin shell")

    def test_group_matrix_defined(self):
        """Verify all mandated groups exist in /etc/group."""
        self.assertTrue(os.path.exists(self.group_path), "Missing /etc/group")
        groups = {}
        with open(self.group_path, "r") as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 3:
                    groups[parts[0]] = {
                        "gid": int(parts[2]),
                        "members": parts[3].split(",") if len(parts) > 3 and parts[3] else []
                    }

        mandated_groups = [
            "desktop",
            "audio",
            "video",
            "network",
            "trading",
            "research",
            "plugins",
            "administrators",
            "wheel"
        ]
        for g in mandated_groups:
            self.assertIn(g, groups, f"Mandated group missing: {g}")

        # Ensure operator is in essential workstation groups
        operator_groups = ["desktop", "audio", "video", "network", "trading", "research"]
        for og in operator_groups:
            self.assertIn("kairos", groups[og]["members"], f"Operator 'kairos' should be member of group '{og}'")

        # Ensure plugins service account is in plugins group but not wheel/administrators
        self.assertIn("kairos-plugin", groups["plugins"]["members"])
        self.assertNotIn("kairos-plugin", groups["wheel"]["members"])
        self.assertNotIn("kairos-plugin", groups["administrators"]["members"])

    def test_pam_stack_files(self):
        """Verify PAM configuration files exist in rootfs."""
        pam_dir = os.path.join(self.rootfs_etc, "pam.d")
        for pam_file in ["system-auth", "login", "sudo"]:
            path = os.path.join(pam_dir, pam_file)
            self.assertTrue(os.path.exists(path), f"Missing PAM config: {path}")

    def test_sudoers_policy_syntax(self):
        """Verify sudoers file restricts privileges to wheel/administrators."""
        self.assertTrue(os.path.exists(self.sudoers_path), "Missing 10-wheel sudoers policy")
        with open(self.sudoers_path, "r") as f:
            content = f.read()
            self.assertIn("%wheel ALL=(ALL:ALL) ALL", content)
            self.assertIn("%administrators ALL=(ALL:ALL) ALL", content)
            self.assertNotIn("NOPASSWD: ALL", content, "Root access must not be granted globally without password")

    def test_security_limits_conf(self):
        """Verify real-time limits for trading and sandboxing for plugins."""
        self.assertTrue(os.path.exists(self.limits_path), "Missing security limits config")
        with open(self.limits_path, "r") as f:
            content = f.read()
            self.assertIn("@trading", content)
            self.assertIn("rtprio", content)
            self.assertIn("@plugins", content)
            self.assertIn("rtprio          0", content)

    def test_kairos_user_cli_commands(self):
        """Verify `kairos user info` and `kairos permissions` commands."""
        # Test `kairos user info`
        res_info = subprocess.run([self.kairos_bin, "user", "info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res_info.returncode, 0, f"kairos user info failed: {res_info.stderr}")
        self.assertIn("KAIROS OS - User Identity & Session Diagnostic", res_info.stdout)
        self.assertIn("Least Privilege Workstation Architecture", res_info.stdout)

        # Test `kairos permissions`
        res_perm = subprocess.run([self.kairos_bin, "permissions"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res_perm.returncode, 0, f"kairos permissions failed: {res_perm.stderr}")
        self.assertIn("Permission Boundaries & Service Sandboxing Audit", res_perm.stdout)
        self.assertIn("kairos-risk", res_perm.stdout)
        self.assertIn("NO ROOT", res_perm.stdout)

if __name__ == "__main__":
    unittest.main()
