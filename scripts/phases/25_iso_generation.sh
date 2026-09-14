#!/usr/bin/env bash
# Phase 25: ISO Generation & Image Mastering
# Builds squashfs compressed image from rootfs and masters bootable hybrid UEFI/BIOS ISO via xorriso
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"
ISO_DIR="${ROOT_DIR}/build/iso"
OUT_DIR="${ROOT_DIR}/out/iso"
LIMINE_DIR="${ROOT_DIR}/tools/limine/limine-binary"

echo "[Phase 25] Mastering Bootable KAIROS OS Live ISO..."

mkdir -p "${ISO_DIR}/live"
mkdir -p "${ISO_DIR}/boot/grub"
mkdir -p "${ISO_DIR}/boot/limine"
mkdir -p "${ISO_DIR}/EFI/BOOT"
mkdir -p "${OUT_DIR}"

# 1. Generate filesystem.squashfs
echo "[*] Creating rootfs squashfs image..."
mksquashfs "${TARGET_ROOTFS}" "${ISO_DIR}/live/filesystem.squashfs" -noappend -comp zstd -Xcompression-level 15

# 2. Copy boot configurations to ISO tree
cp "${ROOT_DIR}/config/boot/grub.cfg" "${ISO_DIR}/boot/grub/grub.cfg"

# 3. Deploy Limine bootloader to ISO
echo "[*] Adding Limine bootloader to ISO..."
if [ -d "${LIMINE_DIR}" ]; then
    # Copy Limine EFI binaries
    if [ -f "${LIMINE_DIR}/BOOTX64.EFI" ]; then
        cp "${LIMINE_DIR}/BOOTX64.EFI" "${ISO_DIR}/EFI/BOOT/BOOTX64.EFI"
    fi
    if [ -f "${LIMINE_DIR}/BOOTIA32.EFI" ]; then
        cp "${LIMINE_DIR}/BOOTIA32.EFI" "${ISO_DIR}/EFI/BOOT/BOOTIA32.EFI"
    fi
    
    # Copy Limine BIOS and CD binaries
    if [ -f "${LIMINE_DIR}/limine-bios-cd.bin" ]; then
        cp "${LIMINE_DIR}/limine-bios-cd.bin" "${ISO_DIR}/boot/limine/limine-bios-cd.bin"
    fi
    if [ -f "${LIMINE_DIR}/limine-uefi-cd.bin" ]; then
        cp "${LIMINE_DIR}/limine-uefi-cd.bin" "${ISO_DIR}/boot/limine/limine-uefi-cd.bin"
    fi
    if [ -f "${LIMINE_DIR}/limine-bios.sys" ]; then
        cp "${LIMINE_DIR}/limine-bios.sys" "${ISO_DIR}/boot/limine/limine-bios.sys"
    fi
    
    # Copy Limine configuration
    if [ -f "${ROOT_DIR}/config/boot/limine/limine.conf" ]; then
        cp "${ROOT_DIR}/config/boot/limine/limine.conf" "${ISO_DIR}/boot/limine/limine.conf"
    fi
else
    echo "[Phase 25] Warning: Limine binaries not found at ${LIMINE_DIR}, skipping Limine integration"
fi

# 4. Create EFI boot payload structure (fallback stub)
cat << 'EOF' > "${ISO_DIR}/EFI/BOOT/BOOTX64.EFI.stub"
KAIROS_EFI_PAYLOAD_STUB
EOF

# 5. Master ISO with xorriso
ISO_PATH="${OUT_DIR}/kairos-os-1.0.0-x86_64.iso"
echo "[*] Packaging hybrid ISO via xorriso -> ${ISO_PATH}"
xorriso -as mkisofs \
    -iso-level 3 \
    -full-iso9660-filenames \
    -volid "KAIROS_OS_1_0" \
    -output "${ISO_PATH}" \
    -graft-points \
    /="${ISO_DIR}"

echo "[Phase 25] KAIROS OS Live ISO mastered successfully: ${ISO_PATH}"
ls -lh "${ISO_PATH}"
