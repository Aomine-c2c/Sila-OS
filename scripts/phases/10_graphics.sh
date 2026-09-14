#!/usr/bin/env bash
# Phase 10: Graphics Stack Configuration
# Provisions environment variables for Mesa DRI, Vulkan ICDs, DRM/KMS acceleration
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 10] Configuring Mesa, DRM/KMS, and Hardware Accelerated Graphics Stack..."

mkdir -p "${TARGET_ROOTFS}/etc/environment.d"

cat << 'EOF' > "${TARGET_ROOTFS}/etc/environment.d/10-kairos-graphics.conf"
# Hardware acceleration environment for Wayland compositor
LIBVA_DRIVER_NAME=auto
MESA_LOADER_DRIVER_OVERRIDE=
VDPAU_DRIVER=va_gl
WLR_RENDERER=vulkan
WLR_NO_HARDWARE_CURSORS=0
EOF

echo "[Phase 10] Graphics stack environment profiles installed."
