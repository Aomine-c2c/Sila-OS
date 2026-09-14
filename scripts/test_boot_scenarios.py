#!/usr/bin/env python3
"""
Comprehensive KAIROS Boot Architecture & Scenarios Verifier
Tests the 7 essential boot scenarios in QEMU:
  1. Normal Boot (UEFI/systemd-boot profile, low-latency parameters, identity verification)
  2. Fallback Boot (fallback initramfs, safe drivers, nomodeset)
  3. Recovery Boot (single/emergency mode, recovery shell)
  4. Boot Diagnostics (kairos.mode=diag, hardware & EFI inspection)
  5. Invalid Kernel Parameters Handling (graceful fallback to safe profile)
  6. Missing Configuration Resilience (system handles missing custom parameters cleanly)
  7. Reboot & Shutdown Cycles (clean ACPI S5 poweroff / reboot signals)
"""

import os
import sys
import subprocess
import time

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KERNEL_PATH = os.path.join(ROOT_DIR, "build/rootfs/boot/vmlinuz-kairos")
INITRD_NORMAL = os.path.join(ROOT_DIR, "build/rootfs/boot/initramfs-kairos.img")
INITRD_FALLBACK = os.path.join(ROOT_DIR, "build/rootfs/boot/initramfs-kairos-fallback.img")

def run_qemu_scenario(name, kernel, initrd, cmdline, timeout_sec=20):
    print(f"\n================================================================================")
    print(f" [*] Running Scenario: {name}")
    print(f"     Initrd  : {os.path.basename(initrd)}")
    print(f"     Cmdline : {cmdline}")
    print(f"================================================================================")

    base_cmd = [
        "qemu-system-x86_64",
        "-m", "1024",
        "-smp", "2",
        "-kernel", kernel,
        "-initrd", initrd,
        "-append", cmdline,
        "-serial", "stdio",
        "-display", "none",
        "-no-reboot"
    ]

    try:
        proc = subprocess.Popen(
            base_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            if proc.poll() is not None:
                break
            time.sleep(0.3)

        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

        stdout, stderr = proc.communicate()
        return stdout, proc.returncode

    except Exception as e:
        print(f"[!] QEMU execution failed: {e}")
        return "", -1

def verify_all_scenarios():
    if not os.path.exists(KERNEL_PATH) or not os.path.exists(INITRD_NORMAL):
        print(f"[!] Kernel or Initramfs missing! Run build_minimal_initramfs.sh first.")
        return 1

    scenarios = [
        {
            "name": "1. Normal Boot (Default Profile & KAIROS Identity)",
            "initrd": INITRD_NORMAL,
            "cmdline": "console=ttyS0 quiet kairos.mode=normal kairos.autotest=1 panic=1",
            "expected": [
                "KAIROS Adaptive Trading Operating System",
                "[Active Profile]  : normal",
                "KAIROS_BOOT_SUCCESS"
            ]
        },
        {
            "name": "2. Fallback Boot (Safe Drivers & Fallback Initrd)",
            "initrd": INITRD_FALLBACK,
            "cmdline": "console=ttyS0 quiet kairos.mode=fallback nomodeset kairos.autotest=1 panic=1",
            "expected": [
                "KAIROS Adaptive Trading Operating System",
                "[Active Profile]  : fallback",
                "[FALLBACK] Booting with safe driver fallbacks",
                "KAIROS_BOOT_SUCCESS"
            ]
        },
        {
            "name": "3. Recovery Boot (Emergency / Single User Shell)",
            "initrd": INITRD_NORMAL,
            "cmdline": "console=ttyS0 quiet single emergency kairos.mode=recovery kairos.autotest=1 panic=1",
            "expected": [
                "KAIROS Adaptive Trading Operating System",
                "[Active Profile]  : recovery",
                "[RECOVERY] Entering emergency single-user maintenance shell",
                "KAIROS_BOOT_SUCCESS"
            ]
        },
        {
            "name": "4. Boot Diagnostics (Hardware & EFI Inspection)",
            "initrd": INITRD_NORMAL,
            "cmdline": "console=ttyS0 quiet kairos.mode=diag kairos.autotest=1 panic=1",
            "expected": [
                "KAIROS Adaptive Trading Operating System",
                "[Active Profile]  : diag",
                "[DIAG] Executing KAIROS hardware & bootloader diagnostics",
                "[DIAG] Diagnostics Complete: PASS",
                "KAIROS_BOOT_SUCCESS"
            ]
        },
        {
            "name": "5. Invalid Kernel Parameters Handling",
            "initrd": INITRD_NORMAL,
            "cmdline": "console=ttyS0 quiet kairos.mode=CORRUPT_UNKNOWN_VALUE! kairos.autotest=1 panic=1",
            "expected": [
                "WARNING: Unrecognized kernel parameter mode",
                "Defaulting to safe fallback mode",
                "KAIROS_BOOT_SUCCESS"
            ]
        },
        {
            "name": "6. Missing Configuration Resilience (Empty Mode)",
            "initrd": INITRD_NORMAL,
            "cmdline": "console=ttyS0 quiet kairos.autotest=1 panic=1",
            "expected": [
                "KAIROS Adaptive Trading Operating System",
                "[Active Profile]  : normal",
                "KAIROS_BOOT_SUCCESS"
            ]
        },
        {
            "name": "7. Clean Reboot & Shutdown Handling",
            "initrd": INITRD_NORMAL,
            "cmdline": "console=ttyS0 quiet kairos.mode=normal kairos.autotest=2 panic=1",
            "expected": [
                "KAIROS Adaptive Trading Operating System",
                "Reboot requested...",
                "KAIROS_BOOT_SUCCESS"
            ]
        }
    ]

    all_passed = True
    results = []

    for sc in scenarios:
        output, rc = run_qemu_scenario(
            sc["name"],
            KERNEL_PATH,
            sc["initrd"],
            sc["cmdline"],
            timeout_sec=20
        )

        missing = []
        for exp in sc["expected"]:
            if exp not in output:
                missing.append(exp)

        if missing:
            all_passed = False
            results.append((sc["name"], "FAIL", f"Missing expected strings: {missing}"))
            print(f"[-] FAILED: {sc['name']}")
            print(f"    Output excerpt:\n{output[-500:]}")
        else:
            results.append((sc["name"], "PASS", "All assertions satisfied"))
            print(f"[+] PASSED: {sc['name']}")

    print("\n================================================================================")
    print(" ◈ KAIROS Boot Architecture Test Summary")
    print("================================================================================")
    for name, status, detail in results:
        badge = "[✓ PASS]" if status == "PASS" else "[✗ FAIL]"
        print(f" {badge} {name}: {detail}")
    print("================================================================================")

    if all_passed:
        print("[+] ALL 7 KAIROS BOOT SCENARIOS VERIFIED SUCCESSFULLY.")
        return 0
    else:
        print("[!] SOME BOOT SCENARIOS FAILED.")
        return 1

if __name__ == "__main__":
    sys.exit(verify_all_scenarios())
