#!/usr/bin/env python3
"""
KAIROS OS ISO Verification — Pure Python Implementation
========================================================

Cross-platform, root-free ISO verification tool.
Complements scripts/verify-iso (which requires Linux + optional root for mounting).

Verifies (without mounting or root):
  1.  ISO file existence and size
  2.  SHA256 checksum against SHA256SUMS
  3.  ISO 9660 volume ID via sector 16 inspection
  4.  ISO 9660 primary volume descriptor structure
  5.  El Torito boot record presence (BIOS bootability indicator)
  6.  Required file presence (via ISO 9660 directory traversal)
  7.  GRUB config content inspection
  8.  Installer and recovery Python syntax check (extracted in-memory)
  9.  version.json JSON validity and field completeness
  10. package-manifest.json JSON validity and package count
  11. build-manifest.json JSON validity and structure
  12. Version consistency (ISO vs. dist/)
  13. SOURCE_DATE_EPOCH reproducibility check
  14. KAIROS identity validation

Run:
  python3 scripts/verify_iso.py [path/to/kairos.iso] [options]
  python3 scripts/verify_iso.py               (auto-detect in dist/)

Options:
  --json      Output machine-readable JSON result
  --strict    Treat warnings as failures
  --quiet     Suppress per-check output
  --help

Exit codes:
  0 — All checks passed
  1 — One or more checks failed
  2 — ISO not found
"""

from __future__ import annotations

import io
import json
import os
import struct
import sys
import hashlib
import datetime
import argparse
import re
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

# ─────────────────────────────────────────────────────────────────────────────
# Result tracking
# ─────────────────────────────────────────────────────────────────────────────

PASS = 0
FAIL = 0
WARN = 0
QUIET = False
STRICT = False
CHECKS: List[Dict[str, Any]] = []


def _record(status: str, msg: str) -> None:
    CHECKS.append({"status": status, "message": msg})


def result_pass(msg: str) -> None:
    global PASS
    PASS += 1
    _record("PASS", msg)
    if not QUIET:
        print(f"  \033[32m[PASS]\033[0m  {msg}")


def result_fail(msg: str) -> None:
    global FAIL
    FAIL += 1
    _record("FAIL", msg)
    print(f"  \033[31m[FAIL]\033[0m  {msg}")


def result_warn(msg: str) -> None:
    global WARN, FAIL
    if STRICT:
        FAIL += 1
        _record("FAIL", f"(strict) {msg}")
        print(f"  \033[31m[FAIL]\033[0m  (strict) {msg}")
    else:
        WARN += 1
        _record("WARN", msg)
        if not QUIET:
            print(f"  \033[33m[WARN]\033[0m  {msg}")


def section(title: str) -> None:
    if not QUIET:
        print(f"\n  \033[1m── {title}\033[0m\n")


# ─────────────────────────────────────────────────────────────────────────────
# ISO 9660 Low-Level Parsing
# ─────────────────────────────────────────────────────────────────────────────

SECTOR_SIZE = 2048
SYSTEM_AREA_SECTORS = 16

def _read_sector(fp: io.BufferedIOBase, lba: int) -> bytes:
    """Read one 2048-byte ISO 9660 sector."""
    fp.seek(lba * SECTOR_SIZE)
    return fp.read(SECTOR_SIZE)


def _parse_volume_descriptor(sector: bytes) -> Optional[Dict[str, Any]]:
    """
    Parse an ISO 9660 Volume Descriptor from a raw sector.
    Returns dict with 'type', 'id', 'version', and type-specific fields.
    """
    if len(sector) < 8:
        return None
    vd_type    = sector[0]
    vd_id      = sector[1:6]
    vd_version = sector[6]
    if vd_id != b"CD001":
        return None
    result: Dict[str, Any] = {
        "type":    vd_type,
        "id":      vd_id.decode("ascii"),
        "version": vd_version,
    }
    if vd_type == 1:  # Primary Volume Descriptor
        result["volume_id"]         = sector[40:72].decode("ascii", errors="replace").strip()
        result["volume_set_size"]   = struct.unpack_from("<H", sector, 122)[0]
        result["volume_sequence"]   = struct.unpack_from("<H", sector, 126)[0]
        result["logical_block_size"]= struct.unpack_from("<H", sector, 128)[0]
        result["volume_space_size"] = struct.unpack_from("<I", sector, 80)[0]
        result["root_dir_lba"]      = struct.unpack_from("<I", sector, 158)[0]
        result["root_dir_size"]     = struct.unpack_from("<I", sector, 166)[0]
    elif vd_type == 0:  # Boot Record (El Torito etc.)
        result["boot_system_id"] = sector[7:39].decode("ascii", errors="replace").strip()
        result["boot_id"]        = sector[39:71].decode("ascii", errors="replace").strip()
    return result


def _read_directory(fp: io.BufferedIOBase, lba: int, size: int,
                    encoding: str = "ascii") -> List[Dict[str, Any]]:
    """
    Read ISO 9660 directory entries from a given LBA.
    Returns a list of (name, lba, size, is_dir) dicts.
    """
    entries = []
    bytes_read = 0
    fp.seek(lba * SECTOR_SIZE)

    while bytes_read < size:
        # Each record starts with length byte
        data = fp.read(1)
        if not data or data == b"\x00":
            # Skip padding to sector boundary
            pos = fp.tell()
            next_sector = ((pos + SECTOR_SIZE - 1) // SECTOR_SIZE) * SECTOR_SIZE
            if next_sector - pos < size - bytes_read:
                fp.seek(next_sector)
                bytes_read = next_sector - (lba * SECTOR_SIZE)
                continue
            else:
                break

        rec_len = data[0]
        if rec_len == 0:
            break

        record = data + fp.read(rec_len - 1)
        bytes_read += rec_len

        if len(record) < 33:
            continue

        file_lba   = struct.unpack_from("<I", record, 2)[0]
        file_size  = struct.unpack_from("<I", record, 10)[0]
        flags      = record[25]
        name_len   = record[32]
        name_bytes = record[33:33 + name_len]

        # Decode name: strip version suffix (";1")
        try:
            raw_name = name_bytes.decode(encoding, errors="replace")
        except Exception:
            raw_name = repr(name_bytes)
        name = raw_name.rstrip(";0123456789").rstrip(";").strip("\x00")

        is_dir = bool(flags & 0x02)
        if name in ("", "\x00", "\x01"):  # . and .. entries
            continue

        entries.append({
            "name":   name,
            "lba":    file_lba,
            "size":   file_size,
            "is_dir": is_dir,
        })

    return entries


def _build_file_index(fp: io.BufferedIOBase,
                      root_lba: int, root_size: int,
                      prefix: str = "") -> Dict[str, Dict[str, Any]]:
    """
    Recursively traverse ISO 9660 directory tree, building a flat index
    of path→{lba, size, is_dir}.
    Limited to 6 levels deep and 5000 entries total to avoid infinite loops.
    """
    index: Dict[str, Dict[str, Any]] = {}
    stack = [(root_lba, root_size, prefix)]
    depth_limit = 6
    total_entries = 0

    while stack and total_entries < 5000:
        lba, sz, path_prefix = stack.pop()

        try:
            entries = _read_directory(fp, lba, sz)
        except Exception:
            continue

        for entry in entries:
            rel_path = f"{path_prefix}/{entry['name']}" if path_prefix else entry["name"]
            rel_path = rel_path.lower().lstrip("/")
            index[rel_path] = {
                "lba":    entry["lba"],
                "size":   entry["size"],
                "is_dir": entry["is_dir"],
            }
            total_entries += 1
            if entry["is_dir"] and path_prefix.count("/") < depth_limit:
                stack.append((entry["lba"], entry["size"], rel_path))

    return index


def _read_file_from_iso(fp: io.BufferedIOBase, lba: int, size: int) -> bytes:
    """Read a file's raw bytes from ISO given its LBA and size."""
    fp.seek(lba * SECTOR_SIZE)
    return fp.read(size)


# ─────────────────────────────────────────────────────────────────────────────
# Main Verification Logic
# ─────────────────────────────────────────────────────────────────────────────

def verify_iso(iso_path: Path, dist_dir: Path) -> int:
    """Run all verification checks. Returns exit code."""
    global PASS, FAIL, WARN

    START = datetime.datetime.utcnow()

    # ── 1. File existence & size ─────────────────────────────────────────────
    section("1. ISO File Existence")

    if not iso_path.exists():
        result_fail(f"ISO not found: {iso_path}")
        return 2

    iso_size = iso_path.stat().st_size
    iso_size_mib = iso_size // (1024 * 1024)
    result_pass(f"ISO file exists: {iso_path.name} ({iso_size_mib} MiB / {iso_size:,} bytes)")

    if iso_size < 10240:
        result_warn("ISO is very small (<10 KiB) — likely placeholder or empty.")
    elif iso_size < 1_048_576:
        result_warn(f"ISO under 1 MiB ({iso_size:,} bytes) — expected much larger for a full OS.")
    else:
        result_pass(f"ISO size reasonable: {iso_size_mib} MiB")

    # ── 2. SHA256 checksum ───────────────────────────────────────────────────
    section("2. SHA256 Checksum Integrity")

    sha256file = dist_dir / "SHA256SUMS"
    computed_sha256 = _sha256file(iso_path)
    if not QUIET:
        print(f"     Computed : {computed_sha256}")

    if sha256file.exists():
        expected_sha256 = _find_sha256(sha256file, iso_path.name)
        if expected_sha256:
            if not QUIET:
                print(f"     Expected : {expected_sha256}")
            if expected_sha256.startswith("DRY-RUN"):
                result_warn(f"Dry-run placeholder SHA256: {expected_sha256}")
            elif computed_sha256 == expected_sha256:
                result_pass("SHA256 checksum matches.")
            else:
                result_fail("SHA256 MISMATCH — ISO may be corrupted or tampered.")
        else:
            result_warn(f"{iso_path.name} not listed in SHA256SUMS — cannot verify.")
    else:
        result_warn(f"SHA256SUMS not found: {sha256file}")

    # ── Open ISO for low-level parsing ───────────────────────────────────────
    try:
        fp = open(iso_path, "rb")
    except PermissionError:
        result_fail(f"Cannot open ISO (permission denied): {iso_path}")
        return 1

    # ── 3. ISO 9660 structure ────────────────────────────────────────────────
    section("3. ISO 9660 Structure")

    pvd: Optional[Dict[str, Any]] = None
    has_boot_record = False
    has_volume_descriptor_set_terminator = False

    try:
        for lba in range(16, 32):
            sector = _read_sector(fp, lba)
            vd = _parse_volume_descriptor(sector)
            if vd is None:
                break
            if vd["type"] == 1:    # Primary Volume Descriptor
                pvd = vd
            elif vd["type"] == 0:  # Boot Record
                has_boot_record = True
                boot_sys = vd.get("boot_system_id", "")
                result_pass(f"El Torito boot record present: '{boot_sys[:32]}'")
            elif vd["type"] == 255:  # Volume Descriptor Set Terminator
                has_volume_descriptor_set_terminator = True
                break
    except Exception as e:
        result_warn(f"ISO structure parsing error: {e}")

    if pvd:
        vol_id = pvd.get("volume_id", "").strip()
        if vol_id.startswith("KAIROS_") or vol_id.startswith("KAIROS"):
            result_pass(f"Volume ID: '{vol_id}' (KAIROS-branded)")
        else:
            result_warn(f"Volume ID: '{vol_id}' — expected KAIROS_*")

        lbs = pvd.get("logical_block_size", 0)
        if lbs == 2048:
            result_pass(f"Logical block size: {lbs} (correct ISO 9660)")
        else:
            result_warn(f"Logical block size: {lbs} (expected 2048)")

        result_pass(f"Primary Volume Descriptor: valid (sectors: {pvd.get('volume_space_size',0):,})")
    else:
        result_fail("No valid ISO 9660 Primary Volume Descriptor found — not a valid ISO.")
        fp.close()
        return 1

    if not has_volume_descriptor_set_terminator:
        result_warn("Volume Descriptor Set Terminator not found — ISO may be malformed.")

    # ── Build file index ─────────────────────────────────────────────────────
    file_index: Dict[str, Dict[str, Any]] = {}
    try:
        root_lba  = pvd["root_dir_lba"]
        root_size = pvd["root_dir_size"]
        file_index = _build_file_index(fp, root_lba, root_size)
        result_pass(f"ISO directory traversal: {len(file_index)} entries indexed")
    except Exception as e:
        result_warn(f"Could not fully traverse ISO directory: {e}")

    # ── 4. Required files ────────────────────────────────────────────────────
    section("4. Required Files Presence")

    MANDATORY = [
        ("live/filesystem.squashfs",              "Root filesystem (SquashFS)"),
        ("live/filesystem.sha256",                "SquashFS integrity checksum"),
        ("boot/vmlinuz-kairos",                   "KAIROS RT kernel"),
        ("boot/initramfs-kairos.img",             "Primary initramfs"),
        ("boot/grub/grub.cfg",                    "GRUB2 bootloader config"),
        ("efi/boot/bootx64.efi",                  "UEFI EFI binary"),
        ("kairos/version.json",                   "Version metadata"),
        ("kairos/installer.py",                   "KAIROS installer"),
        ("kairos/package-manifest.json",          "Package manifest"),
        ("recovery/recovery.py",                  "Recovery environment"),
        ("recovery/recovery.json",                "Recovery metadata"),
    ]

    RECOMMENDED = [
        ("boot/initramfs-kairos-fallback.img",    "Fallback initramfs"),
        ("kairos/build-info.json",                "Reproducibility build info"),
        ("kairos/installer-readme.md",            "Installer documentation"),
        ("recovery/readme.md",                    "Recovery documentation"),
    ]

    def _check_file(rel: str, label: str, mandatory: bool) -> Optional[Dict[str, Any]]:
        key = rel.lower().lstrip("/")
        entry = file_index.get(key)
        if entry:
            sz = entry.get("size", 0)
            if sz > 0:
                result_pass(f"{rel} ({sz:,} bytes) — {label}")
            else:
                result_warn(f"{rel} — exists but is EMPTY (0 bytes) — {label}")
            return entry
        else:
            if mandatory:
                result_fail(f"{rel} — MISSING — {label}")
            else:
                result_warn(f"{rel} — not present — {label} (recommended)")
            return None

    print("  Mandatory files:")
    mandatory_entries: Dict[str, Optional[Dict]] = {}
    for rel, label in MANDATORY:
        mandatory_entries[rel] = _check_file(rel, label, mandatory=True)

    print("\n  Recommended files:")
    for rel, label in RECOMMENDED:
        _check_file(rel, label, mandatory=False)

    # ── 5. Bootloader configuration ──────────────────────────────────────────
    section("5. Bootloader Configuration")

    grub_entry = mandatory_entries.get("boot/grub/grub.cfg")
    if grub_entry:
        try:
            grub_data = _read_file_from_iso(fp, grub_entry["lba"], grub_entry["size"])
            grub_text = grub_data.decode("utf-8", errors="replace")

            GRUB_PATTERNS = {
                "vmlinuz-kairos":       "Kernel image referenced",
                "initramfs-kairos.img": "Initramfs referenced",
                "kairos.mode=live":     "Live mode boot entry",
                "kairos.mode=installer":"Installer boot entry",
                "kairos.mode=recovery": "Recovery boot entry",
                "menuentry":            "Boot entries present",
            }
            for pattern, desc in GRUB_PATTERNS.items():
                if pattern in grub_text:
                    result_pass(f"GRUB: {desc}")
                else:
                    result_warn(f"GRUB missing: {desc} (pattern: '{pattern}')")

            menu_count = grub_text.count("menuentry")
            if menu_count >= 3:
                result_pass(f"GRUB has {menu_count} menuentry blocks (≥3)")
            else:
                result_warn(f"GRUB has only {menu_count} menuentry blocks (expected ≥3)")

        except Exception as e:
            result_warn(f"Could not read/parse GRUB config: {e}")
    else:
        result_warn("Cannot inspect GRUB config (file missing from index).")

    # ── 6. SquashFS integrity ────────────────────────────────────────────────
    section("6. SquashFS Integrity")

    squash_entry = mandatory_entries.get("live/filesystem.squashfs")
    squash_sum_entry = mandatory_entries.get("live/filesystem.sha256")

    if squash_entry:
        sq_size = squash_entry.get("size", 0)
        result_pass(f"SquashFS present ({sq_size:,} bytes)")

        # SquashFS magic: 0x73717368 LE = "sqsh"
        try:
            sq_header = _read_file_from_iso(fp, squash_entry["lba"], min(4, sq_size))
            if sq_header[:4] == b"hsqs":  # little-endian SquashFS magic
                result_pass("SquashFS magic bytes valid (hsqs — little-endian)")
            elif sq_header[:4] == b"sqsh":
                result_pass("SquashFS magic bytes valid (sqsh — big-endian)")
            elif sq_size < 10240 and any(c in sq_header for c in [b"KAIROS", b"placeholder"]):
                result_warn("SquashFS appears to be a build placeholder — not a real rootfs.")
            else:
                result_warn(f"Unexpected SquashFS header: {sq_header.hex()}")
        except Exception as e:
            result_warn(f"Could not read SquashFS header: {e}")

        # Re-verify SquashFS SHA256 if we can read the .sha256 file
        if squash_sum_entry:
            try:
                sum_data = _read_file_from_iso(
                    fp, squash_sum_entry["lba"], squash_sum_entry["size"]
                )
                expected_sq_sha256 = sum_data.decode("utf-8", errors="replace").split()[0]
                if not QUIET:
                    print(f"     Expected SquashFS SHA256: {expected_sq_sha256}")

                # Read the SquashFS and compute SHA256 (may be large — stream it)
                h = hashlib.sha256()
                fp.seek(squash_entry["lba"] * SECTOR_SIZE)
                remaining = sq_size
                while remaining > 0:
                    chunk = fp.read(min(65536, remaining))
                    if not chunk:
                        break
                    h.update(chunk)
                    remaining -= len(chunk)
                computed_sq_sha256 = h.hexdigest()
                if not QUIET:
                    print(f"     Computed SquashFS SHA256: {computed_sq_sha256}")

                if expected_sq_sha256 == computed_sq_sha256:
                    result_pass("SquashFS SHA256 integrity verified ✓")
                else:
                    result_fail("SquashFS SHA256 MISMATCH — rootfs may be corrupted.")
            except Exception as e:
                result_warn(f"Could not verify SquashFS SHA256: {e}")
        else:
            result_warn("No filesystem.sha256 in ISO — cannot verify SquashFS integrity.")
    else:
        result_warn("SquashFS not found in index — cannot verify.")

    # ── 7. Installer integrity ───────────────────────────────────────────────
    section("7. Installer")

    installer_entry = mandatory_entries.get("kairos/installer.py")
    if installer_entry:
        try:
            ins_size = installer_entry.get("size", 0)
            result_pass(f"Installer embedded ({ins_size:,} bytes)")

            if ins_size < 10240:
                result_warn(f"Installer seems small ({ins_size} bytes < 10 KiB).")

            ins_data = _read_file_from_iso(fp, installer_entry["lba"], ins_size)
            ins_text = ins_data.decode("utf-8", errors="replace")

            # Python syntax check
            try:
                import py_compile, tempfile
                with tempfile.NamedTemporaryFile(
                    suffix=".py", delete=False, mode="wb"
                ) as tf:
                    tf.write(ins_data)
                    tf_path = tf.name
                py_compile.compile(tf_path, doraise=True)
                os.unlink(tf_path)
                result_pass("Installer: Python syntax valid.")
            except py_compile.PyCompileError as e:
                result_fail(f"Installer: Python syntax error: {e}")
            except Exception:
                pass

            # Invariant checks
            INSTALLER_PATTERNS = {
                r"YES, DESTROY DATA":     "Destructive confirmation gate",
                r"dry.run|DRY_RUN":       "Dry-run mode support",
                r"phase_health_check":    "Health check phase",
                r"InstallState":          "Install state management",
                r"<REDACTED>":            "Secret redaction in manifests",
                r"LUKS|luks|encrypt":     "Disk encryption support",
            }
            for pattern, desc in INSTALLER_PATTERNS.items():
                if re.search(pattern, ins_text, re.IGNORECASE):
                    result_pass(f"Installer: {desc}")
                else:
                    result_warn(f"Installer missing: {desc}")

        except Exception as e:
            result_warn(f"Could not inspect installer: {e}")
    else:
        result_warn("Installer not in file index — cannot verify.")

    # ── 8. Recovery environment ──────────────────────────────────────────────
    section("8. Recovery Environment")

    recovery_entry = mandatory_entries.get("recovery/recovery.py")
    if recovery_entry:
        try:
            rec_size = recovery_entry.get("size", 0)
            result_pass(f"Recovery script embedded ({rec_size:,} bytes)")

            rec_data = _read_file_from_iso(fp, recovery_entry["lba"], rec_size)
            rec_text = rec_data.decode("utf-8", errors="replace")

            # Python syntax check
            try:
                import py_compile, tempfile
                with tempfile.NamedTemporaryFile(
                    suffix=".py", delete=False, mode="wb"
                ) as tf:
                    tf.write(rec_data)
                    tf_path = tf.name
                py_compile.compile(tf_path, doraise=True)
                os.unlink(tf_path)
                result_pass("Recovery: Python syntax valid.")
            except py_compile.PyCompileError as e:
                result_fail(f"Recovery: Python syntax error: {e}")
            except Exception:
                pass

            RECOVERY_PATTERNS = {
                r"repair|Repair":    "System repair capability",
                r"rollback|Rollback":"Update rollback capability",
                r"diagnos":          "Diagnostics capability",
                r"recovery|Recovery":"Recovery menu",
            }
            for pattern, desc in RECOVERY_PATTERNS.items():
                if re.search(pattern, rec_text, re.IGNORECASE):
                    result_pass(f"Recovery: {desc}")
                else:
                    result_warn(f"Recovery missing: {desc}")

        except Exception as e:
            result_warn(f"Could not inspect recovery script: {e}")

    # version.json
    rec_json_entry = mandatory_entries.get("recovery/recovery.json")
    if rec_json_entry:
        try:
            data = _read_file_from_iso(fp, rec_json_entry["lba"], rec_json_entry["size"])
            d = json.loads(data.decode("utf-8", errors="replace"))
            result_pass(f"recovery.json valid JSON ({len(d.get('menu_items', []))} menu items)")
        except Exception as e:
            result_fail(f"recovery.json: {e}")

    # ── 9. Version metadata ──────────────────────────────────────────────────
    section("9. Version Metadata Consistency")

    iso_version = ""
    iso_codename = ""
    iso_epoch = ""
    iso_commit = ""

    ver_entry = mandatory_entries.get("kairos/version.json")
    if ver_entry:
        try:
            ver_data = _read_file_from_iso(fp, ver_entry["lba"], ver_entry["size"])
            ver_d = json.loads(ver_data.decode("utf-8", errors="replace"))
            result_pass("kairos/version.json: valid JSON.")

            required_ver_keys = ["name", "version", "codename", "arch",
                                  "build_date", "source_date_epoch"]
            missing = [k for k in required_ver_keys if k not in ver_d]
            if missing:
                result_warn(f"version.json missing keys: {missing}")
            else:
                result_pass("version.json has all required fields.")

            iso_version  = str(ver_d.get("version", ""))
            iso_codename = str(ver_d.get("codename", ""))
            iso_epoch    = str(ver_d.get("source_date_epoch", ""))
            iso_commit   = str(ver_d.get("git_commit", ""))

            result_pass(f"ISO version: {iso_version} '{iso_codename}' "
                        f"(epoch={iso_epoch} commit={iso_commit})")

            if ver_d.get("name") == "KAIROS OS":
                result_pass("KAIROS OS identity confirmed.")
            else:
                result_fail(f"ISO name is not 'KAIROS OS': '{ver_d.get('name')}'")

        except json.JSONDecodeError as e:
            result_fail(f"kairos/version.json: invalid JSON: {e}")
        except Exception as e:
            result_warn(f"Could not parse version.json: {e}")

    # Cross-check with dist/version-metadata.json
    if (dist_dir / "version-metadata.json").exists():
        try:
            dist_d = json.loads((dist_dir / "version-metadata.json").read_text())
            result_pass("dist/version-metadata.json: valid JSON.")
            dist_version = str(dist_d.get("version", ""))
            if iso_version and dist_version:
                if iso_version == dist_version:
                    result_pass(f"Version consistent: ISO={iso_version} = dist={dist_version}")
                else:
                    result_fail(f"Version MISMATCH: ISO={iso_version} ≠ dist={dist_version}")
        except json.JSONDecodeError as e:
            result_fail(f"dist/version-metadata.json: invalid JSON: {e}")

    # ── 10. Build manifest ───────────────────────────────────────────────────
    section("10. Build Manifest")

    bm_path = dist_dir / "build-manifest.json"
    if bm_path.exists():
        try:
            bm_d = json.loads(bm_path.read_text())
            result_pass("dist/build-manifest.json: valid JSON.")

            REQUIRED_BM_KEYS = ["iso", "version", "components", "required_files",
                                 "reproducibility"]
            missing_bm = [k for k in REQUIRED_BM_KEYS if k not in bm_d]
            if missing_bm:
                result_warn(f"Build manifest missing keys: {missing_bm}")
            else:
                result_pass("Build manifest has all required keys.")

            manifest_sha = bm_d.get("iso", {}).get("sha256", "")
            if manifest_sha and not manifest_sha.startswith("DRY-RUN"):
                if manifest_sha == computed_sha256:
                    result_pass("Build manifest SHA256 matches computed hash.")
                else:
                    result_fail(
                        f"Build manifest SHA256 mismatch: "
                        f"manifest={manifest_sha[:16]}… computed={computed_sha256[:16]}…"
                    )
            elif manifest_sha.startswith("DRY-RUN"):
                result_warn("Build manifest contains dry-run placeholder SHA256.")

        except json.JSONDecodeError as e:
            result_fail(f"dist/build-manifest.json: invalid JSON: {e}")
    else:
        result_warn("dist/build-manifest.json not found.")

    # ── 11. Package manifest ─────────────────────────────────────────────────
    section("11. Package Manifest")

    pm_path = dist_dir / "package-manifest.json"
    if pm_path.exists():
        try:
            pm_d = json.loads(pm_path.read_text())
            result_pass("dist/package-manifest.json: valid JSON.")
            pkg_count = pm_d.get("count", len(pm_d.get("packages", [])))
            if pkg_count > 0:
                result_pass(f"Package manifest: {pkg_count} packages listed.")
            else:
                result_warn("Package manifest: no packages listed.")
        except json.JSONDecodeError as e:
            result_fail(f"dist/package-manifest.json: invalid JSON: {e}")
    else:
        result_warn("dist/package-manifest.json not found.")

    # Also check in-ISO copy
    pkg_in_iso = mandatory_entries.get("kairos/package-manifest.json")
    if pkg_in_iso:
        try:
            pkg_data = _read_file_from_iso(fp, pkg_in_iso["lba"], pkg_in_iso["size"])
            pkg_d = json.loads(pkg_data.decode("utf-8", errors="replace"))
            pkg_count = pkg_d.get("count", len(pkg_d.get("packages", [])))
            result_pass(f"kairos/package-manifest.json (in ISO): {pkg_count} packages.")
        except Exception as e:
            result_warn(f"Could not parse in-ISO package-manifest.json: {e}")

    # ── 12. Reproducibility ──────────────────────────────────────────────────
    section("12. Reproducibility Metadata")

    if iso_epoch:
        try:
            epoch_int = int(iso_epoch)
            epoch_date = datetime.datetime.utcfromtimestamp(epoch_int).strftime("%Y-%m-%d")
            result_pass(f"SOURCE_DATE_EPOCH={iso_epoch} ({epoch_date}) — reproducibility timestamp set.")

            if epoch_int == 0:
                result_warn("SOURCE_DATE_EPOCH=0 — not truly reproducible.")
        except ValueError:
            result_warn(f"SOURCE_DATE_EPOCH invalid: '{iso_epoch}'")
    else:
        result_warn("SOURCE_DATE_EPOCH not found in version metadata — ISO may not be reproducible.")

    fp.close()

    # ─────────────────────────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────────────────────────

    END = datetime.datetime.utcnow()
    elapsed = (END - START).total_seconds()

    return (iso_version, iso_codename, iso_epoch, iso_commit, computed_sha256, elapsed)


def _sha256file(path: Path, chunk_size: int = 65536) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _find_sha256(sha256file: Path, iso_name: str) -> Optional[str]:
    try:
        for line in sha256file.read_text().splitlines():
            parts = line.strip().split(None, 1)
            if len(parts) == 2 and parts[1].strip() in (iso_name, f"./{iso_name}"):
                return parts[0]
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    global QUIET, STRICT

    parser = argparse.ArgumentParser(
        description="KAIROS OS ISO Verification (pure Python, no root required)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.strip().split("\n\nRun:")[0].strip()
    )
    parser.add_argument("iso", nargs="?", help="Path to KAIROS ISO file")
    parser.add_argument("--json",   action="store_true", help="Output JSON result")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failures")
    parser.add_argument("--quiet",  "-q", action="store_true", help="Suppress per-check output")
    args = parser.parse_args()

    QUIET = args.quiet
    STRICT = args.strict

    # Locate ISO
    root_dir = Path(__file__).parent.parent
    dist_dir = root_dir / "dist"

    iso_path: Optional[Path] = None
    if args.iso:
        iso_path = Path(args.iso)
    else:
        isos = sorted(dist_dir.glob("*.iso"), key=lambda p: p.stat().st_mtime, reverse=True)
        if isos:
            iso_path = isos[0]

    if not iso_path:
        print("\n  Error: No ISO specified and none found in dist/.")
        print("  Usage: python3 scripts/verify_iso.py [path/to/kairos.iso]")
        print("  Build: ./scripts/build-iso\n")
        return 2

    # Banner
    if not QUIET and not args.json:
        print()
        print("━" * 74)
        print()
        print("  \033[1m◈  KAIROS OS ISO Verification (Python)\033[0m")
        print(f"     ISO     : {iso_path}")
        print(f"     Date    : {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"     Strict  : {'YES' if STRICT else 'NO'}")
        print()
        print("━" * 74)

    # Run verification
    result = verify_iso(iso_path, dist_dir)
    if isinstance(result, int):
        return result
    iso_version, iso_codename, iso_epoch, iso_commit, computed_sha256, elapsed = result

    # Apply strict: warn → fail
    final_fail = FAIL
    final_warn = WARN
    if STRICT:
        final_fail += WARN
        final_warn  = 0

    # JSON output
    if args.json:
        output = {
            "iso":            str(iso_path),
            "iso_name":       iso_path.name,
            "sha256":         computed_sha256,
            "iso_size_bytes": iso_path.stat().st_size if iso_path.exists() else 0,
            "verified_at":    datetime.datetime.utcnow().isoformat() + "Z",
            "elapsed_seconds": elapsed,
            "strict_mode":    STRICT,
            "iso_version":    iso_version,
            "iso_codename":   iso_codename,
            "iso_epoch":      iso_epoch,
            "iso_commit":     iso_commit,
            "pass":           PASS,
            "warn":           final_warn,
            "fail":           final_fail,
            "overall":        "PASS" if final_fail == 0 else "FAIL",
            "checks":         CHECKS,
        }
        print(json.dumps(output, indent=2))
        return 0 if final_fail == 0 else 1

    # Human-readable summary
    print()
    print("━" * 74)
    print()
    print("\033[1m  Verification Summary:\033[0m")
    print()
    print(f"    \033[32mPASSED  : {PASS}\033[0m")
    print(f"    \033[33mWARNED  : {final_warn}\033[0m")
    print(f"    \033[31mFAILED  : {final_fail}\033[0m")
    print(f"    Elapsed : {elapsed:.2f}s")
    print()

    if final_fail > 0:
        print(f"  \033[31m✗  VERIFICATION FAILED — {final_fail} critical check(s) failed.\033[0m")
        print()
        print("     This ISO may not boot or may be missing required components.")
        print("     Rebuild with: ./scripts/build-iso")
        print()
        return 1
    elif final_warn > 0:
        print(f"  \033[33m⚠  PASSED WITH WARNINGS — {final_warn} advisory item(s).\033[0m")
        print()
        print("     ISO appears functional. Warnings typically arise from limited")
        print("     inspection capabilities (no root mount, missing optional tools).")
        print()
        return 0
    else:
        print("  \033[32m✓  ALL CHECKS PASSED — ISO verified and ready.\033[0m")
        print()
        print(f"     SHA256  : {computed_sha256}")
        if iso_version:
            print(f"     Version : {iso_version} '{iso_codename}'")
        if iso_epoch:
            print(f"     Epoch   : {iso_epoch}")
        if iso_commit:
            print(f"     Commit  : {iso_commit}")
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())
