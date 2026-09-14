#!/usr/bin/env bash
# Phase 9: Hardware Support & Driver Integration
# Packages hardware initialization routines and udev rules into rootfs
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 9] Installing Hardware Support and Initialization Infrastructure..."

mkdir -p "${TARGET_ROOTFS}/usr/lib/kairos"
mkdir -p "${TARGET_ROOTFS}/etc/udev/rules.d"

# Copy hardware initialization routine
cp "${ROOT_DIR}/scripts/hardware/kairos-hardware-init.sh" "${TARGET_ROOTFS}/usr/lib/kairos/kairos-hardware-init.sh"
chmod +x "${TARGET_ROOTFS}/usr/lib/kairos/kairos-hardware-init.sh"

# Low latency udev rules (set optimal I/O schedulers: none/mq-deadline for NVMe)
cat << 'EOF' > "${TARGET_ROOTFS}/etc/udev/rules.d/60-kairos-io-scheduler.rules"
# Set none scheduler for NVMe drives to eliminate kernel dispatch overhead
ACTION=="add|change", KERNEL=="nvme[0-9]*", ATTR{queue/scheduler}="none"
# Set mq-deadline for SATA SSDs
ACTION=="add|change", KERNEL=="sd[a-z]", ATTR{queue/rotational}=="0", ATTR{queue/scheduler}="mq-deadline"
EOF

echo "[Phase 9] Hardware detection and NVMe low-latency I/O rules deployed."
