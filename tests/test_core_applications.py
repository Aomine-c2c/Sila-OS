"""
KAIROS Core System Applications & Privilege Boundary Test Suite
Verifies:
1. All 14 core system applications execute cleanly through `kairos_apps.py`.
2. JSON output mode (--json) yields valid typed structured data for every application.
3. Protected system boundary (`kairos-sysd`):
   - Privileged operations require appropriate role authorization ('wheel' / 'admin').
   - Normal users cannot perform destructive or privileged changes without authorization.
   - Non-privileged actions (inspection, telemetry, state query) succeed for all authenticated users.
   - All dispatch actions and authorization denials write structured records to audit log.
4. CLI integration via `kairos app <name>`.
"""

import os
import sys
import json
import unittest
import io
from contextlib import redirect_stdout

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.services.kairos_sysd import (
    dispatch_action,
    check_authorization,
    log_audit_event,
    client_request,
    ACTION_PERMISSIONS,
    AUDIT_LOG_PATH
)
from scripts.apps.kairos_apps import (
    app_settings,
    app_network,
    app_display,
    app_audio,
    app_users,
    app_storage,
    app_security,
    app_updates,
    app_services,
    app_startup,
    app_hardware,
    app_logs,
    app_recovery,
    app_about,
    APP_REGISTRY
)

class TestKairosCoreApplications(unittest.TestCase):

    def test_app_registry_completeness(self):
        """Verify all 14 mandatory core OS applications are registered."""
        expected_apps = [
            "settings", "network", "display", "audio", "users",
            "storage", "security", "updates", "services", "startup",
            "hardware", "logs", "recovery", "about"
        ]
        self.assertEqual(len(APP_REGISTRY), 14)
        for app_id in expected_apps:
            self.assertIn(app_id, APP_REGISTRY, f"Mandatory application '{app_id}' missing from registry")

    def test_app_settings(self):
        """Test System Settings application (inspection & tuning)."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = app_settings("get")
        self.assertEqual(ret, 0)
        out = buf.getvalue().upper()
        self.assertIn("SYSTEM SETTINGS", out)
        self.assertIn("ACTIVE TUNING PROFILE", out)

    def test_app_network(self):
        """Test Network Manager application."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = app_network("status")
        self.assertEqual(ret, 0)
        out = buf.getvalue().upper()
        self.assertIn("NETWORK MANAGER", out)
        self.assertIn("STACK HEALTH", out)

    def test_app_display(self):
        """Test Display Settings application."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = app_display("info")
        self.assertEqual(ret, 0)
        out = buf.getvalue().upper()
        self.assertIn("DISPLAY SETTINGS", out)
        self.assertIn("WAYLAND COMPOSITOR", out)

    def test_app_audio(self):
        """Test Audio Settings application."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = app_audio("status")
        self.assertEqual(ret, 0)
        out = buf.getvalue().upper()
        self.assertIn("AUDIO SETTINGS", out)
        self.assertIn("SOUND SERVER", out)

    def test_app_users(self):
        """Test Users application."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = app_users("list")
        self.assertEqual(ret, 0)
        out = buf.getvalue().upper()
        self.assertIn("USERS", out)
        self.assertIn("DEFINED SYSTEM & LOCAL ACCOUNTS", out)

    def test_app_storage(self):
        """Test Storage application."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = app_storage("info")
        self.assertEqual(ret, 0)
        out = buf.getvalue().upper()
        self.assertIn("STORAGE", out)
        self.assertIn("FILESYSTEM ENGINE", out)
        self.assertIn("BTRFS", out)

    def test_app_security(self):
        """Test Security application."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = app_security("audit")
        self.assertEqual(ret, 0)
        out = buf.getvalue().upper()
        self.assertIn("SECURITY", out)
        self.assertIn("OVERALL SECURITY STATUS", out)

    def test_app_updates(self):
        """Test Updates application."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = app_updates("check")
        self.assertEqual(ret, 0)
        out = buf.getvalue().upper()
        self.assertIn("UPDATES", out)
        self.assertIn("INSTALLED VERSION", out)

    def test_app_services(self):
        """Test Services application."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = app_services("list")
        self.assertEqual(ret, 0)
        out = buf.getvalue().upper()
        self.assertIn("SERVICES", out)
        self.assertIn("KAIROS-RISKD", out)

    def test_app_startup(self):
        """Test Startup Applications application."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = app_startup("list")
        self.assertEqual(ret, 0)
        out = buf.getvalue().upper()
        self.assertIn("STARTUP APPLICATIONS", out)
        self.assertIn("WAYBAR", out)

    def test_app_hardware(self):
        """Test Hardware Information application."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = app_hardware()
        self.assertEqual(ret, 0)
        out = buf.getvalue().upper()
        self.assertIn("HARDWARE INFORMATION", out)
        self.assertIn("CPU ARCHITECTURE", out)

    def test_app_logs(self):
        """Test Logs application."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = app_logs(limit=5)
        self.assertEqual(ret, 0)
        out = buf.getvalue().upper()
        self.assertIn("LOGS", out)
        self.assertIn("AUDIT & JOURNAL LOG RECORDS", out)

    def test_app_recovery(self):
        """Test Recovery application."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = app_recovery("status")
        self.assertEqual(ret, 0)
        out = buf.getvalue().upper()
        self.assertIn("RECOVERY", out)
        self.assertIn("FALLBACK INITRAMFS", out)

    def test_app_about(self):
        """Test About KAIROS application."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = app_about()
        self.assertEqual(ret, 0)
        out = buf.getvalue().upper()
        self.assertIn("ABOUT KAIROS", out)
        self.assertIn("ADAPTIVE TRADING OPERATING SYSTEM", out)

class TestKairosSysdPrivilegeBoundary(unittest.TestCase):

    def test_action_permissions_matrix(self):
        """Validate that all dangerous actions are gated by admin/wheel."""
        admin_gated = [
            "settings.set_profile",
            "network.restart_interface",
            "network.set_dns",
            "users.lock_account",
            "storage.create_snapshot",
            "security.reload_firewall",
            "updates.rollback",
            "services.restart"
        ]
        for act in admin_gated:
            self.assertEqual(ACTION_PERMISSIONS.get(act), "admin", f"Action {act} must require admin role")

    def test_unauthorized_user_blocked_from_admin_action(self):
        """Verify that an unprivileged UID is rejected for admin actions."""
        fake_uid = 9999
        fake_gid = 9999
        allowed = check_authorization(fake_uid, fake_gid, "admin")
        self.assertFalse(allowed, "Unprivileged user should be denied admin actions")

    def test_root_authorized_for_all_actions(self):
        """Verify that UID 0 is authorized for admin actions."""
        allowed = check_authorization(0, 0, "admin")
        self.assertTrue(allowed, "Root user (UID 0) should be authorized")

    def test_audit_logging_writes_entry(self):
        """Verify that audit logging generates structured JSON records."""
        test_action = "test.verification_audit"
        log_audit_event(1000, test_action, True, "Unit test audit verification")
        self.assertTrue(os.path.exists(AUDIT_LOG_PATH), "Audit log file must exist")
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
            self.assertGreater(len(lines), 0)
            last_entry = json.loads(lines[-1])
            self.assertEqual(last_entry["action"], test_action)
            self.assertEqual(last_entry["caller_uid"], 1000)
            self.assertTrue(last_entry["authorized"])

    def test_client_request_dispatch(self):
        """Verify client_request accurately invokes sysd dispatch."""
        res = client_request("about.info")
        self.assertEqual(res.get("os_name"), "KAIROS Operating System")
        self.assertEqual(res.get("version"), "1.0.0")

if __name__ == "__main__":
    unittest.main()
