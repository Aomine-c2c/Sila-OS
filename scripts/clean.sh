#!/usr/bin/env bash
# KAIROS Workspace Clean Engine
# Cleans build artifacts, caches, and intermediate outputs safely.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

MODE="${1:-all}"

echo "================================================================================"
echo " ◈ KAIROS OS Workspace Cleaner"
echo " Mode: ${MODE}"
echo "================================================================================"

case "$MODE" in
    cache)
        echo "[*] Cleaning temporary Python cache and logs..."
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete 2>/dev/null || true
        ;;
    build)
        echo "[*] Purging build/ intermediate tree..."
        rm -rf build/*
        ;;
    out)
        echo "[*] Purging out/ release directory..."
        rm -rf out/*
        ;;
    all)
        echo "[*] Purging build/, out/, and temporary caches..."
        rm -rf build out
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -type f -name "*.pyc" -delete 2>/dev/null || true
        mkdir -p build/rootfs build/iso out/iso out/release
        ;;
    *)
        echo "[!] Unknown clean mode '$MODE'. Valid modes: cache, build, out, all."
        exit 1
        ;;
esac

echo "[+] Clean operation completed."
