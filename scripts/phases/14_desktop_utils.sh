#!/usr/bin/env bash
# Phase 14: Desktop Utilities & Configuration
# Deploys Kitty terminal config, Mako notifications, and Wofi launcher profiles
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 14] Installing Desktop Utilities (Kitty, Mako, Wofi)..."

mkdir -p "${TARGET_ROOTFS}/etc/skel/.config/kitty"
mkdir -p "${TARGET_ROOTFS}/etc/skel/.config/mako"
mkdir -p "${TARGET_ROOTFS}/etc/skel/.config/foot"
mkdir -p "${TARGET_ROOTFS}/etc/skel/.config/wofi"

cp "${ROOT_DIR}/config/desktop/kitty.conf" "${TARGET_ROOTFS}/etc/skel/.config/kitty/kitty.conf"
cp "${ROOT_DIR}/config/desktop/mako.conf" "${TARGET_ROOTFS}/etc/skel/.config/mako/config"
cp "${ROOT_DIR}/config/desktop/foot.ini" "${TARGET_ROOTFS}/etc/skel/.config/foot/foot.ini"
cp "${ROOT_DIR}/config/desktop/wofi.css" "${TARGET_ROOTFS}/etc/skel/.config/wofi/style.css"

# Also place in system-wide /etc
mkdir -p "${TARGET_ROOTFS}/etc/xdg/foot" "${TARGET_ROOTFS}/etc/xdg/mako" "${TARGET_ROOTFS}/etc/wofi"
cp "${ROOT_DIR}/config/desktop/foot.ini" "${TARGET_ROOTFS}/etc/xdg/foot/foot.ini"
cp "${ROOT_DIR}/config/desktop/mako.conf" "${TARGET_ROOTFS}/etc/xdg/mako/config"
cp "${ROOT_DIR}/config/desktop/wofi.css" "${TARGET_ROOTFS}/etc/wofi/style.css"

echo "[Phase 14] Desktop utilities successfully provisioned."
