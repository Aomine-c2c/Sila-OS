#!/usr/bin/env bash
# Phase 23: Adaptive Evolution Intelligence Setup
# Deploys AEI telemetry processor and safe runtime heuristics
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 23] Deploying KAIROS Adaptive Evolution Intelligence Runtime..."

mkdir -p "${TARGET_ROOTFS}/usr/lib/python3.12/site-packages/kairos_adaptive"
mkdir -p "${TARGET_ROOTFS}/etc/kairos/adaptive"

cp "${ROOT_DIR}/adaptive/evolution_engine.py" "${TARGET_ROOTFS}/usr/lib/python3.12/site-packages/kairos_adaptive/evolution_engine.py"
cp "${ROOT_DIR}/adaptive/aei.py" "${TARGET_ROOTFS}/usr/lib/python3.12/site-packages/kairos_adaptive/aei.py"
cp "${ROOT_DIR}/adaptive/adaptive_wheel.py" "${TARGET_ROOTFS}/usr/lib/python3.12/site-packages/kairos_adaptive/adaptive_wheel.py"
cp "${ROOT_DIR}/adaptive/__init__.py" "${TARGET_ROOTFS}/usr/lib/python3.12/site-packages/kairos_adaptive/__init__.py"

# Also stage to /usr/lib/kairos/adaptive for system tools
mkdir -p "${TARGET_ROOTFS}/usr/lib/kairos/adaptive"
cp -r "${ROOT_DIR}/adaptive/"* "${TARGET_ROOTFS}/usr/lib/kairos/adaptive/"

# Stage desktop Adaptive Wheel visual assets
mkdir -p "${TARGET_ROOTFS}/usr/share/kairos/icons"
mkdir -p "${TARGET_ROOTFS}/usr/share/kairos/css"
cp "${ROOT_DIR}/config/desktop/icons/kairos-adaptive-wheel.svg" "${TARGET_ROOTFS}/usr/share/kairos/icons/"
cp "${ROOT_DIR}/config/desktop/adaptive-wheel.css" "${TARGET_ROOTFS}/usr/share/kairos/css/"
cp "${ROOT_DIR}/config/boot/kairos-boot-wheel.txt" "${TARGET_ROOTFS}/etc/kairos/boot-wheel.txt"

echo "[Phase 23] Adaptive Evolution Intelligence successfully staged."
