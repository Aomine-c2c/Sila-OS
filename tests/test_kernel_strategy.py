import unittest
import os
from scripts.validate_kernel_config import validate_configuration, load_fragments, REQUIRED_KERNEL_OPTIONS

class TestKernelStrategy(unittest.TestCase):
    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.config_dir = os.path.join(self.root_dir, "config", "kernel")

    def test_kernel_configuration_fragments_exist(self):
        expected_fragments = [
            "00-core-hardware.config",
            "10-storage-filesystems.config",
            "20-networking.config",
            "30-desktop-graphics.config",
            "40-audio-peripherals.config",
            "50-security.config",
            "60-performance.config",
            "70-virtualization.config"
        ]
        for frag in expected_fragments:
            p = os.path.join(self.config_dir, frag)
            self.assertTrue(os.path.isfile(p), f"Fragment {frag} must exist")

    def test_automated_kernel_config_validation(self):
        res = validate_configuration(self.config_dir)
        self.assertEqual(res, 0, "Automated kernel configuration audit must pass")

    def test_uefi_and_nvme_enabled(self):
        options, _ = load_fragments(self.config_dir)
        self.assertEqual(options.get("CONFIG_EFI"), "y")
        self.assertEqual(options.get("CONFIG_EFIVAR_FS"), "y")
        self.assertEqual(options.get("CONFIG_BLK_DEV_NVME"), "y")
        self.assertEqual(options.get("CONFIG_BTRFS_FS"), "y")

    def test_desktop_graphics_drm_enabled(self):
        options, _ = load_fragments(self.config_dir)
        self.assertEqual(options.get("CONFIG_DRM"), "y")
        self.assertIn(options.get("CONFIG_DRM_AMDGPU"), ["m", "y"])
        self.assertIn(options.get("CONFIG_DRM_I915"), ["m", "y"])
        self.assertIn(options.get("CONFIG_DRM_NOUVEAU"), ["m", "y"])

    def test_kernel_strategy_documentation(self):
        doc = os.path.join(self.root_dir, "docs", "architecture", "KERNEL_STRATEGY.md")
        self.assertTrue(os.path.isfile(doc), "KERNEL_STRATEGY.md must exist")
        with open(doc, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Kernel Version Strategy", content)
        self.assertIn("Module Strategy", content)
        self.assertIn("Firmware Strategy", content)

if __name__ == "__main__":
    unittest.main()
