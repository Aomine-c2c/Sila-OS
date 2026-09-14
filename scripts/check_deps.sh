#!/usr/bin/env bash
# KAIROS Dependency Checking Engine
# Audits required tools for building, testing, mastering, and booting KAIROS OS.
set -euo pipefail

echo "================================================================================"
echo " ◈ KAIROS OS Dependency Verification"
echo "================================================================================"

MISSING_CORE=0
MISSING_OPTIONAL=0

check_tool() {
    local tool="$1"
    local category="$2"
    local status="Available"
    
    if ! command -v "$tool" >/dev/null 2>&1; then
        status="MISSING"
        if [[ "$category" == "CORE" ]]; then
            MISSING_CORE=$((MISSING_CORE + 1))
        else
            MISSING_OPTIONAL=$((MISSING_OPTIONAL + 1))
        fi
        printf "  [!] %-22s [%s] : %s\n" "$tool" "$category" "$status"
    else
        printf "  [+] %-22s [%s] : %s (%s)\n" "$tool" "$category" "$status" "$(which "$tool")"
    fi
}

echo "[*] Core System Tools:"
check_tool "bash" "CORE"
check_tool "python3" "CORE"
check_tool "tar" "CORE"
check_tool "gzip" "CORE"
check_tool "make" "CORE"

echo ""
echo "[*] Packaging & ISO Mastering Tools:"
check_tool "mksquashfs" "CORE"
check_tool "xorriso" "CORE"
check_tool "btrfs" "OPTIONAL"

echo ""
echo "[*] Virtualization & Emulation Tools:"
check_tool "qemu-system-x86_64" "OPTIONAL"
check_tool "qemu-img" "OPTIONAL"

echo "================================================================================"
if [[ $MISSING_CORE -gt 0 ]]; then
    echo "[!] Result: $MISSING_CORE mandatory core tool(s) missing. Install missing tools or run via build container."
    exit 1
else
    echo "[+] Result: All mandatory build dependencies are satisfied."
    if [[ $MISSING_OPTIONAL -gt 0 ]]; then
        echo "[*] Note: $MISSING_OPTIONAL optional tool(s) missing (e.g. QEMU). VM testing will be skipped if unavailable."
    fi
    exit 0
fi
