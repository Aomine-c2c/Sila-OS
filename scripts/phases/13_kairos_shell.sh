#!/usr/bin/env bash
# Phase 13: KAIROS Shell & Financial Status Bar
# Deploys Waybar configs, financial ticker modules, and risk indicators
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 13] Installing KAIROS Shell & Waybar High-Frequency Dashboard..."

mkdir -p "${TARGET_ROOTFS}/etc/kairos/shell"
mkdir -p "${TARGET_ROOTFS}/var/run/kairos"

cp "${ROOT_DIR}/config/shell/waybar.json" "${TARGET_ROOTFS}/etc/kairos/shell/waybar.json"
cp "${ROOT_DIR}/config/shell/waybar.css" "${TARGET_ROOTFS}/etc/kairos/shell/waybar.css"

# Deploy Command Palette & Shell State IPC Provider
mkdir -p "${TARGET_ROOTFS}/usr/libexec/kairos"
mkdir -p "${TARGET_ROOTFS}/usr/local/bin"
cp "${ROOT_DIR}/scripts/shell/kairos_cmd.py" "${TARGET_ROOTFS}/usr/libexec/kairos/kairos_cmd.py"
cp "${ROOT_DIR}/scripts/shell/kairos_shell_state.py" "${TARGET_ROOTFS}/usr/libexec/kairos/kairos_shell_state.py"
chmod 755 "${TARGET_ROOTFS}/usr/libexec/kairos/kairos_cmd.py" "${TARGET_ROOTFS}/usr/libexec/kairos/kairos_shell_state.py"

# Symlink kairos-cmd to /usr/local/bin/kairos-cmd
ln -sf "/usr/libexec/kairos/kairos_cmd.py" "${TARGET_ROOTFS}/usr/local/bin/kairos-cmd"

# Initialize live risk status indicator file
echo "🛡️ RISK: LOCKED-STABLE (MaxDD: 0.8% | Var: Low)" > "${TARGET_ROOTFS}/var/run/kairos/risk_status.txt"

echo "[Phase 13] KAIROS Shell components successfully staged."
