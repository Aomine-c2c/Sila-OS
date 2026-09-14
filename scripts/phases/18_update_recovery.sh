#!/usr/bin/env bash
# Phase 18: Update and Recovery Subsystem
# Installs kairos-update utility and automatic snapshot hooks into rootfs
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 18] Deploying KAIROS Update and Atomic Snapshot Recovery System..."

mkdir -p "${TARGET_ROOTFS}/usr/bin"
cp "${ROOT_DIR}/bin/kairos-update" "${TARGET_ROOTFS}/usr/bin/kairos-update"
chmod +x "${TARGET_ROOTFS}/usr/bin/kairos-update"

echo "[Phase 18] Update and recovery tools staged."
