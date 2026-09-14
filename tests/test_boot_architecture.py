"""
KAIROS OS - Boot Architecture & Invariants Test Suite
Tests:
  - UEFI directory layout and BLS entries
  - systemd-boot configuration & entries (normal, fallback, recovery, diag)
  - GRUB2 EFI configuration & visual identity syntax
  - Kernel and initramfs artifacts (vmlinuz, normal initrd, fallback initrd)
  - Boot diagnostic utility capabilities in rootfs
  - Parameter parsing and resilience rules
"""

import os
import unittest

class TestBootArchitecture(unittest.TestCase):
    def setUp(self):
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def test_bootloader_config_files(self):
        """Verify presence of master loader.conf and grub.cfg."""
        loader_conf = os.path.join(self.root_dir, "config/boot/loader.conf")
        grub_cfg = os.path.join(self.root_dir, "config/boot/grub.cfg")
        self.assertTrue(os.path.exists(loader_conf), "Missing config/boot/loader.conf")
        self.assertTrue(os.path.exists(grub_cfg), "Missing config/boot/grub.cfg")

        with open(loader_conf, "r") as f:
            content = f.read()
            self.assertIn("default kairos.conf", content)
            self.assertIn("timeout 3", content)
            self.assertIn("editor no", content)

        with open(grub_cfg, "r") as f:
            content = f.read()
            self.assertIn("KAIROS OS (Adaptive Trading Operating System)", content)
            self.assertIn("KAIROS OS (Fallback Boot / Safe Drivers)", content)
            self.assertIn("KAIROS OS (Recovery Mode / Emergency Shell)", content)
            self.assertIn("KAIROS OS (Boot & Hardware Diagnostics)", content)
            self.assertIn("insmod efi_gop", content)
            self.assertIn("insmod btrfs", content)
            self.assertIn("terminal_output gfxterm", content)

    def test_systemd_boot_entries(self):
        """Verify all 4 required systemd-boot BLS entry configurations."""
        entries_dir = os.path.join(self.root_dir, "config/boot/entries")
        entries = ["kairos.conf", "kairos-fallback.conf", "kairos-recovery.conf", "kairos-diag.conf"]
        for entry in entries:
            path = os.path.join(entries_dir, entry)
            self.assertTrue(os.path.exists(path), f"Missing entry: {path}")

        # Normal entry
        with open(os.path.join(entries_dir, "kairos.conf"), "r") as f:
            content = f.read()
            self.assertIn("linux /vmlinuz-kairos", content)
            self.assertIn("initrd /initramfs-kairos.img", content)
            self.assertIn("kairos.mode=normal", content)
            self.assertIn("efi=runtime", content)

        # Fallback entry
        with open(os.path.join(entries_dir, "kairos-fallback.conf"), "r") as f:
            content = f.read()
            self.assertIn("initrd /initramfs-kairos-fallback.img", content)
            self.assertIn("kairos.mode=fallback", content)
            self.assertIn("nomodeset", content)

        # Recovery entry
        with open(os.path.join(entries_dir, "kairos-recovery.conf"), "r") as f:
            content = f.read()
            self.assertIn("single", content)
            self.assertIn("emergency", content)
            self.assertIn("kairos.mode=recovery", content)

        # Diag entry
        with open(os.path.join(entries_dir, "kairos-diag.conf"), "r") as f:
            content = f.read()
            self.assertIn("kairos.mode=diag", content)

    def test_boot_directory_tree_in_rootfs(self):
        """Verify target rootfs boot directory tree structure."""
        boot_dir = os.path.join(self.root_dir, "build/rootfs/boot")
        self.assertTrue(os.path.exists(os.path.join(boot_dir, "loader/loader.conf")))
        self.assertTrue(os.path.exists(os.path.join(boot_dir, "loader/entries/kairos.conf")))
        self.assertTrue(os.path.exists(os.path.join(boot_dir, "grub/grub.cfg")))
        self.assertTrue(os.path.exists(os.path.join(boot_dir, "efi/EFI/BOOT")))
        self.assertTrue(os.path.exists(os.path.join(boot_dir, "efi/EFI/kairos")))

    def test_kernel_and_initramfs_artifacts(self):
        """Verify compiled kernel and both normal and fallback initramfs images exist and are non-empty."""
        kernel = os.path.join(self.root_dir, "build/rootfs/boot/vmlinuz-kairos")
        initrd_normal = os.path.join(self.root_dir, "build/rootfs/boot/initramfs-kairos.img")
        initrd_fallback = os.path.join(self.root_dir, "build/rootfs/boot/initramfs-kairos-fallback.img")

        self.assertTrue(os.path.exists(kernel) and os.path.getsize(kernel) > 1000000, "Kernel missing or too small")
        self.assertTrue(os.path.exists(initrd_normal) and os.path.getsize(initrd_normal) > 100000, "Normal initrd missing or too small")
        self.assertTrue(os.path.exists(initrd_fallback) and os.path.getsize(initrd_fallback) > 100000, "Fallback initrd missing or too small")

    def test_kairos_boot_diagnostic_cli(self):
        """Verify kairos CLI has boot diagnostics support."""
        kairos_bin = os.path.join(self.root_dir, "build/rootfs/usr/bin/kairos")
        self.assertTrue(os.path.exists(kairos_bin), "usr/bin/kairos missing in rootfs")
        with open(kairos_bin, "r", encoding="utf-8") as f:
            content = f.read()
            self.assertIn("boot_diagnostics", content)
            self.assertIn("KAIROS Adaptive Trading Operating System", content)
            self.assertIn("efivars", content)

if __name__ == "__main__":
    unittest.main()
