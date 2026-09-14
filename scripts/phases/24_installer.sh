#!/usr/bin/env bash
# Phase 24: Installer Packaging
# Deploys kairos-install into the rootfs and prepares installer profile
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 24] Packaging KAIROS OS Automated Installer..."

mkdir -p "${TARGET_ROOTFS}/usr/bin"
cp "${ROOT_DIR}/bin/kairos-install" "${TARGET_ROOTFS}/usr/bin/kairos-install"
chmod +x "${TARGET_ROOTFS}/usr/bin/kairos-install"

echo "[Phase 24] Installer packaged successfully."
