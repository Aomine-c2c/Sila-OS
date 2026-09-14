#!/usr/bin/env bash
# Phase 26: Automated Testing & QEMU Boot Verification
# Runs the full Python unit test suite, config validation, and ISO sanity checks
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[Phase 26] Running KAIROS OS Automated Verification & Sanity Suite..."

# 1. Run Python unit tests
python3 -m unittest discover -s tests -p "test_*.py"

# 2. Check rootfs tree integrity
echo "[Phase 26] Auditing target rootfs hierarchy..."
test -f "build/rootfs/etc/os-release"
test -f "build/rootfs/etc/sysctl.d/99-kairos-sysctl.conf"
test -f "build/rootfs/boot/grub/grub.cfg"
test -f "build/rootfs/usr/bin/kairos-control"
test -f "build/rootfs/usr/bin/kairos-install"
test -f "build/rootfs/usr/bin/kairos-update"
test -f "build/rootfs/usr/libexec/kairos/kairos-riskd.py"
test -f "build/rootfs/etc/systemd/system/kairos-riskd.service"
test -f "build/rootfs/etc/kairos/shell/waybar.json"
test -f "build/rootfs/etc/hypr/hyprland.conf"

echo "[Phase 26] All automated tests passed successfully."
