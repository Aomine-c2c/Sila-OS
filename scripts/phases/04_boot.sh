#!/usr/bin/env bash
# Phase 4: Boot Process Setup
# Deploys UEFI layout, systemd-boot entries, GRUB2 configurations, Limine, and EFI staging trees into build/rootfs and boot/
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"
LIMINE_DIR="${ROOT_DIR}/tools/limine/limine-binary"

echo "[Phase 4] Configuring KAIROS OS UEFI Boot Subsystems (systemd-boot, GRUB2, Limine, EFI vars)..."

# 1. Create boot directory layout according to Boot Loader Specification (BLS) & UEFI
mkdir -p "${TARGET_ROOTFS}/boot/grub"
mkdir -p "${TARGET_ROOTFS}/boot/loader/entries"
mkdir -p "${TARGET_ROOTFS}/boot/efi/EFI/BOOT"
mkdir -p "${TARGET_ROOTFS}/boot/efi/EFI/kairos"
mkdir -p "${TARGET_ROOTFS}/boot/limine"
mkdir -p "${ROOT_DIR}/boot/loader/entries"
mkdir -p "${ROOT_DIR}/boot/grub"
mkdir -p "${ROOT_DIR}/boot/efi/EFI/BOOT"
mkdir -p "${ROOT_DIR}/boot/efi/EFI/kairos"
mkdir -p "${ROOT_DIR}/boot/limine"

# 2. Deploy GRUB2 configuration
cp "${ROOT_DIR}/config/boot/grub.cfg" "${TARGET_ROOTFS}/boot/grub/grub.cfg"
cp "${ROOT_DIR}/config/boot/grub.cfg" "${ROOT_DIR}/boot/grub/grub.cfg"

# 3. Deploy systemd-boot loader configuration
cp "${ROOT_DIR}/config/boot/loader.conf" "${TARGET_ROOTFS}/boot/loader/loader.conf"
cp "${ROOT_DIR}/config/boot/loader.conf" "${ROOT_DIR}/boot/loader/loader.conf"

# 4. Deploy systemd-boot entries (Normal, Fallback, Recovery, Diag)
for entry in "${ROOT_DIR}/config/boot/entries"/*.conf; do
    if [ -f "$entry" ]; then
        cp "$entry" "${TARGET_ROOTFS}/boot/loader/entries/"
        cp "$entry" "${ROOT_DIR}/boot/loader/entries/"
    fi
done

# 5. Deploy Limine bootloader
echo "[Phase 4] Installing Limine bootloader..."
if [ -d "${LIMINE_DIR}" ]; then
    # Copy Limine EFI binaries to both rootfs and boot directory
    if [ -f "${LIMINE_DIR}/BOOTX64.EFI" ]; then
        cp "${LIMINE_DIR}/BOOTX64.EFI" "${TARGET_ROOTFS}/boot/efi/EFI/BOOT/BOOTX64.EFI"
        cp "${LIMINE_DIR}/BOOTX64.EFI" "${ROOT_DIR}/boot/efi/EFI/BOOT/BOOTX64.EFI"
    fi
    if [ -f "${LIMINE_DIR}/BOOTIA32.EFI" ]; then
        cp "${LIMINE_DIR}/BOOTIA32.EFI" "${TARGET_ROOTFS}/boot/efi/EFI/BOOT/BOOTIA32.EFI"
        cp "${LIMINE_DIR}/BOOTIA32.EFI" "${ROOT_DIR}/boot/efi/EFI/BOOT/BOOTIA32.EFI"
    fi
    
    # Copy Limine BIOS and CD binaries
    if [ -f "${LIMINE_DIR}/limine-bios-hdd.h" ]; then
        cp "${LIMINE_DIR}/limine-bios-hdd.h" "${TARGET_ROOTFS}/boot/limine/limine-bios-hdd.h"
        cp "${LIMINE_DIR}/limine-bios-hdd.h" "${ROOT_DIR}/boot/limine/limine-bios-hdd.h"
    fi
    if [ -f "${LIMINE_DIR}/limine-bios-cd.bin" ]; then
        cp "${LIMINE_DIR}/limine-bios-cd.bin" "${TARGET_ROOTFS}/boot/limine/limine-bios-cd.bin"
        cp "${LIMINE_DIR}/limine-bios-cd.bin" "${ROOT_DIR}/boot/limine/limine-bios-cd.bin"
    fi
    if [ -f "${LIMINE_DIR}/limine-uefi-cd.bin" ]; then
        cp "${LIMINE_DIR}/limine-uefi-cd.bin" "${TARGET_ROOTFS}/boot/limine/limine-uefi-cd.bin"
        cp "${LIMINE_DIR}/limine-uefi-cd.bin" "${ROOT_DIR}/boot/limine/limine-uefi-cd.bin"
    fi
    if [ -f "${LIMINE_DIR}/limine-bios.sys" ]; then
        cp "${LIMINE_DIR}/limine-bios.sys" "${TARGET_ROOTFS}/boot/limine/limine-bios.sys"
        cp "${LIMINE_DIR}/limine-bios.sys" "${ROOT_DIR}/boot/limine/limine-bios.sys"
    fi
    
    # Deploy Limine configuration
    if [ -f "${ROOT_DIR}/config/boot/limine/limine.conf" ]; then
        cp "${ROOT_DIR}/config/boot/limine/limine.conf" "${TARGET_ROOTFS}/boot/limine/limine.conf"
        cp "${ROOT_DIR}/config/boot/limine/limine.conf" "${ROOT_DIR}/boot/limine/limine.conf"
    fi
else
    echo "[Phase 4] Warning: Limine binaries not found at ${LIMINE_DIR}, skipping Limine installation"
fi

# 6. Populate EFI directory structure with reference startup.nsh for UEFI shell
cat << 'EOF' > "${TARGET_ROOTFS}/boot/efi/startup.nsh"
@echo -off
cls
echo "Starting KAIROS Adaptive Trading Operating System..."
vmlinuz-kairos initrd=initramfs-kairos.img root=LABEL=KAIROS_ROOT rootflags=subvol=@ ro quiet loglevel=3 kairos.mode=normal efi=runtime
EOF
cp "${TARGET_ROOTFS}/boot/efi/startup.nsh" "${ROOT_DIR}/boot/efi/startup.nsh"

# 7. Validate configuration files
echo "[Phase 4] Validating boot configuration files..."
test -f "${TARGET_ROOTFS}/boot/loader/loader.conf"
test -f "${TARGET_ROOTFS}/boot/loader/entries/kairos.conf"
test -f "${TARGET_ROOTFS}/boot/loader/entries/kairos-fallback.conf"
test -f "${TARGET_ROOTFS}/boot/loader/entries/kairos-recovery.conf"
test -f "${TARGET_ROOTFS}/boot/loader/entries/kairos-diag.conf"
test -f "${TARGET_ROOTFS}/boot/grub/grub.cfg"
if [ -d "${LIMINE_DIR}" ]; then
    test -f "${TARGET_ROOTFS}/boot/efi/EFI/BOOT/BOOTX64.EFI"
    test -f "${TARGET_ROOTFS}/boot/limine/limine.conf"
fi

echo "[Phase 4] Boot configuration staging successfully completed."
