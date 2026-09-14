# KAIROS OS Boot Architecture & Specification

## 1. Overview & Vision
KAIROS OS is an engineered Linux operating system for professional traders, quantitative researchers, and autonomous market operators. The boot architecture is designed **UEFI-first**, prioritizing predictability, low latency, robust recovery, and absolute stability.

The boot system adheres to the following principles:
- **Clean, Minimal Visual Identity**: No consumer splash animations or graphical bloat. Clean status output communicating:
  `KAIROS Adaptive Trading Operating System`
- **UEFI-First**: Native support for modern UEFI firmware, GPT partition schemes, and EFI runtime variables (`efivarfs`).
- **Dual Bootloader Support**:
  1. **systemd-boot** (Primary UEFI Boot Loader): Minimal, fast, compliant with the Boot Loader Specification (BLS).
  2. **GRUB2** (Hybrid / Fallback Boot Loader): For systems requiring modular recovery, ISO live boots, or hypervisor compatibility.
- **Fail-Safe Operation**: Dedicated entries and initramfs archives for normal operation, safe driver fallbacks, emergency single-user recovery, and automated boot diagnostics.

---

## 2. Boot Hierarchy & Flow

```
+-------------------------------------------------------------------------+
|                              UEFI Firmware                              |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                  ESP (EFI System Partition - FAT32)                     |
|           /boot/efi/EFI/systemd/systemd-bootx64.efi or GRUB             |
+-------------------------------------------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|              Boot Menu (Timeout: 3s, Console-Mode: Max)                 |
|  1. KAIROS OS (Adaptive Trading Operating System) [Default]             |
|  2. KAIROS OS (Fallback Boot / Safe Drivers)                            |
|  3. KAIROS OS (Recovery Mode / Emergency Shell)                         |
|  4. KAIROS OS (Boot & Hardware Diagnostics)                             |
+-------------------------------------------------------------------------+
                                     |
                  +------------------+------------------+
                  |                                     |
                  v                                     v
+-----------------------------------+ +-----------------------------------+
|      Normal / Diag Kernel Boot    | |        Fallback Kernel Boot       |
|    vmlinuz-kairos (x86_64)        | |    vmlinuz-kairos (x86_64)        |
|    initramfs-kairos.img           | |    initramfs-kairos-fallback.img  |
|    Low-latency tuning active      | |    nomodeset, acpi=noirq active   |
+-----------------------------------+ +-----------------------------------+
                  |                                     |
                  +------------------+------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                       KAIROS PID 1 Init Process                         |
|  - Mounts /proc, /sys, /dev, /run, /tmp                                 |
|  - Mounts /sys/firmware/efi/efivars (if UEFI active)                    |
|  - Initializes loopback network                                         |
|  - Displays Identity: KAIROS Adaptive Trading Operating System          |
|  - Dispatches Profile: normal | fallback | recovery | diag              |
+-------------------------------------------------------------------------+
```

---

## 3. Directory Layout

The boot directory hierarchy in `/boot` conforms to standard modern Linux and UEFI specifications:

```
/boot/
├── vmlinuz-kairos                       # 6.14.x x86_64 Linux kernel
├── initramfs-kairos.img                 # Primary production initramfs
├── initramfs-kairos-fallback.img        # Safe driver fallback initramfs
├── loader/
│   ├── loader.conf                      # systemd-boot configuration
│   └── entries/
│       ├── kairos.conf                  # Normal boot entry
│       ├── kairos-fallback.conf         # Fallback boot entry
│       ├── kairos-recovery.conf         # Emergency recovery entry
│       └── kairos-diag.conf             # Diagnostics entry
├── grub/
│   └── grub.cfg                         # GRUB2 fallback & ISO configuration
└── efi/
    ├── startup.nsh                      # UEFI Shell boot script
    └── EFI/
        ├── BOOT/
        │   └── BOOTX64.EFI              # Default UEFI loader
        └── kairos/
            └── systemd-bootx64.efi      # KAIROS UEFI loader binary
```

---

## 4. Boot Entries & Kernel Parameter Profiles

### 4.1. Normal Production Boot (`kairos.conf`)
- **Kernel**: `/vmlinuz-kairos`
- **Initrd**: `/initramfs-kairos.img`
- **Command Line**:
  ```text
  root=LABEL=KAIROS_ROOT rootflags=subvol=@ ro quiet loglevel=3 \
  kairos.mode=normal skew_tick=1 nohz=on nohz_full=1-7 rcu_nocbs=1-7 \
  processor.max_cstate=1 apparmor=1 security=apparmor efi=runtime
  ```
- **Rationale**: Enables deterministic real-time scheduling ticks, offloads RCU callbacks from trading cores, locks CPU power states to eliminate C-state exit latency, and keeps UEFI runtime services active.

### 4.2. Fallback Boot (`kairos-fallback.conf`)
- **Kernel**: `/vmlinuz-kairos`
- **Initrd**: `/initramfs-kairos-fallback.img`
- **Command Line**:
  ```text
  root=LABEL=KAIROS_ROOT rootflags=subvol=@ ro kairos.mode=fallback nomodeset acpi=noirq efi=runtime
  ```
- **Rationale**: Used when new graphics cards, firmware updates, or peripheral hardware issues prevent normal boot. Disables kernel modesetting (`nomodeset`) and ACPI IRQ routing conflicts.

### 4.3. Emergency Recovery Boot (`kairos-recovery.conf`)
- **Kernel**: `/vmlinuz-kairos`
- **Initrd**: `/initramfs-kairos.img`
- **Command Line**:
  ```text
  root=LABEL=KAIROS_ROOT rootflags=subvol=@ ro single emergency systemd.unit=rescue.target kairos.mode=recovery nomodeset
  ```
- **Rationale**: Drops directly into a root maintenance shell with minimal services running for disaster recovery, Btrfs snapshot rollbacks, and risk gateway audits.

### 4.4. Boot & Hardware Diagnostics (`kairos-diag.conf`)
- **Kernel**: `/vmlinuz-kairos`
- **Initrd**: `/initramfs-kairos.img`
- **Command Line**:
  ```text
  root=LABEL=KAIROS_ROOT rootflags=subvol=@ ro kairos.mode=diag nomodeset loglevel=7
  ```
- **Rationale**: Performs non-destructive hardware inspection, prints detailed PCI bus trees, enumerates NVMe/SATA storage blocks, and verifies EFI runtime accessibility.

---

## 5. Boot Diagnostics Subsystem (`kairos boot diag`)

KAIROS includes an integrated boot diagnostic tool available from userspace and emergency shells:

```bash
kairos boot diag
```

Sample output:
```text
================================================================================
 ◈ KAIROS OS - Boot Architecture Diagnostic Subsystem
 Identity: KAIROS Adaptive Trading Operating System
================================================================================
 [Firmware / Boot Mode]   : UEFI (Unified Extensible Firmware Interface)
 [EFI Variables Mount]    : Available & Populated (/sys/firmware/efi/efivars)
 [Active Kernel Cmdline]  : console=ttyS0 quiet kairos.mode=normal efi=runtime
 [Boot Profile]           : NORMAL
 [Storage Subsystems]     : NVMe (nvme0n1), SATA/SCSI (sda)
 [Bootloaders Staged]     : systemd-boot (UEFI-primary), GRUB2 (Hybrid/Recovery)
 [Boot Targets Validated] :
   * Normal Boot   : vmlinuz-kairos + initramfs-kairos.img
   * Fallback Boot : vmlinuz-kairos + initramfs-kairos-fallback.img (safe drivers)
   * Recovery Boot : single/emergency shell, nomodeset
   * Diag Boot     : non-destructive hardware inspection
================================================================================
 Boot Diagnostic Result    : PASS | Integrity Verified
================================================================================
```

---

## 6. Automated Verification Matrix

The boot architecture is continuously tested via automated QEMU test harnesses (`scripts/test_boot_scenarios.py` and `tests/test_boot_architecture.py`):

| Scenario | Kernel Parameters | Target Image | Expected Result | Status |
|---|---|---|---|---|
| **1. Normal Boot** | `kairos.mode=normal` | `initramfs-kairos.img` | Displays clean KAIROS identity, boots to userspace | **PASS** |
| **2. Fallback Boot** | `kairos.mode=fallback nomodeset` | `initramfs-kairos-fallback.img` | Safe driver fallback, boots to userspace | **PASS** |
| **3. Recovery Boot** | `single emergency kairos.mode=recovery` | `initramfs-kairos.img` | Emergency shell active | **PASS** |
| **4. Boot Diagnostics** | `kairos.mode=diag` | `initramfs-kairos.img` | Hardware, block & EFI probe | **PASS** |
| **5. Invalid Parameters** | `kairos.mode=CORRUPT_VALUE` | `initramfs-kairos.img` | Warning issued, graceful fallback to safe mode | **PASS** |
| **6. Missing Config** | *(none)* | `initramfs-kairos.img` | Defaults to normal profile cleanly | **PASS** |
| **7. Reboot / Shutdown** | `kairos.autotest=2` | `initramfs-kairos.img` | ACPI S5 poweroff / clean reboot | **PASS** |

---

## 7. How to Test Inside a VM

To execute the full automated test suite inside QEMU:
```bash
# Run all 7 boot scenarios in QEMU
python3 scripts/test_boot_scenarios.py

# Run unit tests for boot configuration and integrity
python3 -m unittest tests/test_boot_architecture.py
```
