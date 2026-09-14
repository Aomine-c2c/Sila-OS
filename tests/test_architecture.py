import unittest
import os
import sys

class TestKairosArchitecture(unittest.TestCase):
    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def test_makefile_exists(self):
        makefile = os.path.join(self.root_dir, "Makefile")
        self.assertTrue(os.path.isfile(makefile), "Root Makefile must exist")

    def test_build_scripts_exist(self):
        check_script = os.path.join(self.root_dir, "scripts", "check_environment.py")
        phase_script = os.path.join(self.root_dir, "scripts", "build_phase.sh")
        self.assertTrue(os.path.isfile(check_script), "check_environment.py must exist")
        self.assertTrue(os.path.isfile(phase_script), "build_phase.sh must exist")

    def test_build_order_phases_defined(self):
        with open(os.path.join(self.root_dir, "Makefile"), "r", encoding="utf-8") as f:
            content = f.read()
        phases = [
            "01_build_system", "02_linux_base", "03_kernel", "04_boot",
            "05_storage", "06_users", "07_networking", "08_services",
            "09_hardware", "10_graphics", "11_wayland", "12_hyprland",
            "13_kairos_shell", "14_desktop_utils", "15_system_settings",
            "16_package_management", "17_security", "18_update_recovery",
            "19_trading_services", "20_research_env", "21_plugin_infra",
            "22_ai_agents", "23_adaptive_intelligence", "24_installer",
            "25_iso_generation", "26_automated_testing", "27_release_engineering"
        ]
        for p in phases:
            self.assertIn(p, content, f"Phase {p} must be defined in Makefile")

if __name__ == "__main__":
    unittest.main()
