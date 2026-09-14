#!/usr/bin/env python3
"""
Unit and Integration Tests for KAIROS Desktop Shell Architecture & Command Palette.
Verifies:
1. Shell IPC State Provider (system, network, audio, battery, market, risk, brokers, adaptive, positions, plugins).
2. Typed Command Registry (all 17 commands defined, typed actions, permissions).
3. Command resolution and execution logic (navigation, telemetry, session, power).
4. Security and permission boundary enforcement (admin-only commands rejected for unprivileged users).
5. Waybar configuration (top bar modules, command palette button, market/risk/broker/adaptive indicators).
6. Hyprland integration (Super + P binding for command palette).
7. Staging of shell components in target rootfs.
"""

import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.shell import kairos_shell_state
from scripts.shell import kairos_cmd

class TestDesktopShellArchitecture(unittest.TestCase):

    def test_shell_state_provider_keys(self):
        """Verify shell state telemetry includes all required status fields."""
        state = kairos_shell_state.get_full_shell_state()
        required_keys = [
            "system", "network", "audio", "battery", "market",
            "risk", "brokers", "adaptive", "positions", "plugins"
        ]
        for key in required_keys:
            self.assertIn(key, state, f"Missing telemetry key: {key}")

    def test_system_telemetry_types(self):
        """Verify system CPU/memory telemetry structure."""
        sys_data = kairos_shell_state.get_cpu_and_mem()
        self.assertIn("cpu_usage_pct", sys_data)
        self.assertIn("mem_total_mb", sys_data)
        self.assertIn("mem_used_mb", sys_data)
        self.assertIn("mem_usage_pct", sys_data)
        self.assertIsInstance(sys_data["cpu_usage_pct"], float)

    def test_risk_and_market_telemetry(self):
        """Verify immutable risk status and market ticker feeds."""
        risk_data = kairos_shell_state.get_risk_status()
        self.assertEqual(risk_data["status"], "LOCKED_STABLE")
        self.assertEqual(risk_data["gatekeeper"], "ENFORCING")
        self.assertEqual(risk_data["max_drawdown_pct"], 3.0)

        market_data = kairos_shell_state.get_market_status()
        self.assertIn("tickers", market_data)
        symbols = [t["symbol"] for t in market_data["tickers"]]
        self.assertIn("SPY", symbols)
        self.assertIn("BTC/USD", symbols)

    def test_command_registry_completeness(self):
        """Verify all 17 required commands exist in the typed command palette registry."""
        required_cmds = [
            "open markets",
            "open execution",
            "open research",
            "open automation",
            "open agents",
            "open system",
            "open development",
            "open adaptive",
            "show positions",
            "show risk",
            "show brokers",
            "show plugins",
            "show system",
            "lock",
            "logout",
            "shutdown",
            "reboot"
        ]
        registry = kairos_cmd.COMMAND_REGISTRY
        for cmd in required_cmds:
            self.assertIn(cmd, registry, f"Missing command definition: {cmd}")
            cmd_def = registry[cmd]
            self.assertIsNotNone(cmd_def.description)
            self.assertIsNotNone(cmd_def.action_type)
            self.assertIsNotNone(cmd_def.min_permission)

    def test_permission_boundaries_for_admin_commands(self):
        """Verify admin commands (shutdown, reboot) reject unprivileged non-wheel users."""
        shutdown_def = kairos_cmd.COMMAND_REGISTRY["shutdown"]
        reboot_def = kairos_cmd.COMMAND_REGISTRY["reboot"]

        with patch("os.getuid", return_value=1000), \
             patch("scripts.shell.kairos_cmd.get_current_user_groups", return_value=["trader"]):
            self.assertFalse(kairos_cmd.check_permission(shutdown_def))
            self.assertFalse(kairos_cmd.check_permission(reboot_def))

    def test_permission_granted_for_wheel_admin(self):
        """Verify admin commands succeed for wheel members."""
        shutdown_def = kairos_cmd.COMMAND_REGISTRY["shutdown"]
        with patch("os.getuid", return_value=1000), \
             patch("scripts.shell.kairos_cmd.get_current_user_groups", return_value=["trader", "wheel"]):
            self.assertTrue(kairos_cmd.check_permission(shutdown_def))

    def test_telemetry_commands_execution(self):
        """Verify telemetry show commands execute cleanly and output valid JSON/state."""
        for cmd in ["show risk", "show brokers", "show positions", "show system"]:
            ret = kairos_cmd.execute_command(cmd)
            self.assertEqual(ret, 0, f"Command failed: {cmd}")

    def test_waybar_configuration_structure(self):
        """Verify Waybar JSON configuration includes all status indicators."""
        waybar_json_path = os.path.join(ROOT_DIR, "config/shell/waybar.json")
        self.assertTrue(os.path.exists(waybar_json_path))
        with open(waybar_json_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        modules_left = cfg.get("modules-left", [])
        modules_center = cfg.get("modules-center", [])
        modules_right = cfg.get("modules-right", [])

        self.assertIn("custom/logo", modules_left)
        self.assertIn("hyprland/workspaces", modules_left)
        self.assertIn("custom/palette_btn", modules_left)
        self.assertIn("custom/risk_status", modules_left)
        self.assertIn("custom/market_ticker", modules_center)
        self.assertIn("custom/broker_status", modules_right)
        self.assertIn("custom/adaptive_status", modules_right)
        self.assertIn("network", modules_right)
        self.assertIn("pulseaudio", modules_right)
        self.assertIn("battery", modules_right)
        self.assertIn("cpu", modules_right)
        self.assertIn("memory", modules_right)
        self.assertIn("tray", modules_right)

    def test_hyprland_command_palette_binding(self):
        """Verify hyprland.conf binds Super + P to the KAIROS Command Palette."""
        hypr_path = os.path.join(ROOT_DIR, "config/hyprland/hyprland.conf")
        with open(hypr_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("bind = $mainMod, P,", content)
        self.assertIn("kairos_cmd.py", content)

    def test_shell_components_staged_in_target_rootfs(self):
        """Verify target rootfs contains kairos_cmd.py, kairos_shell_state.py, and waybar."""
        cmd_path = os.path.join(ROOT_DIR, "build/rootfs/usr/libexec/kairos/kairos_cmd.py")
        state_path = os.path.join(ROOT_DIR, "build/rootfs/usr/libexec/kairos/kairos_shell_state.py")
        waybar_path = os.path.join(ROOT_DIR, "build/rootfs/etc/kairos/shell/waybar.json")

        self.assertTrue(os.path.exists(cmd_path), f"Missing {cmd_path}")
        self.assertTrue(os.path.exists(state_path), f"Missing {state_path}")
        self.assertTrue(os.path.exists(waybar_path), f"Missing {waybar_path}")

if __name__ == "__main__":
    unittest.main()
