import unittest
import os
import subprocess

class TestReleaseEngineering(unittest.TestCase):
    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def test_all_27_phases_exist(self):
        phases_dir = os.path.join(self.root_dir, "scripts", "phases")
        expected_phases = [
            "01_build_system.sh",
            "02_linux_base.sh",
            "03_kernel.sh",
            "04_boot.sh",
            "05_storage.sh",
            "06_users.sh",
            "07_networking.sh",
            "08_services.sh",
            "09_hardware.sh",
            "10_graphics.sh",
            "11_wayland.sh",
            "12_hyprland.sh",
            "13_kairos_shell.sh",
            "14_desktop_utils.sh",
            "15_system_settings.sh",
            "16_package_management.sh",
            "17_security.sh",
            "18_update_recovery.sh",
            "19_trading_services.sh",
            "20_research_env.sh",
            "21_plugin_infra.sh",
            "22_ai_agents.sh",
            "23_adaptive_intelligence.sh",
            "24_installer.sh",
            "25_iso_generation.sh",
            "26_automated_testing.sh",
            "27_release_engineering.sh"
        ]
        for p in expected_phases:
            p_path = os.path.join(phases_dir, p)
            self.assertTrue(os.path.isfile(p_path), f"Phase script {p} must exist")

    def test_binaries_executable(self):
        binaries = [
            os.path.join(self.root_dir, "bin", "kairos-control"),
            os.path.join(self.root_dir, "bin", "kairos-update"),
            os.path.join(self.root_dir, "bin", "kairos-install"),
            os.path.join(self.root_dir, "services", "kairos-riskd.py"),
            os.path.join(self.root_dir, "services", "kairos-watchdog.py")
        ]
        for b in binaries:
            self.assertTrue(os.path.isfile(b), f"Binary {b} must exist")

if __name__ == "__main__":
    unittest.main()
