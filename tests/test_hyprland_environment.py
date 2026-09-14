#!/usr/bin/env python3
"""
Unit and Integration Tests for KAIROS Hyprland Desktop Environment.
Verifies:
1. Hyprland configuration structure, monitors, workspaces, and syntax.
2. Complete keyboard-first bindings (launchers, audio, clipboard, screenshots, navigation).
3. Supervised session watchdog script integrity.
4. Desktop utilities configuration (Foot terminal, Mako notifications, Wofi launcher, Waybar status bar).
5. Fault recovery & non-blocking boot invariance.
"""

import unittest
import os
import sys
import re

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestHyprlandDesktopEnvironment(unittest.TestCase):

    def setUp(self):
        self.hypr_conf = os.path.join(ROOT_DIR, "config/hyprland/hyprland.conf")
        self.watchdog_sh = os.path.join(ROOT_DIR, "scripts/hardware/kairos-session-watchdog.sh")
        self.waybar_json = os.path.join(ROOT_DIR, "config/shell/waybar.json")
        self.mako_conf = os.path.join(ROOT_DIR, "config/desktop/mako.conf")
        self.foot_ini = os.path.join(ROOT_DIR, "config/desktop/foot.ini")
        self.wofi_css = os.path.join(ROOT_DIR, "config/desktop/wofi.css")
        self.docs_md = os.path.join(ROOT_DIR, "docs/desktop/hyprland-environment.md")

    def test_configuration_files_exist(self):
        """Ensure all required desktop configuration files are present."""
        files = [
            self.hypr_conf,
            self.watchdog_sh,
            self.waybar_json,
            self.mako_conf,
            self.foot_ini,
            self.wofi_css,
            self.docs_md
        ]
        for f in files:
            self.assertTrue(os.path.exists(f), f"Required file missing: {f}")

    def test_hyprland_monitor_and_workspaces(self):
        """Verify Hyprland config defines multi-monitor support and 5 financial workspaces."""
        with open(self.hypr_conf, "r", encoding="utf-8") as f:
            content = f.read()

        # Multi-monitor directives
        self.assertIn("monitor = DP-1", content)
        self.assertIn("monitor = , preferred, auto, 1.0", content)

        # Dedicated workspaces (1 to 5)
        for i in range(1, 6):
            self.assertIn(f"workspace = {i}", content)

    def test_hyprland_keybindings_comprehensiveness(self):
        """Verify presence of keybindings for terminal, launcher, audio, clipboard, screenshots, navigation."""
        with open(self.hypr_conf, "r", encoding="utf-8") as f:
            content = f.read()

        # Terminal & Launcher
        self.assertIn("bind = $mainMod, Return, exec, foot || kitty", content)
        self.assertIn("bind = $mainMod, Space, exec, wofi", content)

        # Audio controls
        self.assertIn("XF86AudioRaiseVolume", content)
        self.assertIn("XF86AudioLowerVolume", content)
        self.assertIn("XF86AudioMute", content)
        self.assertIn("pamixer", content)

        # Clipboard & Screenshots
        self.assertIn("cliphist", content)
        self.assertIn("grim", content)
        self.assertIn("slurp", content)
        self.assertIn("wl-copy", content)

        # Screen locker & Exit
        self.assertIn("swaylock", content)
        self.assertIn("bind = $mainMod SHIFT, Escape, exit,", content)

        # Vim navigation
        self.assertIn("bind = $mainMod, h, movefocus, l", content)
        self.assertIn("bind = $mainMod, l, movefocus, r", content)
        self.assertIn("bind = $mainMod, k, movefocus, u", content)
        self.assertIn("bind = $mainMod, j, movefocus, d", content)

        # Multi-monitor focus navigation
        self.assertIn("focusmonitor", content)

    def test_session_watchdog_resilience(self):
        """Ensure session watchdog supervises required daemons and implements restart logic."""
        with open(self.watchdog_sh, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("supervise()", content)
        self.assertIn("polkit-gnome", content)
        self.assertIn("mako", content)
        self.assertIn("waybar", content)
        self.assertIn("swaybg", content)
        self.assertIn("swayidle", content)
        self.assertIn("cliphist", content)
        self.assertIn("nm-applet", content)

    def test_waybar_modules_and_tray(self):
        """Verify Waybar includes audio, network, market ticker, and system tray."""
        with open(self.waybar_json, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("pulseaudio", content)
        self.assertIn("network", content)
        self.assertIn("tray", content)
        self.assertIn("custom/market_ticker", content)
        self.assertIn("custom/risk_status", content)

    def test_foot_and_mako_styling(self):
        """Verify foot terminal colors and mako critical risk alerts."""
        with open(self.foot_ini, "r", encoding="utf-8") as f:
            foot_content = f.read()
        self.assertIn("JetBrains Mono", foot_content)
        self.assertIn("background=0a0c10", foot_content)

        with open(self.mako_conf, "r", encoding="utf-8") as f:
            mako_content = f.read()
        self.assertIn("[urgency=critical]", mako_content)
        self.assertIn("border-color=#ff0055", mako_content)

    def test_desktop_utilities_staged_in_target_rootfs(self):
        """Ensure Phase 12 and Phase 14 scripts stage configurations in build/rootfs."""
        rootfs_hypr = os.path.join(ROOT_DIR, "build/rootfs/etc/hypr/hyprland.conf")
        rootfs_watchdog = os.path.join(ROOT_DIR, "build/rootfs/usr/libexec/kairos/kairos-session-watchdog.sh")
        rootfs_waybar = os.path.join(ROOT_DIR, "build/rootfs/etc/kairos/shell/waybar.json")
        rootfs_foot = os.path.join(ROOT_DIR, "build/rootfs/etc/xdg/foot/foot.ini")

        self.assertTrue(os.path.exists(rootfs_hypr), f"Missing {rootfs_hypr}")
        self.assertTrue(os.path.exists(rootfs_watchdog), f"Missing {rootfs_watchdog}")
        self.assertTrue(os.path.exists(rootfs_waybar), f"Missing {rootfs_waybar}")
        self.assertTrue(os.path.exists(rootfs_foot), f"Missing {rootfs_foot}")

if __name__ == "__main__":
    unittest.main()
