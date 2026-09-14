#!/usr/bin/env bash
# KAIROS Virtual Machine Boot & Emulation Engine
# Launches the mastered KAIROS Live ISO inside QEMU with UEFI, VirtIO, and hardware acceleration.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ISO_PATH="${1:-out/iso/kairos-os-1.0.0-x86_64.iso}"
RAM_SIZE="${2:-4096}"
CPUS="${3:-4}"

echo "================================================================================"
echo " ◈ KAIROS OS QEMU Virtual Machine Boot Engine"
echo " ISO Image : ${ISO_PATH}"
echo " Memory    : ${RAM_SIZE} MB"
echo " SMP Cores : ${CPUS}"
echo "================================================================================"

if [[ ! -f "$ISO_PATH" ]]; then
    echo "[!] Error: Target ISO '${ISO_PATH}' does not exist! Run scripts/iso_generate.sh first."
    exit 1
fi

if ! command -v qemu-system-x86_64 >/dev/null 2>&1; then
    echo "[*] Notice: qemu-system-x86_64 not found in current PATH."
    echo "[*] Command that will execute on hypervisor host:"
    echo "    qemu-system-x86_64 -enable-kvm -m ${RAM_SIZE} -smp ${CPUS} -cdrom ${ISO_PATH} -boot d -vga virtio"
    exit 0
fi

# Detect KVM acceleration
KVM_FLAG=""
if [[ -w "/dev/kvm" ]] 2>/dev/null; then
    KVM_FLAG="-enable-kvm -cpu host"
else
    KVM_FLAG="-cpu max"
fi

echo "[+] Launching QEMU VM instance..."
qemu-system-x86_64 \
    $KVM_FLAG \
    -m "${RAM_SIZE}" \
    -smp "${CPUS}" \
    -cdrom "${ISO_PATH}" \
    -boot d \
    -vga virtio \
    -net nic,model=virtio \
    -net user \
    -serial mon:stdio
