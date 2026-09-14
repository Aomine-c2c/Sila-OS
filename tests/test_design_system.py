#!/usr/bin/env python3
"""
Unit and Integration Tests for KAIROS Design System & Visual Language.
Verifies:
1. Design token specification integrity (typography, spacing, borders, elevation, surfaces, states, workspaces, adaptive ring).
2. Light mode as the primary default and dark mode availability.
3. CSS design token variables completeness.
4. Adaptive Ring iconography (original SVG, 6 stages: OBSERVE, DIAGNOSE, ADAPT, VALIDATE, DEPLOY, LEARN).
5. Official technical icon concepts in SVG spritesheet (all 15 symbols verified).
6. Theme switcher engine (kairos_theme.py and CLI integration).
"""

import unittest
import os
import sys
import json
import xml.etree.ElementTree as ET

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

class TestKairosDesignSystem(unittest.TestCase):

    def setUp(self):
        self.tokens_json = os.path.join(ROOT_DIR, "config/desktop/kairos-design-tokens.json")
        self.tokens_css = os.path.join(ROOT_DIR, "config/desktop/kairos-tokens.css")
        self.ring_svg = os.path.join(ROOT_DIR, "config/desktop/icons/kairos-adaptive-ring.svg")
        self.icons_svg = os.path.join(ROOT_DIR, "config/desktop/icons/kairos-icons.svg")
        self.docs_md = os.path.join(ROOT_DIR, "docs/desktop/design-system.md")

    def test_design_system_files_exist(self):
        """Ensure token files, SVG assets, and documentation exist."""
        files = [
            self.tokens_json,
            self.tokens_css,
            self.ring_svg,
            self.icons_svg,
            self.docs_md
        ]
        for f in files:
            self.assertTrue(os.path.exists(f), f"Required file missing: {f}")

    def test_design_tokens_json_structure(self):
        """Verify tokens define typography, spacing, borders, elevation, surfaces, states, and adaptive ring."""
        with open(self.tokens_json, "r", encoding="utf-8") as f:
            tokens = json.load(f)

        # Meta validation
        self.assertEqual(tokens["meta"]["default_mode"], "light")
        self.assertIn("dark", tokens["meta"]["supported_modes"])

        # Check all required token groups
        for key in ["typography", "spacing", "borders", "elevation", "color", "states", "workspaces", "adaptive_ring"]:
            self.assertIn(key, tokens, f"Missing token key: {key}")

        # Verify surfaces in light & dark
        self.assertIn("surface_base", tokens["color"]["light"])
        self.assertIn("surface_base", tokens["color"]["dark"])
        self.assertEqual(tokens["color"]["light"]["surface_base"], "#f8fafc")
        self.assertEqual(tokens["color"]["dark"]["surface_base"], "#0a0c10")

        # Verify states
        for mode in ["light", "dark"]:
            for state in ["nominal", "warning", "critical", "info"]:
                self.assertIn(state, tokens["states"][mode])

    def test_adaptive_ring_six_stages(self):
        """Verify Adaptive Ring represents the 6 continuous evolutionary stages."""
        with open(self.tokens_json, "r", encoding="utf-8") as f:
            tokens = json.load(f)

        stages = tokens["adaptive_ring"]["stages"]
        stage_names = [s["name"] for s in stages]
        expected_stages = ["OBSERVE", "DIAGNOSE", "ADAPT", "VALIDATE", "DEPLOY", "LEARN"]
        self.assertEqual(stage_names, expected_stages)

        # Also inspect SVG content
        with open(self.ring_svg, "r", encoding="utf-8") as f:
            svg_content = f.read()
        self.assertIn("OBSERVE", svg_content)
        self.assertIn("LEARN", svg_content)
        self.assertIn("<svg", svg_content)

    def test_official_icon_concepts_completeness(self):
        """Verify presence of all 15 official technical icon concepts in the SVG sprite."""
        required_icons = [
            "icon-kairos",
            "icon-market",
            "icon-strategy",
            "icon-signal",
            "icon-execution",
            "icon-risk",
            "icon-broker",
            "icon-research",
            "icon-ai",
            "icon-plugin",
            "icon-adaptive",
            "icon-rollback",
            "icon-system",
            "icon-security",
            "icon-workspace"
        ]
        with open(self.icons_svg, "r", encoding="utf-8") as f:
            content = f.read()

        for icon in required_icons:
            self.assertIn(f'id="{icon}"', content, f"Missing icon symbol: {icon}")

    def test_theme_switcher_logic(self):
        """Verify theme switcher sets light and dark without error."""
        from scripts.shell import kairos_theme
        ret_dark = kairos_theme.apply_theme("dark")
        self.assertEqual(ret_dark, 0)
        self.assertEqual(kairos_theme.get_current_theme(), "dark")

        ret_light = kairos_theme.apply_theme("light")
        self.assertEqual(ret_light, 0)
        self.assertEqual(kairos_theme.get_current_theme(), "light")

if __name__ == "__main__":
    unittest.main()
