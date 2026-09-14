#!/usr/bin/env bash
# Phase 11: Wayland Protocols and Compositor Session
# Installs wayland session desktop definitions and environment profiles
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 11] Setting up Wayland Session and Display Protocols..."

mkdir -p "${TARGET_ROOTFS}/usr/share/wayland-sessions"
cp "${ROOT_DIR}/config/wayland/kairos-hyprland.desktop" "${TARGET_ROOTFS}/usr/share/wayland-sessions/hyprland.desktop"

# Environment variables for Wayland desktop
mkdir -p "${TARGET_ROOTFS}/etc/environment.d"
cat << 'EOF' > "${TARGET_ROOTFS}/etc/environment.d/20-kairos-wayland.conf"
XDG_CURRENT_DESKTOP=Hyprland
XDG_SESSION_TYPE=wayland
XDG_SESSION_DESKTOP=Hyprland
QT_QPA_PLATFORM=wayland;xcb
QT_WAYLAND_DISABLE_WINDOWDECORATION=1
GDK_BACKEND=wayland,x11
CLUTTER_BACKEND=wayland
SDL_VIDEODRIVER=wayland
_JAVA_AWT_WM_NONREPARENTING=1
XCURSOR_THEME=Adwaita
XCURSOR_SIZE=24
HYPRCURSOR_THEME=Adwaita
HYPRCURSOR_SIZE=24
MOZ_ENABLE_WAYLAND=1
ELECTRON_OZONE_PLATFORM_HINT=wayland
EOF

echo "[Phase 11] Wayland session configuration staged."
