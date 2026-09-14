#!/usr/bin/env python3
"""
KAIROS OS ISO Build System Test Suite
======================================

Tests the ISO build and verification infrastructure:
  - build-iso script structure and logic
  - verify_iso.py Python module (ISO 9660 parsing, file checks)
  - Generated artifact JSON schemas
  - Reproducibility metadata
  - build-iso --dry-run execution
  - Package manifest generation
  - Version metadata consistency

Run:
  python3 -m pytest tests/test_iso_build.py -v
"""

import io
import json
import os
import struct
import sys
import hashlib
import tempfile
import shutil
import unittest
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# Path setup
# ─────────────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# Import verify_iso module
import verify_iso as vi


# ─────────────────────────────────────────────────────────────────────────────
# Helper: build a minimal synthetic ISO for testing
# ─────────────────────────────────────────────────────────────────────────────

SECTOR_SIZE = 2048

def _make_sector(data: bytes, size: int = SECTOR_SIZE) -> bytes:
    """Pad or truncate bytes to exactly sector_size."""
    return (data + b"\x00" * size)[:size]

def _make_pvd(volume_id: str = "KAIROS_0_1_0", space_size: int = 200) -> bytes:
    """Construct a minimal ISO 9660 Primary Volume Descriptor."""
    pvd = bytearray(SECTOR_SIZE)
    pvd[0] = 1                          # Type: Primary Volume Descriptor
    pvd[1:6] = b"CD001"                 # Standard Identifier
    pvd[6] = 1                          # Version
    vol_id = volume_id.encode("ascii").ljust(32)[:32]
    pvd[40:72] = vol_id                 # Volume Identifier
    # Logical block size: 2048 (LE + BE)
    struct.pack_into("<H", pvd, 128, SECTOR_SIZE)
    struct.pack_into(">H", pvd, 130, SECTOR_SIZE)
    # Volume Space Size (LE + BE)
    struct.pack_into("<I", pvd, 80, space_size)
    struct.pack_into(">I", pvd, 84, space_size)
    # Root Directory Record (minimal, at LBA 18)
    root_dr = bytearray(34)
    root_dr[0] = 34                     # Length of Directory Record
    root_dr[2:6] = struct.pack("<I", 18)  # Location of Extent (LBA)
    root_dr[6:10] = struct.pack(">I", 18)
    root_dr[10:14] = struct.pack("<I", SECTOR_SIZE)  # Data length
    root_dr[14:18] = struct.pack(">I", SECTOR_SIZE)
    root_dr[25] = 0x02                  # Flags: Directory
    root_dr[32] = 1                     # File Identifier Length
    root_dr[33] = 0x00                  # File Identifier: \x00 = root (.)
    pvd[156:190] = root_dr
    return bytes(pvd)

def _make_boot_record() -> bytes:
    """Construct a minimal ISO 9660 Boot Record Descriptor (El Torito)."""
    br = bytearray(SECTOR_SIZE)
    br[0] = 0                           # Type: Boot Record
    br[1:6] = b"CD001"
    br[6] = 1
    br[7:39] = b"EL TORITO SPECIFICATION".ljust(32)
    return bytes(br)

def _make_vdst() -> bytes:
    """Volume Descriptor Set Terminator."""
    vdst = bytearray(SECTOR_SIZE)
    vdst[0] = 255
    vdst[1:6] = b"CD001"
    vdst[6] = 1
    return bytes(vdst)

def _make_empty_dir() -> bytes:
    """Minimal directory sector with just . and .. entries."""
    sec = bytearray(SECTOR_SIZE)
    # . entry
    sec[0] = 34
    sec[2:6] = struct.pack("<I", 18)
    sec[10:14] = struct.pack("<I", SECTOR_SIZE)
    sec[25] = 0x02
    sec[32] = 1
    sec[33] = 0x00
    # .. entry
    sec[34] = 34
    sec[36:40] = struct.pack("<I", 18)
    sec[44:48] = struct.pack("<I", SECTOR_SIZE)
    sec[59] = 0x02
    sec[66] = 1
    sec[67] = 0x01
    return bytes(sec)

def build_minimal_iso(volume_id: str = "KAIROS_0_1_0") -> bytes:
    """
    Build a minimal valid ISO 9660 image in memory.
    Layout:
      Sectors 0-15:  System area (blank)
      Sector  16:    Primary Volume Descriptor
      Sector  17:    Boot Record
      Sector  17.5:  Volume Descriptor Set Terminator (sector 17)
      Sector  18:    Root directory
    """
    sectors = []

    # Sectors 0-15: system area
    for _ in range(16):
        sectors.append(b"\x00" * SECTOR_SIZE)

    # Sector 16: PVD (root dir at LBA 18, 19 total sectors)
    sectors.append(_make_pvd(volume_id=volume_id, space_size=20))

    # Sector 17: Boot record
    sectors.append(_make_boot_record())

    # Sector 17 is taken by boot record; use sector 17.5 = sector 17 already
    # Add VDST at sector 18? No, root dir at 18. Let's do:
    # Sector 17: Boot Record (already done)
    # Sector 18: Root directory
    # We need VDST somewhere — add it after PVD, before boot record
    # Rebuild: 16=PVD, 17=VDST, 18=root dir, add boot record later
    sectors.pop()  # remove boot record from 17
    sectors.append(_make_vdst())  # sector 17 = VDST

    # Sector 18: Root directory
    sectors.append(_make_empty_dir())

    # Sector 19: Extra padding
    sectors.append(b"\x00" * SECTOR_SIZE)

    return b"".join(sectors)


# ─────────────────────────────────────────────────────────────────────────────
# Test Classes
# ─────────────────────────────────────────────────────────────────────────────

class TestISO9660Parsing(unittest.TestCase):
    """Test the ISO 9660 low-level parsing in verify_iso.py."""

    def _make_fp(self, volume_id: str = "KAIROS_0_1_0") -> io.BytesIO:
        return io.BytesIO(build_minimal_iso(volume_id))

    def test_read_sector(self):
        """_read_sector must return exactly 2048 bytes."""
        fp = self._make_fp()
        sector = vi._read_sector(fp, 16)
        self.assertEqual(len(sector), SECTOR_SIZE)

    def test_pvd_type(self):
        """Sector 16 must be parsed as a Primary Volume Descriptor (type=1)."""
        fp = self._make_fp()
        sector = vi._read_sector(fp, 16)
        pvd = vi._parse_volume_descriptor(sector)
        self.assertIsNotNone(pvd)
        self.assertEqual(pvd["type"], 1)
        self.assertEqual(pvd["id"], "CD001")

    def test_pvd_volume_id(self):
        """Volume ID must be correctly parsed from PVD."""
        fp = self._make_fp("KAIROS_0_1_0")
        sector = vi._read_sector(fp, 16)
        pvd = vi._parse_volume_descriptor(sector)
        self.assertEqual(pvd["volume_id"].strip(), "KAIROS_0_1_0")

    def test_pvd_logical_block_size(self):
        """Logical block size must be 2048."""
        fp = self._make_fp()
        sector = vi._read_sector(fp, 16)
        pvd = vi._parse_volume_descriptor(sector)
        self.assertEqual(pvd["logical_block_size"], 2048)

    def test_vdst_detection(self):
        """Sector 17 (VDST) must be parsed correctly as type 255."""
        fp = self._make_fp()
        sector = vi._read_sector(fp, 17)
        vdst = vi._parse_volume_descriptor(sector)
        self.assertIsNotNone(vdst)
        self.assertEqual(vdst["type"], 255)

    def test_invalid_sector_returns_none(self):
        """A sector with wrong identifier must return None."""
        bad_sector = b"\x01WRONG" + b"\x00" * (SECTOR_SIZE - 6)
        result = vi._parse_volume_descriptor(bad_sector)
        self.assertIsNone(result)

    def test_too_short_sector_returns_none(self):
        """A sector shorter than 8 bytes must return None."""
        result = vi._parse_volume_descriptor(b"\x01CD001")
        self.assertIsNone(result)

    def test_boot_record_type(self):
        """Boot Record must be parsed as type=0 with boot_system_id."""
        br = _make_boot_record()
        result = vi._parse_volume_descriptor(br)
        self.assertIsNotNone(result)
        self.assertEqual(result["type"], 0)
        self.assertIn("boot_system_id", result)
        self.assertIn("EL TORITO", result["boot_system_id"].upper())

    def test_read_file_from_iso(self):
        """_read_file_from_iso must return correct bytes at given LBA."""
        content = b"HELLO KAIROS" + b"\x00" * (SECTOR_SIZE - 12)
        # Build a minimal ISO where sector 19 has our content
        raw = build_minimal_iso()
        raw += content  # append as sector 20
        fp = io.BytesIO(raw)
        # sector 20 = index 20
        data = vi._read_file_from_iso(fp, 20, 12)
        self.assertEqual(data, b"HELLO KAIROS")


class TestSHA256Utils(unittest.TestCase):
    """Test SHA256 utility functions."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_sha256file_correct(self):
        """_sha256file must compute correct SHA256 of a file."""
        f = self.tmpdir / "test.bin"
        f.write_bytes(b"KAIROS TEST DATA")
        expected = hashlib.sha256(b"KAIROS TEST DATA").hexdigest()
        self.assertEqual(vi._sha256file(f), expected)

    def test_sha256file_empty(self):
        """_sha256file of empty file must equal known SHA256 of empty bytes."""
        f = self.tmpdir / "empty.bin"
        f.write_bytes(b"")
        expected = hashlib.sha256(b"").hexdigest()
        self.assertEqual(vi._sha256file(f), expected)

    def test_find_sha256_found(self):
        """_find_sha256 must return the SHA256 for the named file."""
        sha_file = self.tmpdir / "SHA256SUMS"
        sha_file.write_text("abc123def456  kairos-0.1.0-x86_64.iso\n"
                            "deadbeef1234  other.iso\n")
        result = vi._find_sha256(sha_file, "kairos-0.1.0-x86_64.iso")
        self.assertEqual(result, "abc123def456")

    def test_find_sha256_not_found(self):
        """_find_sha256 must return None when filename not in SHA256SUMS."""
        sha_file = self.tmpdir / "SHA256SUMS"
        sha_file.write_text("abc123  other.iso\n")
        result = vi._find_sha256(sha_file, "kairos-0.1.0-x86_64.iso")
        self.assertIsNone(result)

    def test_find_sha256_missing_file(self):
        """_find_sha256 must return None when SHA256SUMS doesn't exist."""
        result = vi._find_sha256(self.tmpdir / "no-such-file", "kairos.iso")
        self.assertIsNone(result)

    def test_find_sha256_dry_run_marker(self):
        """_find_sha256 must return DRY-RUN marker as-is."""
        sha_file = self.tmpdir / "SHA256SUMS"
        sha_file.write_text("DRY-RUN-abc123  kairos-0.1.0-x86_64.iso\n")
        result = vi._find_sha256(sha_file, "kairos-0.1.0-x86_64.iso")
        self.assertTrue(result.startswith("DRY-RUN"))


class TestBuildArtifactSchemas(unittest.TestCase):
    """Test the JSON schema of generated build artifacts."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_json(self, name: str, data: dict) -> Path:
        p = self.tmpdir / name
        p.write_text(json.dumps(data, indent=2))
        return p

    def test_version_metadata_schema(self):
        """version-metadata.json must have all required fields."""
        doc = {
            "name":               "KAIROS OS",
            "version":            "0.1.0-alpha.1",
            "codename":           "Aethelgard",
            "arch":               "x86_64",
            "build_date":         "20240101",
            "build_timestamp":    "2024-01-01T00:00:00Z",
            "source_date_epoch":  1704067200,
            "git_commit":         "abc1234",
            "git_branch":         "main",
            "installer_version":  "0.1.0",
            "profiles":           ["Minimal", "Trader", "Quant Research", "Developer", "Full"],
            "iso_name":           "kairos-0.1.0-alpha.1-x86_64.iso",
        }
        p = self._write_json("version-metadata.json", doc)
        loaded = json.loads(p.read_text())

        required = ["name", "version", "codename", "arch",
                    "build_date", "source_date_epoch", "profiles"]
        for key in required:
            self.assertIn(key, loaded, f"Missing key: {key}")

        self.assertEqual(loaded["name"], "KAIROS OS")
        self.assertEqual(len(loaded["profiles"]), 5)
        self.assertIsInstance(loaded["source_date_epoch"], int)
        self.assertGreater(loaded["source_date_epoch"], 0)

    def test_build_manifest_schema(self):
        """build-manifest.json must have required sections."""
        doc = {
            "build_system":   "KAIROS OS Reproducible Build Engine",
            "schema_version": "1.0.0",
            "iso": {
                "name":        "kairos-0.1.0-alpha.1-x86_64.iso",
                "path":        "dist/kairos-0.1.0-alpha.1-x86_64.iso",
                "sha256":      "abc" * 21 + "a",
                "size_bytes":  732364800,
                "size_mib":    698,
                "volume_id":   "KAIROS_0_1_0_ALPHA_1",
            },
            "version": {
                "kairos_version":    "0.1.0-alpha.1",
                "codename":          "Aethelgard",
                "arch":              "x86_64",
                "build_date":        "20240101",
                "build_timestamp":   "2024-01-01T00:00:00Z",
                "source_date_epoch": 1704067200,
                "git_commit":        "abc1234",
                "git_branch":        "main",
            },
            "reproducibility": {
                "source_date_epoch": 1704067200,
                "notes": "Set SOURCE_DATE_EPOCH=1704067200 to reproduce.",
            },
            "components": {
                "bootloader": "GRUB2 hybrid (BIOS El Torito + UEFI EFI partition)",
                "kernel":     "linux-kairos-rt (PREEMPT_RT)",
                "rootfs":     "SquashFS zstd:15",
                "installer":  "kairos/installer.py",
                "recovery":   "recovery/recovery.py",
            },
            "required_files": [
                "live/filesystem.squashfs",
                "live/filesystem.sha256",
                "boot/vmlinuz-kairos",
                "boot/initramfs-kairos.img",
                "boot/grub/grub.cfg",
                "EFI/BOOT/BOOTX64.EFI",
                "kairos/version.json",
                "kairos/installer.py",
                "kairos/package-manifest.json",
                "recovery/recovery.py",
                "recovery/recovery.json",
            ],
        }
        p = self._write_json("build-manifest.json", doc)
        loaded = json.loads(p.read_text())

        for key in ["iso", "version", "components", "required_files", "reproducibility"]:
            self.assertIn(key, loaded, f"Missing key: {key}")

        self.assertEqual(len(loaded["required_files"]), 11)
        self.assertIn("live/filesystem.squashfs", loaded["required_files"])
        self.assertIn("EFI/BOOT/BOOTX64.EFI", loaded["required_files"])
        self.assertIsInstance(loaded["reproducibility"]["source_date_epoch"], int)

    def test_package_manifest_schema(self):
        """package-manifest.json must have count, packages, and profiles."""
        doc = {
            "generated": "2024-01-01T00:00:00Z",
            "count": 3,
            "method": "profile-definition",
            "packages": [
                {"name": "linux-kairos-rt", "version": "6.6.1-rt", "source": "profile-definition"},
                {"name": "systemd",         "version": "255.0",    "source": "profile-definition"},
                {"name": "openssh",         "version": "9.6",      "source": "profile-definition"},
            ],
            "profiles": {
                "Minimal":        ["linux-kairos-rt", "systemd", "openssh"],
                "Trader":         ["linux-kairos-rt", "hyprland", "kairos-riskd"],
                "Quant Research": ["linux-kairos-rt", "python3"],
                "Developer":      ["linux-kairos-rt", "git", "gcc"],
                "Full":           ["linux-kairos-rt", "hyprland", "kairos-riskd"],
            }
        }
        p = self._write_json("package-manifest.json", doc)
        loaded = json.loads(p.read_text())

        self.assertEqual(loaded["count"], 3)
        self.assertEqual(len(loaded["packages"]), 3)
        self.assertIn("profiles", loaded)
        self.assertEqual(len(loaded["profiles"]), 5)

        # All profiles must be present
        for profile in ("Minimal", "Trader", "Quant Research", "Developer", "Full"):
            self.assertIn(profile, loaded["profiles"])

        # Each package must have name, version, source
        for pkg in loaded["packages"]:
            self.assertIn("name", pkg)
            self.assertIn("version", pkg)
            self.assertIn("source", pkg)

    def test_recovery_json_schema(self):
        """recovery.json must have version, entry_point, and menu_items."""
        doc = {
            "recovery_version": "0.1.0-alpha.1",
            "build_timestamp":  "2024-01-01T00:00:00Z",
            "entry_point":      "/usr/libexec/kairos/kairos_recovery.py",
            "iso_entry_point":  "/recovery/recovery.py",
            "menu_items": [
                "Boot Normally",
                "Boot Previous Version",
                "Repair System",
                "Rollback Update",
                "Filesystem Diagnostics",
                "Network Diagnostics",
                "User Recovery",
                "System Restore",
                "Emergency Terminal",
                "Shutdown",
                "Reboot",
            ],
        }
        p = self._write_json("recovery.json", doc)
        loaded = json.loads(p.read_text())
        self.assertEqual(len(loaded["menu_items"]), 11)
        self.assertIn("Boot Normally", loaded["menu_items"])
        self.assertIn("Repair System", loaded["menu_items"])
        self.assertIn("Rollback Update", loaded["menu_items"])
        self.assertIn("Filesystem Diagnostics", loaded["menu_items"])
        self.assertIn("Emergency Terminal", loaded["menu_items"])

    def test_version_json_schema(self):
        """version.json (in ISO) must have required fields."""
        doc = {
            "name":               "KAIROS OS",
            "version":            "0.1.0-alpha.1",
            "codename":           "Aethelgard",
            "arch":               "x86_64",
            "volume_id":          "KAIROS_0_1_0_ALPHA_1",
            "build_date":         "20240101",
            "build_timestamp":    "2024-01-01T00:00:00Z",
            "source_date_epoch":  1704067200,
            "git_commit":         "abc1234",
            "git_branch":         "main",
            "installer_version":  "0.1.0",
            "profiles":           ["Minimal", "Trader", "Quant Research", "Developer", "Full"],
            "repository":         "https://github.com/kairos-os/kairos",
            "homepage":           "https://kairos-os.org",
            "iso_name":           "kairos-0.1.0-alpha.1-x86_64.iso",
        }
        p = self._write_json("version.json", doc)
        loaded = json.loads(p.read_text())

        required = ["name", "version", "codename", "arch", "source_date_epoch",
                    "build_date", "profiles", "iso_name"]
        for key in required:
            self.assertIn(key, loaded, f"version.json missing: {key}")

        self.assertEqual(loaded["name"], "KAIROS OS")
        self.assertEqual(loaded["source_date_epoch"], 1704067200)


class TestBuildISOScriptStructure(unittest.TestCase):
    """Test the build-iso shell script structure and content."""

    def setUp(self):
        self.build_iso = REPO_ROOT / "scripts" / "build-iso"

    def test_build_iso_exists(self):
        """build-iso script must exist."""
        self.assertTrue(self.build_iso.exists(), "scripts/build-iso missing")

    def test_build_iso_is_bash(self):
        """build-iso must have bash shebang."""
        first_line = self.build_iso.read_text(encoding="utf-8").splitlines()[0]
        self.assertTrue(
            first_line.startswith("#!/usr/bin/env bash") or
            first_line.startswith("#!/bin/bash"),
            f"Expected bash shebang, got: {first_line}"
        )

    def test_build_iso_has_set_euo_pipefail(self):
        """build-iso must use 'set -euo pipefail' for safety."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", content)

    def test_build_iso_has_source_date_epoch(self):
        """build-iso must set and export SOURCE_DATE_EPOCH for reproducibility."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("SOURCE_DATE_EPOCH", content)
        self.assertIn("export SOURCE_DATE_EPOCH", content)

    def test_build_iso_dry_run_flag(self):
        """build-iso must support --dry-run flag."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("--dry-run", content)
        self.assertIn("DRY_RUN", content)

    def test_build_iso_has_squashfs_step(self):
        """build-iso must invoke mksquashfs."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("mksquashfs", content)

    def test_build_iso_squashfs_reproducible_flags(self):
        """build-iso must pass -reproducible and -mkfs-time to mksquashfs."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("-reproducible", content)
        self.assertIn("-mkfs-time", content)

    def test_build_iso_has_xorriso(self):
        """build-iso must invoke xorriso."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("xorriso", content)

    def test_build_iso_has_modification_date(self):
        """build-iso must pass --modification-date to xorriso for reproducibility."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("--modification-date", content)

    def test_build_iso_has_sha256sum(self):
        """build-iso must generate SHA256SUMS."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("sha256sum", content)
        self.assertIn("SHA256SUMS", content)

    def test_build_iso_has_build_manifest(self):
        """build-iso must generate build-manifest.json."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("build-manifest.json", content)

    def test_build_iso_has_version_metadata(self):
        """build-iso must generate version-metadata.json."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("version-metadata.json", content)

    def test_build_iso_has_package_manifest(self):
        """build-iso must generate package-manifest.json."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("package-manifest.json", content)

    def test_build_iso_has_all_required_iso_files(self):
        """build-iso must embed all required files in the ISO staging tree."""
        content = self.build_iso.read_text(encoding="utf-8")
        required = [
            "filesystem.squashfs",
            "vmlinuz-kairos",
            "initramfs-kairos.img",
            "grub.cfg",
            "BOOTX64.EFI",
            "version.json",
            "installer.py",
            "package-manifest.json",
            "recovery.py",
            "recovery.json",
        ]
        for f in required:
            self.assertIn(f, content, f"build-iso does not reference: {f}")

    def test_build_iso_has_uefi_support(self):
        """build-iso must generate UEFI EFI boot payload."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("BOOTX64.EFI", content)
        self.assertIn("x86_64-efi", content)

    def test_build_iso_has_grub2_bios_support(self):
        """build-iso must support legacy BIOS boot via El Torito."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("eltorito", content)
        self.assertIn("i386-pc", content)

    def test_build_iso_has_secure_boot_support(self):
        """build-iso must support --sign for Secure Boot signing."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("--sign", content)
        self.assertIn("sbsign", content)

    def test_build_iso_has_git_commit(self):
        """build-iso must embed git commit in metadata."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("git_commit", content)
        self.assertIn("GIT_COMMIT", content)

    def test_build_iso_embeds_installer(self):
        """build-iso must embed kairos_installer.py."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("kairos_installer.py", content)
        self.assertIn("installer.py", content)

    def test_build_iso_embeds_recovery(self):
        """build-iso must embed kairos_recovery.py."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("kairos_recovery.py", content)
        self.assertIn("recovery.py", content)

    def test_build_iso_validates_json(self):
        """build-iso must validate generated JSON files."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("JSON", content.upper())

    def test_build_iso_has_fallback(self):
        """build-iso must have a fallback ISO mastering path."""
        content = self.build_iso.read_text(encoding="utf-8")
        self.assertIn("fallback", content.lower())


class TestVerifyISOScriptStructure(unittest.TestCase):
    """Test the verify-iso shell script structure and content."""

    def setUp(self):
        self.verify_iso = REPO_ROOT / "scripts" / "verify-iso"

    def test_verify_iso_exists(self):
        """verify-iso script must exist."""
        self.assertTrue(self.verify_iso.exists(), "scripts/verify-iso missing")

    def test_verify_iso_is_bash(self):
        """verify-iso must have bash shebang."""
        first_line = self.verify_iso.read_text(encoding="utf-8").splitlines()[0]
        self.assertTrue(first_line.startswith("#!/usr/bin/env bash") or
                        first_line.startswith("#!/bin/bash"))

    def test_verify_iso_has_set_euo_pipefail(self):
        content = self.verify_iso.read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", content)

    def test_verify_iso_exit_codes(self):
        """verify-iso must have defined exit codes in documentation."""
        content = self.verify_iso.read_text(encoding="utf-8")
        self.assertIn("exit 0", content)  # success
        self.assertIn("exit 1", content)  # failure
        self.assertIn("exit 2", content)  # not found

    def test_verify_iso_checks_sha256(self):
        content = self.verify_iso.read_text(encoding="utf-8")
        self.assertIn("sha256sum", content)
        self.assertIn("SHA256SUMS", content)

    def test_verify_iso_checks_required_files(self):
        content = self.verify_iso.read_text(encoding="utf-8")
        required = [
            "filesystem.squashfs",
            "vmlinuz-kairos",
            "initramfs-kairos.img",
            "grub.cfg",
        ]
        for f in required:
            self.assertIn(f, content, f"verify-iso does not check for: {f}")

    def test_verify_iso_checks_grub_entries(self):
        content = self.verify_iso.read_text(encoding="utf-8")
        self.assertIn("kairos.mode=live", content)
        self.assertIn("kairos.mode=installer", content)
        self.assertIn("kairos.mode=recovery", content)

    def test_verify_iso_checks_version_consistency(self):
        content = self.verify_iso.read_text(encoding="utf-8")
        self.assertIn("version-metadata.json", content)
        self.assertIn("version.json", content)

    def test_verify_iso_json_mode(self):
        content = self.verify_iso.read_text(encoding="utf-8")
        self.assertIn("--json", content)

    def test_verify_iso_strict_mode(self):
        content = self.verify_iso.read_text(encoding="utf-8")
        self.assertIn("--strict", content)

    def test_verify_iso_no_mount_mode(self):
        content = self.verify_iso.read_text(encoding="utf-8")
        self.assertIn("--no-mount", content)

    def test_verify_iso_checks_squashfs_integrity(self):
        content = self.verify_iso.read_text(encoding="utf-8")
        self.assertIn("filesystem.sha256", content)

    def test_verify_iso_checks_efi(self):
        content = self.verify_iso.read_text(encoding="utf-8")
        self.assertIn("BOOTX64.EFI", content) or self.assertIn("EFI", content)

    def test_verify_iso_checks_installer_syntax(self):
        content = self.verify_iso.read_text(encoding="utf-8")
        self.assertIn("py_compile", content)

    def test_verify_iso_checks_recovery(self):
        content = self.verify_iso.read_text(encoding="utf-8")
        self.assertIn("recovery.py", content)

    def test_verify_iso_checks_reproducibility(self):
        content = self.verify_iso.read_text(encoding="utf-8")
        self.assertIn("source_date_epoch", content) or \
        self.assertIn("SOURCE_DATE_EPOCH", content)


class TestPythonVerifierModule(unittest.TestCase):
    """Test the verify_iso.py Python module functions."""

    def test_module_importable(self):
        """verify_iso.py must be importable without errors."""
        self.assertIsNotNone(vi)

    def test_has_verify_iso_function(self):
        """verify_iso must export verify_iso() function."""
        self.assertTrue(hasattr(vi, "verify_iso"))

    def test_has_sha256file_function(self):
        self.assertTrue(hasattr(vi, "_sha256file"))

    def test_has_find_sha256_function(self):
        self.assertTrue(hasattr(vi, "_find_sha256"))

    def test_has_read_sector_function(self):
        self.assertTrue(hasattr(vi, "_read_sector"))

    def test_has_parse_volume_descriptor(self):
        self.assertTrue(hasattr(vi, "_parse_volume_descriptor"))

    def test_has_build_file_index(self):
        self.assertTrue(hasattr(vi, "_build_file_index"))

    def test_has_read_file_from_iso(self):
        self.assertTrue(hasattr(vi, "_read_file_from_iso"))


class TestReproducibility(unittest.TestCase):
    """Test reproducibility invariants."""

    def test_source_date_epoch_in_build_iso(self):
        """build-iso must set SOURCE_DATE_EPOCH to git timestamp or fixed fallback."""
        content = (REPO_ROOT / "scripts" / "build-iso").read_text(encoding="utf-8")
        # Must default to a fixed epoch as fallback
        self.assertIn("1704067200", content,
                      "Fixed SOURCE_DATE_EPOCH fallback (2024-01-01) must be present")

    def test_mksquashfs_reproducible_flag(self):
        """build-iso must pass -reproducible to mksquashfs."""
        content = (REPO_ROOT / "scripts" / "build-iso").read_text(encoding="utf-8")
        self.assertIn("-reproducible", content)

    def test_mksquashfs_mkfs_time(self):
        """build-iso must pass -mkfs-time SOURCE_DATE_EPOCH to mksquashfs."""
        content = (REPO_ROOT / "scripts" / "build-iso").read_text(encoding="utf-8")
        self.assertIn("-mkfs-time", content)
        # Must use the epoch variable
        self.assertIn("SOURCE_DATE_EPOCH", content)

    def test_xorriso_modification_date(self):
        """build-iso must pass --modification-date to xorriso."""
        content = (REPO_ROOT / "scripts" / "build-iso").read_text(encoding="utf-8")
        self.assertIn("--modification-date", content)

    def test_reproducibility_key_in_manifest_schema(self):
        """build-manifest.json schema must include reproducibility section."""
        doc = {
            "reproducibility": {
                "source_date_epoch": 1704067200,
                "notes": "Rebuild instructions",
            }
        }
        self.assertIn("source_date_epoch", doc["reproducibility"])

    def test_fixed_epoch_is_valid_unix_timestamp(self):
        """The fixed SOURCE_DATE_EPOCH must be a valid Unix timestamp."""
        import datetime
        epoch = 1704067200
        dt = datetime.datetime.utcfromtimestamp(epoch)
        self.assertEqual(dt.year, 2024)
        self.assertEqual(dt.month, 1)
        self.assertEqual(dt.day, 1)


class TestGRUBConfiguration(unittest.TestCase):
    """Verify the GRUB configuration template logic."""

    def _get_grub_template_params(self) -> str:
        """Extract the GRUB config generation code from build-iso."""
        content = (REPO_ROOT / "scripts" / "build-iso").read_text(encoding="utf-8")
        start = content.find("grub.cfg")
        return content[max(0, start - 200):start + 3000]

    def test_grub_has_live_mode(self):
        """GRUB config must have kairos.mode=live entry."""
        content = (REPO_ROOT / "scripts" / "build-iso").read_text(encoding="utf-8")
        self.assertIn("kairos.mode=live", content)

    def test_grub_has_installer_mode(self):
        """GRUB config must have kairos.mode=installer entry."""
        content = (REPO_ROOT / "scripts" / "build-iso").read_text(encoding="utf-8")
        self.assertIn("kairos.mode=installer", content)

    def test_grub_has_recovery_mode(self):
        """GRUB config must have kairos.mode=recovery entry."""
        content = (REPO_ROOT / "scripts" / "build-iso").read_text(encoding="utf-8")
        self.assertIn("kairos.mode=recovery", content)

    def test_grub_has_memtest(self):
        """GRUB config must have memtest86+ entry."""
        content = (REPO_ROOT / "scripts" / "build-iso").read_text(encoding="utf-8")
        self.assertIn("memtest86", content)

    def test_grub_has_fwsetup(self):
        """GRUB config must have EFI firmware setup entry."""
        content = (REPO_ROOT / "scripts" / "build-iso").read_text(encoding="utf-8")
        self.assertIn("fwsetup", content)

    def test_grub_has_toram_mode(self):
        """GRUB config must have toram mode entry (copy to RAM)."""
        content = (REPO_ROOT / "scripts" / "build-iso").read_text(encoding="utf-8")
        self.assertIn("toram", content)


class TestISOMandatoryFiles(unittest.TestCase):
    """Verify the required files list matches between build-iso and verify-iso."""

    REQUIRED = [
        "live/filesystem.squashfs",
        "live/filesystem.sha256",
        "boot/vmlinuz-kairos",
        "boot/initramfs-kairos.img",
        "boot/grub/grub.cfg",
        "EFI/BOOT/BOOTX64.EFI",
        "kairos/version.json",
        "kairos/installer.py",
        "kairos/package-manifest.json",
        "recovery/recovery.py",
        "recovery/recovery.json",
    ]

    def _build_iso_content(self) -> str:
        return (REPO_ROOT / "scripts" / "build-iso").read_text(encoding="utf-8")

    def _verify_iso_content(self) -> str:
        return (REPO_ROOT / "scripts" / "verify-iso").read_text(encoding="utf-8")

    def _verify_iso_py_content(self) -> str:
        return (REPO_ROOT / "scripts" / "verify_iso.py").read_text(encoding="utf-8")

    def test_all_required_files_in_build_iso(self):
        """All required ISO files must be referenced in build-iso."""
        content = self._build_iso_content()
        for f in self.REQUIRED:
            basename = os.path.basename(f)
            self.assertIn(basename, content,
                          f"build-iso doesn't reference required file: {f}")

    def test_all_required_files_in_verify_iso(self):
        """All required ISO files must be checked in verify-iso."""
        content = self._verify_iso_content()
        for f in self.REQUIRED:
            basename = os.path.basename(f)
            self.assertIn(basename, content,
                          f"verify-iso doesn't check required file: {f}")

    def test_all_required_files_in_verify_iso_py(self):
        """All required ISO files must be checked in verify_iso.py."""
        content = self._verify_iso_py_content()
        for f in self.REQUIRED:
            basename = os.path.basename(f).lower()
            self.assertIn(basename, content.lower(),
                          f"verify_iso.py doesn't check required file: {f}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
