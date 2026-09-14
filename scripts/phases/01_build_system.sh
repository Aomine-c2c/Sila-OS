#!/usr/bin/env bash
# Phase 1: Build System Initialization
# Validates container runtime, toolchain, and prepares hermetic build runner
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[Phase 1] Initializing KAIROS OS hermetic build environment..."

# Verify python test suite and architecture rules
python3 tests/test_architecture.py

echo "[Phase 1] Validating build directories..."
mkdir -p build/rootfs
mkdir -p build/iso
mkdir -p out/iso
mkdir -p out/packages
mkdir -p config

echo "[Phase 1] Checking container build definition..."
if [[ ! -f "docker/Containerfile.build" ]]; then
    echo "[!] Error: docker/Containerfile.build is missing!" >&2
    exit 1
fi

echo "[Phase 1] Hermetic build runner is configured and ready."
