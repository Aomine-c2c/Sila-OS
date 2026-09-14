#!/usr/bin/env bash
# Phase 22: AI Agent Framework Deployment
# Deploys AI reasoning runtime with mandatory Risk Gatekeeper integration
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 22] Deploying KAIROS AI Agent Runtime with Hard Risk Isolation..."

mkdir -p "${TARGET_ROOTFS}/usr/lib/python3.12/site-packages/kairos_ai"
mkdir -p "${TARGET_ROOTFS}/etc/kairos/ai"

cp "${ROOT_DIR}/ai/agent_harness.py" "${TARGET_ROOTFS}/usr/lib/python3.12/site-packages/kairos_ai/agent_harness.py"
cp "${ROOT_DIR}/ai/__init__.py" "${TARGET_ROOTFS}/usr/lib/python3.12/site-packages/kairos_ai/__init__.py"

echo "[Phase 22] AI Agent subsystem deployed and verified."
