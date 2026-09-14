#!/usr/bin/env bash
# Phase 19: Trading Infrastructure & Risk Gatekeeper Setup
# Deploys trading risk daemon, library modules, and systemd service into rootfs
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 19] Deploying KAIROS Trading Infrastructure & Immutable Risk Gatekeeper..."

mkdir -p "${TARGET_ROOTFS}/usr/lib/python3.12/site-packages/kairos_trading"
mkdir -p "${TARGET_ROOTFS}/usr/libexec/kairos"
mkdir -p "${TARGET_ROOTFS}/etc/kairos/risk"
mkdir -p "${TARGET_ROOTFS}/etc/systemd/system/multi-user.target.wants"

# Copy python trading packages
cp "${ROOT_DIR}/trading/risk_gatekeeper.py" "${TARGET_ROOTFS}/usr/lib/python3.12/site-packages/kairos_trading/risk_gatekeeper.py"
cp "${ROOT_DIR}/trading/__init__.py" "${TARGET_ROOTFS}/usr/lib/python3.12/site-packages/kairos_trading/__init__.py"

# Deploy kairos-riskd daemon
cp "${ROOT_DIR}/services/kairos-riskd.py" "${TARGET_ROOTFS}/usr/libexec/kairos/kairos-riskd.py"
chmod +x "${TARGET_ROOTFS}/usr/libexec/kairos/kairos-riskd.py"

# Deploy & enable systemd service
cp "${ROOT_DIR}/config/services/kairos-riskd.service" "${TARGET_ROOTFS}/etc/systemd/system/kairos-riskd.service"
ln -sf "/etc/systemd/system/kairos-riskd.service" "${TARGET_ROOTFS}/etc/systemd/system/multi-user.target.wants/kairos-riskd.service"

echo "[Phase 19] Trading infrastructure and Risk Gatekeeper successfully deployed."
