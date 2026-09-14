#!/usr/bin/env bash
# KAIROS Orchestrated Build Runner
# Drives the build pipeline sequentially through components or target phases.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TARGET="${1:-all}"

echo "================================================================================"
echo " ◈ KAIROS OS Build System Engine"
echo " Target : ${TARGET}"
echo "================================================================================"

# Validate environment and dependencies first
bash scripts/env_detect.sh
bash scripts/check_deps.sh

# Run targets
case "$TARGET" in
    base)
        echo "[*] Building Base Rootfs..."
        bash scripts/phases/02_linux_base.sh
        ;;
    kernel)
        echo "[*] Staging Low-Latency Kernel Configuration..."
        bash scripts/phases/03_kernel.sh
        ;;
    boot)
        echo "[*] Staging UEFI Boot Components..."
        bash scripts/phases/04_boot.sh
        ;;
    desktop)
        echo "[*] Staging Wayland and Hyprland Desktop Environment..."
        bash scripts/phases/11_wayland.sh
        bash scripts/phases/12_hyprland.sh
        bash scripts/phases/13_kairos_shell.sh
        bash scripts/phases/14_desktop_utils.sh
        ;;
    trading)
        echo "[*] Staging Trading Services and Risk Gatekeeper..."
        bash scripts/phases/19_trading_services.sh
        ;;
    iso)
        echo "[*] Mastering KAIROS Live ISO..."
        bash scripts/iso_generate.sh
        ;;
    all)
        echo "[*] Executing complete sequential build pipeline..."
        make build-all
        ;;
    *)
        echo "[!] Unknown build target '$TARGET'. Valid targets: base, kernel, boot, desktop, trading, iso, all."
        exit 1
        ;;
esac

echo "[+] Build step '${TARGET}' finished successfully."
