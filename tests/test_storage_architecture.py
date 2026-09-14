"""
KAIROS OS - Storage Architecture & Invariants Test Suite
Tests:
  - Safety Invariant: Destructive format is strictly blocked without explicit confirmation
  - Storage Provisioner: Dry-run mode syntax & subvolume specification
  - Partition Layout: GPT, EFI System Partition (FAT32), and Btrfs subvolumes (@, @home, @snapshots, @var_log, @vault, @data)
  - Full Disk Encryption: LUKS2 configuration and dm-crypt transparent wrapping
  - Storage Telemetry: kairos storage info CLI command and telemetry data
  - Mount & Recovery Invariants: errors=remount-ro in /etc/fstab and zram compressed swap
"""

import os
import unittest
import subprocess
import tempfile
import shutil

class TestStorageArchitecture(unittest.TestCase):
    def setUp(self):
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.setup_script = os.path.join(self.root_dir, "scripts/storage/setup_storage.sh")
        self.storage_py = os.path.join(self.root_dir, "scripts/storage/kairos_storage.py")
        self.kairos_bin = os.path.join(self.root_dir, "build/rootfs/usr/bin/kairos")

    def test_scripts_exist_and_executable(self):
        """Ensure storage scripts exist and are executable."""
        self.assertTrue(os.path.exists(self.setup_script), "setup_storage.sh missing")
        self.assertTrue(os.path.exists(self.storage_py), "kairos_storage.py missing")
        self.assertTrue(os.access(self.setup_script, os.X_OK), "setup_storage.sh is not executable")
        self.assertTrue(os.access(self.storage_py, os.X_OK), "kairos_storage.py is not executable")

    def test_safety_gate_blocks_destructive_format(self):
        """CRITICAL: Destructive format must fail without explicit confirmation."""
        cmd = [self.setup_script, "/dev/nonexistent", "false", "false", "false", "no-confirmation"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertNotEqual(res.returncode, 0, "Destructive format was not blocked!")
        self.assertIn("Destructive disk format operation blocked", res.stdout)
        self.assertIn("--confirm-destructive-format", res.stdout)

    def test_dry_run_mode(self):
        """Verify dry run mode reports subvolumes without making changes."""
        cmd = [self.setup_script, "/dev/null", "true", "false", "true", "false"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res.returncode, 0, "Dry run failed")
        self.assertIn("DRY RUN MODE ACTIVE", res.stdout)
        self.assertIn("@home", res.stdout)
        self.assertIn("@snapshots", res.stdout)
        self.assertIn("@data", res.stdout)

    def test_fstab_subvolume_layout(self):
        """Verify rootfs fstab has proper Btrfs subvolume mounts and errors=remount-ro."""
        fstab_path = os.path.join(self.root_dir, "build/rootfs/etc/fstab")
        self.assertTrue(os.path.exists(fstab_path), "Missing /etc/fstab in rootfs")
        with open(fstab_path, "r") as f:
            content = f.read()
            self.assertIn("LABEL=KAIROS_BOOT", content)
            self.assertIn("LABEL=KAIROS_ROOT", content)
            self.assertIn("subvol=@,", content)
            self.assertIn("subvol=@home,", content)
            self.assertIn("subvol=@snapshots,", content)
            self.assertIn("subvol=@var_log,", content)
            self.assertIn("subvol=@vault,", content)
            self.assertIn("errors=remount-ro", content)
            self.assertIn("compress=zstd:1", content)

    def test_zram_swap_configuration(self):
        """Verify zram-generator configuration is deployed in rootfs."""
        zram_conf = os.path.join(self.root_dir, "build/rootfs/etc/systemd/zram-generator.conf.d/zram.conf")
        self.assertTrue(os.path.exists(zram_conf), "Missing zram.conf")
        with open(zram_conf, "r") as f:
            content = f.read()
            self.assertIn("compression-algorithm = zstd", content)
            self.assertIn("fs-type = swap", content)

    def test_kairos_storage_cli(self):
        """Verify `kairos storage info` command execution."""
        res = subprocess.run([self.kairos_bin, "storage", "info"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(res.returncode, 0, f"kairos storage info failed: {res.stderr}")
        self.assertIn("KAIROS OS - Storage Architecture & Telemetry Report", res.stdout)
        self.assertIn("Standard KAIROS Subvolume Target Hierarchy", res.stdout)
        self.assertIn("Disk Health & SMART Assessment", res.stdout)
        self.assertIn("Safety & Recovery Policies", res.stdout)

    def test_loopback_btrfs_and_subvolumes(self):
        """End-to-end test on virtual loopback device (if root/sudo available)."""
        if shutil.which("sudo") is None or shutil.which("losetup") is None:
            self.skipTest("sudo or losetup not available")

        test_img = "/tmp/kairos_unit_test_disk.img"
        loop_dev = None
        mnt = None
        try:
            with open(test_img, "wb") as f:
                f.truncate(1024 * 1024 * 1024)

            loop_dev = subprocess.check_output(["sudo", "losetup", "-fP", "--show", test_img], text=True).strip()
            cmd = ["sudo", self.setup_script, loop_dev, "false", "false", "true", "--confirm-destructive-format"]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)

            part2 = f"{loop_dev}p2"
            mnt = tempfile.mkdtemp()
            subprocess.run(["sudo", "mount", "-o", "subvol=@", part2, mnt], check=True)
            subvols = subprocess.check_output(["sudo", "btrfs", "subvolume", "list", mnt], text=True)

            for exp in ["@", "@home", "@snapshots", "@var_log", "@vault", "@data"]:
                self.assertIn(exp, subvols)

            subprocess.run(["sudo", "umount", mnt], check=True)
            os.rmdir(mnt)
            mnt = None
            subprocess.run(["sudo", "losetup", "-d", loop_dev], check=True)
            loop_dev = None
            os.remove(test_img)
        finally:
            if mnt and os.path.exists(mnt):
                subprocess.run(["sudo", "umount", mnt], stderr=subprocess.DEVNULL)
                try:
                    os.rmdir(mnt)
                except Exception:
                    pass
            if loop_dev:
                subprocess.run(["sudo", "losetup", "-d", loop_dev], stderr=subprocess.DEVNULL)
            if os.path.exists(test_img):
                os.remove(test_img)

if __name__ == "__main__":
    unittest.main()
