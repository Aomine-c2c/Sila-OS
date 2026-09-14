#!/usr/bin/env python3
"""
Automated KAIROS Kernel Configuration Validator.
Audits layered kernel configuration fragments in config/kernel/ against
mandatory hardware, low-latency, security, desktop, and storage requirements.
"""

import os
import sys
import glob

# Ensure stdout handles UTF-8 safely
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REQUIRED_KERNEL_OPTIONS = {
    # UEFI & Boot
    "CONFIG_EFI": ["y"],
    "CONFIG_EFIVAR_FS": ["y"],
    "CONFIG_EFI_STUB": ["y"],

    # Storage & NVMe
    "CONFIG_BLK_DEV_NVME": ["y"],
    "CONFIG_BTRFS_FS": ["y"],
    "CONFIG_EXT4_FS": ["y"],
    "CONFIG_VFAT_FS": ["y"],
    "CONFIG_SATA_AHCI": ["y"],

    # Networking
    "CONFIG_NET": ["y"],
    "CONFIG_INET": ["y"],
    "CONFIG_WIREGUARD": ["y", "m"],
    "CONFIG_BPF_SYSCALL": ["y"],

    # Graphics & Desktop
    "CONFIG_DRM": ["y"],
    "CONFIG_DRM_AMDGPU": ["m", "y"],
    "CONFIG_DRM_I915": ["m", "y"],
    "CONFIG_DRM_NOUVEAU": ["m", "y"],

    # Audio & Bluetooth
    "CONFIG_SOUND": ["y"],
    "CONFIG_SND_HDA_INTEL": ["m", "y"],
    "CONFIG_BT": ["m", "y"],

    # Security
    "CONFIG_SECURITY_APPARMOR": ["y"],
    "CONFIG_SECCOMP": ["y"],
    "CONFIG_HARDENED_USERCOPY": ["y"],

    # Performance
    "CONFIG_PREEMPT_DYNAMIC": ["y"],
    "CONFIG_HZ_1000": ["y"],
    "CONFIG_CPU_FREQ_GOV_PERFORMANCE": ["y"],

    # Virtualization
    "CONFIG_KVM": ["y", "m"],
    "CONFIG_VIRTIO_PCI": ["y"],
    "CONFIG_VIRTIO_BLK": ["y"],
    "CONFIG_VIRTIO_NET": ["y"],
}

def load_fragments(config_dir):
    options = {}
    fragment_files = sorted(glob.glob(os.path.join(config_dir, "*.config")))
    if not fragment_files:
        print(f"[!] No .config files found in {config_dir}")
        return options, []

    for f_path in fragment_files:
        with open(f_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    options[key.strip()] = val.strip()
    return options, fragment_files

def validate_configuration(config_dir="config/kernel"):
    print("================================================================================")
    print(" [*] KAIROS Automated Kernel Configuration Validation Engine")
    print(f" Directory: {config_dir}")
    print("================================================================================")

    options, files = load_fragments(config_dir)
    print(f"[*] Loaded {len(files)} modular configuration fragment(s):")
    for f in files:
        print(f"  - {os.path.basename(f)}")

    missing = []
    mismatched = []

    for opt, expected_vals in REQUIRED_KERNEL_OPTIONS.items():
        if opt not in options:
            missing.append(opt)
        elif options[opt] not in expected_vals:
            mismatched.append((opt, options[opt], expected_vals))

    print("\n[*] Audit Results:")
    if missing:
        print(f"  [!] FAIL: Missing {len(missing)} mandatory option(s):")
        for m in missing:
            print(f"      - {m}")

    if mismatched:
        print(f"  [!] FAIL: Mismatched values in {len(mismatched)} option(s):")
        for opt, actual, expected in mismatched:
            print(f"      - {opt}={actual} (Expected one of: {expected})")

    if not missing and not mismatched:
        print("  [+] PASS: All mandatory hardware, storage, graphics, and low-latency parameters verified.")
        print("================================================================================")
        print(" Kernel Configuration Audit: PASSED (Upstream-Compatible & Production-Ready)")
        print("================================================================================")
        return 0
    else:
        print("================================================================================")
        print(" Kernel Configuration Audit: FAILED")
        print("================================================================================")
        return 1

def main():
    config_dir = sys.argv[1] if len(sys.argv) > 1 else "config/kernel"
    return validate_configuration(config_dir)

if __name__ == "__main__":
    sys.exit(main())
