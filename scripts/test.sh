#!/usr/bin/env bash
# KAIROS Automated Test Suite Runner
# Executes architectural invariant checks, Python unit tests, and security tests.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "================================================================================"
echo " ◈ KAIROS OS Automated Test Suite"
echo "================================================================================"

# Execute Python unit and integration tests
python3 -m unittest discover -s tests -p "test_*.py"

echo "================================================================================"
echo "[+] All KAIROS OS architectural and unit tests passed successfully."
