#!/usr/bin/env bash
# Phase 12: Hyprland Configuration and Setup
# Deploys KAIROS Hyprland profile into system skel and target rootfs
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 12] Deploying KAIROS Hyprland Configuration & Financial Workspaces..."

mkdir -p "${TARGET_ROOTFS}/etc/skel/.config/hypr"
mkdir -p "${TARGET_ROOTFS}/etc/hypr"

cp "${ROOT_DIR}/config/hyprland/hyprland.conf" "${TARGET_ROOTFS}/etc/skel/.config/hypr/hyprland.conf"
cp "${ROOT_DIR}/config/hyprland/hyprland.conf" "${TARGET_ROOTFS}/etc/hypr/hyprland.conf"

# Deploy session supervisor & watchdog
mkdir -p "${TARGET_ROOTFS}/usr/libexec/kairos"
cp "${ROOT_DIR}/scripts/hardware/kairos-session-watchdog.sh" "${TARGET_ROOTFS}/usr/libexec/kairos/kairos-session-watchdog.sh"
chmod 755 "${TARGET_ROOTFS}/usr/libexec/kairos/kairos-session-watchdog.sh"

echo "[Phase 12] Hyprland desktop environment configured successfully."
