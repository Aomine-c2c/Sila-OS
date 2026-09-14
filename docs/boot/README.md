# KAIROS Boot Subsystem Documentation
Details UEFI systemd-boot, GRUB2, Limine configurations, and kernel parameter flags.

This document describes the design, configuration, and implementation requirements for this subsystem.

## Bootloaders

KAIROS OS supports multiple bootloader options for maximum compatibility:

### systemd-boot
- Location: /boot/loader/loader.conf
- UEFI-only bootloader
- Uses Boot Loader Specification (BLS) entries
- Entries located in /boot/loader/entries/

### GRUB2
- Location: /boot/grub/grub.cfg
- Full UEFI/BIOS support
- Menu-driven interface
- Advanced configuration options

### Limine
- Location: /boot/limine/limine.conf
- Modern, secure, portable bootloader
- Supports Linux, Multiboot, and Limine boot protocol
- UEFI and BIOS support
- EFI binaries: /boot/efi/EFI/BOOT/BOOTX64.EFI
- BIOS binaries: /boot/limine/limine-bios-hdd.h
- CD/ISO binaries: /boot/limine/limine-{uefi,bios}-cd.bin

## Boot Entries

KAIROS OS provides four boot modes:

1. **Normal Mode** - Default boot with full optimizations
   - Kernel: vmlinuz-kairos
   - Initrd: initramfs-kairos.img
   - Features: RT kernel, low-latency tuning, AppArmor

2. **Fallback Mode** - Safe drivers for compatibility
   - Kernel: vmlinuz-kairos
   - Initrd: initramfs-kairos-fallback.img
   - Features: nomodeset, acpi=noirq

3. **Recovery Mode** - Emergency shell
   - Kernel: vmlinuz-kairos
   - Initrd: initramfs-kairos.img
   - Features: single, emergency, systemd.unit=rescue.target

4. **Diagnostics Mode** - Hardware diagnostics
   - Kernel: vmlinuz-kairos
   - Initrd: initramfs-kairos.img
   - Features: nomodeset, loglevel=7

## Kernel Parameters

Key kernel parameters for KAIROS OS:

- `root=LABEL=KAIROS_ROOT` - Root filesystem label
- `rootflags=subvol=@` - Btrfs subvolume mount options
- `ro` - Read-only root (immutable)
- `quiet loglevel=3` - Minimal console output
- `kairos.mode=normal|fallback|recovery|diag` - Boot mode selector
- `skew_tick=1` - High-resolution tick for low latency
- `nohz=on nohz_full=1-7` - Dynamic tick disabling
- `rcu_nocbs=1-7` - RCU callback offloading
- `processor.max_cstate=1` - CPU C-state restriction
- `apparmor=1 security=apparmor` - Mandatory Access Control
- `efi=runtime` - EFI runtime services

## Build Integration

The boot subsystem is configured in Phase 4 (`scripts/phases/04_boot.sh`).
ISO generation is handled in Phase 25 (`scripts/phases/25_iso_generation.sh`).

Limine binaries are stored in `tools/limine/limine-binary/` and integrated during the build process.