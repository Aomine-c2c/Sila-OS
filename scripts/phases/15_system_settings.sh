#!/usr/bin/env bash
# Phase 15: System Settings & Control Utility
# Deploys kairos-control into /usr/bin of target rootfs
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 15] Deploying kairos-control System Settings & Tuning Utility..."

mkdir -p "${TARGET_ROOTFS}/usr/bin"
cp "${ROOT_DIR}/bin/kairos-control" "${TARGET_ROOTFS}/usr/bin/kairos-control"
chmod +x "${TARGET_ROOTFS}/usr/bin/kairos-control"

echo "[Phase 15] kairos-control successfully installed."
