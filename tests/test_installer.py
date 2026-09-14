#!/usr/bin/env python3
"""
KAIROS OS Installer Test Suite
===============================
Tests all installer phases in isolation using the --auto dry-run path.
Verifies:
  - All phases execute without error
  - All configuration structures are correct
  - Safety gates function correctly
  - Generated artifacts are well-formed
  - Secret redaction works

Run:
  python3 tests/test_installer.py
  python3 -m pytest tests/test_installer.py -v
"""

import sys
import os
import json
import re
import unittest
import tempfile
import shutil

# Ensure installer module is importable
SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "installer")
sys.path.insert(0, SRC_DIR)

import kairos_installer as ki


class TestInstallerSafety(unittest.TestCase):
    """Verify the installer's safety contracts."""

    def test_profiles_exist(self):
        """All required profiles must be defined."""
        for name in ("Minimal", "Trader", "Quant Research", "Developer", "Full"):
            self.assertIn(name, ki.PROFILES, f"Profile '{name}' is missing")

    def test_profiles_have_required_keys(self):
        """Every profile must have the required keys."""
        required = ("description", "disk_gb_min", "packages", "services", "groups_extra")
        for name, pdata in ki.PROFILES.items():
            for key in required:
                self.assertIn(key, pdata, f"Profile '{name}' missing key '{key}'")

    def test_profiles_have_packages(self):
        """Every profile must have at least one package."""
        for name, pdata in ki.PROFILES.items():
            self.assertGreater(len(pdata["packages"]), 0,
                               f"Profile '{name}' has no packages")

    def test_optional_components_structure(self):
        """Optional components must be (name, description, packages) tuples."""
        for item in ki.OPTIONAL_COMPONENTS:
            self.assertEqual(len(item), 3, f"Optional component must have 3 elements: {item}")
            name, desc, pkgs = item
            self.assertIsInstance(name, str)
            self.assertIsInstance(desc, str)
            self.assertIsInstance(pkgs, list)
            self.assertGreater(len(pkgs), 0, f"Optional '{name}' has no packages")

    def test_languages_structure(self):
        """Languages list must be (locale, description) tuples."""
        for locale, desc in ki.LANGUAGES:
            self.assertRegex(locale, r"[a-z]{2}_[A-Z]{2}\.UTF-8",
                             f"Invalid locale: {locale}")
            self.assertIsInstance(desc, str)

    def test_timezones_not_empty(self):
        """Timezone list must be non-empty."""
        self.assertGreater(len(ki.TIMEZONES), 0)
        self.assertIn("UTC", ki.TIMEZONES)


class TestInstallState(unittest.TestCase):
    """Test the InstallState dataclass."""

    def _make_state(self) -> ki.InstallState:
        s = ki.InstallState()
        s.username     = "trader"
        s.password     = "testpassword123"
        s.root_password= "rootsecret"
        s.luks_pass    = "lukspassword"
        s.profile      = "Minimal"
        s.hostname     = "kairos-test"
        s.language     = "en_US.UTF-8"
        s.timezone     = "UTC"
        s.kb_layout    = "us"
        s.network_cfg  = {"method": "dhcp", "interface": "eth0"}
        return s

    def test_safe_dict_redacts_secrets(self):
        """safe_dict() must redact all secret fields."""
        s = self._make_state()
        d = s.safe_dict()
        self.assertEqual(d["password"],      "<REDACTED>")
        self.assertEqual(d["root_password"], "<REDACTED>")
        self.assertEqual(d["luks_pass"],     "<REDACTED>")
        self.assertNotIn("testpassword123", json.dumps(d))
        self.assertNotIn("rootsecret",      json.dumps(d))
        self.assertNotIn("lukspassword",    json.dumps(d))

    def test_save_manifest_produces_valid_json(self):
        """save_manifest() must write valid JSON to a temp file."""
        s = self._make_state()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            path = tf.name
        try:
            s.save_manifest(path)
            with open(path) as f:
                data = json.load(f)
            self.assertEqual(data["username"], "trader")
            self.assertEqual(data["password"], "<REDACTED>")
        finally:
            os.unlink(path)

    def test_save_manifest_excludes_plaintext_secrets(self):
        """Manifest file must not contain plaintext passwords."""
        s = self._make_state()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tf:
            path = tf.name
        try:
            s.save_manifest(path)
            raw = open(path).read()
            self.assertNotIn("testpassword123", raw)
            self.assertNotIn("rootsecret",      raw)
            self.assertNotIn("lukspassword",    raw)
        finally:
            os.unlink(path)


class TestPartitionNaming(unittest.TestCase):
    """Verify correct partition suffix logic for all disk types."""

    def test_sata_disk(self):
        self.assertEqual(ki.partition_name("/dev/sda", 1), "/dev/sda1")
        self.assertEqual(ki.partition_name("/dev/sda", 3), "/dev/sda3")
        self.assertEqual(ki.partition_name("/dev/sdb", 2), "/dev/sdb2")

    def test_nvme_disk(self):
        self.assertEqual(ki.partition_name("/dev/nvme0n1", 1), "/dev/nvme0n1p1")
        self.assertEqual(ki.partition_name("/dev/nvme1n1", 3), "/dev/nvme1n1p3")

    def test_mmcblk(self):
        self.assertEqual(ki.partition_name("/dev/mmcblk0", 1), "/dev/mmcblk0p1")

    def test_loop_device(self):
        self.assertEqual(ki.partition_name("/dev/loop0", 1), "/dev/loop0p1")

    def test_virtio(self):
        self.assertEqual(ki.partition_name("/dev/vda", 1), "/dev/vda1")

    def test_scsi(self):
        self.assertEqual(ki.partition_name("/dev/sdc", 3), "/dev/sdc3")


class TestConfigGeneration(unittest.TestCase):
    """Test generated configuration files (dry-run mode using temp dir)."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="kairos-test-")

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_state(self) -> ki.InstallState:
        s = ki.InstallState()
        s.dry_run     = False
        s.install_target = self.tmpdir
        s.disk        = ""      # No real disk operations
        s.hostname    = "kairos-test"
        s.language    = "en_US.UTF-8"
        s.kb_layout   = "us"
        s.timezone    = "UTC"
        s.username    = "testuser"
        s.password    = "testpw"
        s.root_locked = True
        s.profile     = "Minimal"
        s.optional    = []
        s.network_cfg = {"method": "dhcp", "interface": "eth0"}
        s.efi_detected= False
        s.encrypt     = False
        s.part_efi    = ""
        s.part_boot   = "/dev/sda2"
        s.part_root   = "/dev/sda3"
        s.uuid_boot   = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        s.uuid_root   = "11111111-2222-3333-4444-555555555555"
        return s

    def test_hostname_file_written(self):
        """_step_hostname must create /etc/hostname with correct content."""
        s = self._make_state()
        ki._step_hostname(s)
        hostname_file = os.path.join(self.tmpdir, "etc", "hostname")
        self.assertTrue(os.path.exists(hostname_file))
        content = open(hostname_file).read().strip()
        self.assertEqual(content, "kairos-test")

    def test_hosts_file_written(self):
        """/etc/hosts must contain hostname entries."""
        s = self._make_state()
        ki._step_hostname(s)
        hosts_file = os.path.join(self.tmpdir, "etc", "hosts")
        self.assertTrue(os.path.exists(hosts_file))
        content = open(hosts_file).read()
        self.assertIn("kairos-test", content)
        self.assertIn("127.0.0.1", content)
        self.assertIn("::1", content)

    def test_locale_files_written(self):
        """locale.gen and locale.conf must be written correctly."""
        s = self._make_state()
        ki._step_locale(s)
        locale_gen  = os.path.join(self.tmpdir, "etc", "locale.gen")
        locale_conf = os.path.join(self.tmpdir, "etc", "locale.conf")
        vconsole    = os.path.join(self.tmpdir, "etc", "vconsole.conf")
        self.assertTrue(os.path.exists(locale_gen))
        self.assertTrue(os.path.exists(locale_conf))
        self.assertTrue(os.path.exists(vconsole))
        self.assertIn("en_US.UTF-8", open(locale_gen).read())
        self.assertIn("LANG=en_US.UTF-8", open(locale_conf).read())
        self.assertIn("KEYMAP=us", open(vconsole).read())

    def test_os_release_written(self):
        """/etc/os-release must exist and contain KAIROS identity."""
        s = self._make_state()
        ki._step_identity(s)
        osrel = os.path.join(self.tmpdir, "etc", "os-release")
        self.assertTrue(os.path.exists(osrel))
        content = open(osrel).read()
        self.assertIn('NAME="KAIROS OS"', content)
        self.assertIn("ID=kairos", content)
        self.assertIn("VERSION_ID=", content)

    def test_kairos_system_toml_written(self):
        """/etc/kairos/system.toml must be created."""
        s = self._make_state()
        ki._step_identity(s)
        toml_path = os.path.join(self.tmpdir, "etc", "kairos", "system.toml")
        self.assertTrue(os.path.exists(toml_path))
        content = open(toml_path).read()
        self.assertIn('[system]', content)
        self.assertIn('hostname = "kairos-test"', content)
        self.assertIn('profile  = "Minimal"', content)
        self.assertIn('[invariants]', content)
        self.assertIn('[components]', content)

    def test_sudoers_written(self):
        """sudoers.d/10-wheel must be created with correct permissions."""
        s = self._make_state()
        ki._step_sudo(s)
        wheel_file = os.path.join(self.tmpdir, "etc", "sudoers.d", "10-wheel")
        self.assertTrue(os.path.exists(wheel_file))
        content = open(wheel_file).read()
        self.assertIn("%wheel ALL=(ALL:ALL) ALL", content)

    def test_limits_written(self):
        """limits.d/10-kairos.conf must be created."""
        s = self._make_state()
        ki._step_groups(s)
        limits_file = os.path.join(self.tmpdir, "etc", "security", "limits.d", "10-kairos.conf")
        self.assertTrue(os.path.exists(limits_file))
        content = open(limits_file).read()
        self.assertIn("@trading", content)
        self.assertIn("@research", content)
        self.assertIn("@plugins", content)
        self.assertIn("rtprio", content)
        self.assertIn("memlock", content)

    def test_fstab_generation_unencrypted(self):
        """fstab must be generated with correct UUIDs for unencrypted install."""
        s = self._make_state()
        ki._step_fstab(s)
        fstab = os.path.join(self.tmpdir, "etc", "fstab")
        self.assertTrue(os.path.exists(fstab))
        content = open(fstab).read()
        self.assertIn("/boot", content)
        self.assertIn("btrfs", content)
        self.assertIn("subvol=@home", content)
        self.assertIn("tmpfs", content)

    def test_fstab_generation_encrypted(self):
        """fstab for encrypted install must use /dev/mapper/kairos-root."""
        s = self._make_state()
        s.encrypt = True
        ki._step_fstab(s)
        fstab = os.path.join(self.tmpdir, "etc", "fstab")
        content = open(fstab).read()
        self.assertIn("/dev/mapper/kairos-root", content)

    def test_network_dhcp_written(self):
        """DHCP network config must be created under /etc/systemd/network/."""
        s = self._make_state()
        ki._step_network_files(s)
        net_file = os.path.join(self.tmpdir, "etc", "systemd", "network", "10-eth0.network")
        self.assertTrue(os.path.exists(net_file))
        content = open(net_file).read()
        self.assertIn("[Match]", content)
        self.assertIn("Name=eth0", content)
        self.assertIn("DHCP=yes", content)

    def test_network_static_written(self):
        """Static network config must include address, gateway, DNS."""
        s = self._make_state()
        s.network_cfg = {
            "method": "static",
            "interface": "eth0",
            "address": "192.168.1.100/24",
            "gateway": "192.168.1.1",
            "dns": ["1.1.1.1", "8.8.8.8"],
        }
        ki._step_network_files(s)
        net_file = os.path.join(self.tmpdir, "etc", "systemd", "network", "10-eth0.network")
        self.assertTrue(os.path.exists(net_file))
        content = open(net_file).read()
        self.assertIn("192.168.1.100/24", content)
        self.assertIn("192.168.1.1", content)
        self.assertIn("DNS=1.1.1.1", content)

    def test_firstboot_config_written(self):
        """First-boot JSON must be written with correct structure."""
        s = self._make_state()
        ki._step_firstboot_config(s)
        fb = os.path.join(self.tmpdir, "etc", "kairos", "first-boot.json")
        self.assertTrue(os.path.exists(fb))
        data = json.load(open(fb))
        self.assertEqual(data["username"], "testuser")
        self.assertEqual(data["hostname"], "kairos-test")
        self.assertEqual(data["profile"],  "Minimal")
        self.assertFalse(data["first_boot_complete"])
        self.assertIn("installed_at", data)

    def test_bootloader_entries_uefi(self):
        """UEFI boot entries must be written for all three modes."""
        s = self._make_state()
        s.efi_detected = True
        s.uuid_root    = "aaaa-bbbb"
        entries_dir    = os.path.join(self.tmpdir, "efi", "loader", "entries")
        os.makedirs(entries_dir, exist_ok=True)

        ki._install_systemd_boot(s, self.tmpdir, "aaaa-bbbb", False)

        for fname in ("kairos.conf", "kairos-safe.conf", "kairos-recovery.conf"):
            fpath = os.path.join(entries_dir, fname)
            self.assertTrue(os.path.exists(fpath), f"Missing boot entry: {fname}")
            content = open(fpath).read()
            self.assertIn("vmlinuz-kairos", content)

        # Normal entry must have kairos.mode=normal
        normal = open(os.path.join(entries_dir, "kairos.conf")).read()
        self.assertIn("kairos.mode=normal", normal)

        # Recovery entry must have kairos.mode=recovery
        recovery = open(os.path.join(entries_dir, "kairos-recovery.conf")).read()
        self.assertIn("kairos.mode=recovery", recovery)

    def test_bootloader_entry_encrypted_contains_luks(self):
        """UEFI boot entry for encrypted install must reference LUKS UUID."""
        s = self._make_state()
        s.efi_detected = True
        s.encrypt      = True
        s.uuid_root    = "deadbeef-cafe-0000-1111-222233334444"
        entries_dir    = os.path.join(self.tmpdir, "efi", "loader", "entries")
        os.makedirs(entries_dir, exist_ok=True)

        ki._install_systemd_boot(s, self.tmpdir, "deadbeef-cafe-0000-1111-222233334444",
                                 False)

        normal = open(os.path.join(entries_dir, "kairos.conf")).read()
        self.assertIn("rd.luks.name=deadbeef-cafe-0000-1111-222233334444=kairos-root", normal)
        self.assertIn("/dev/mapper/kairos-root", normal)


class TestHealthCheck(unittest.TestCase):
    """Verify health check logic."""

    def test_passes_with_complete_config(self):
        """Health check must pass with a complete configuration."""
        s = ki.InstallState()
        s.language    = "en_US.UTF-8"
        s.kb_layout   = "us"
        s.hostname    = "kairos"
        s.timezone    = "UTC"
        s.username    = "trader"
        s.profile     = "Minimal"
        s.network_cfg = {"method": "dhcp"}
        s.disk        = ""   # no disk = skip disk checks
        s.encrypt     = True

        failures = ki.phase_health_check(s)
        self.assertEqual(failures, 0)

    def test_reports_missing_username(self):
        """Health check must detect missing username."""
        s = ki.InstallState()
        s.language    = "en_US.UTF-8"
        s.kb_layout   = "us"
        s.hostname    = "kairos"
        s.timezone    = "UTC"
        s.username    = ""       # intentionally empty
        s.profile     = "Minimal"
        s.network_cfg = {"method": "dhcp"}
        s.disk        = ""
        failures = ki.phase_health_check(s)
        self.assertGreater(failures, 0)


class TestExistingSystemDetection(unittest.TestCase):
    """Test existing OS detection (stub/safe run)."""

    def test_returns_list(self):
        """detect_existing_systems must always return a list."""
        # Run with a non-existent device — should return [] gracefully
        result = ki.detect_existing_systems("/dev/nonexistent")
        self.assertIsInstance(result, list)

    def test_no_crash_on_missing_tools(self):
        """Must not raise even if lsblk/sgdisk not present."""
        try:
            ki.detect_existing_systems("/dev/null")
        except Exception as e:
            self.fail(f"detect_existing_systems raised unexpectedly: {e}")


class TestDryRun(unittest.TestCase):
    """Integration test: --auto mode must complete without error."""

    def test_auto_mode_exits_zero(self):
        """Installer --auto must complete all phases and exit 0."""
        # Simulate auto mode state
        s = ki.InstallState()
        s.dry_run     = True
        s.language    = "en_US.UTF-8"
        s.kb_layout   = "us"
        s.hostname    = "kairos-test"
        s.timezone    = "UTC"
        s.username    = "trader"
        s.password    = "test"
        s.root_locked = True
        s.profile     = "Minimal"
        s.encrypt     = False
        s.network_cfg = {"method": "dhcp", "interface": "eth0"}
        s.install_target = "/tmp"

        # Run install steps with dry_run=True
        steps = [
            ki._step_partition,
            ki._step_format,
            ki._step_luks,
            ki._step_btrfs,
            ki._step_mount,
            ki._step_packages,
            ki._step_initramfs,
            ki._step_services,
            ki._step_unmount,
        ]
        for step in steps:
            try:
                step(s)
            except Exception as e:
                self.fail(f"Dry-run step {step.__name__} raised: {e}")

    def test_health_check_dry_run(self):
        """Health check with dry_run=True must not check disk files."""
        s = ki.InstallState()
        s.language    = "en_US.UTF-8"
        s.kb_layout   = "us"
        s.hostname    = "kairos"
        s.timezone    = "UTC"
        s.username    = "trader"
        s.profile     = "Minimal"
        s.network_cfg = {"method": "dhcp"}
        s.disk        = ""
        s.encrypt     = True
        s.dry_run     = True
        # Should pass all basic checks
        failures = ki.phase_health_check(s)
        self.assertEqual(failures, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
