#!/usr/bin/env bash
# KAIROS Bootable Live ISO Generation Engine
# Wraps squashfs compression, EFI payload configuration, and xorriso mastering.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "================================================================================"
echo " ◈ KAIROS OS Bootable Live ISO Mastering Engine"
echo "================================================================================"

# Execute phase 25 ISO mastering script
bash scripts/phases/25_iso_generation.sh

echo "[+] ISO generation completed successfully."
