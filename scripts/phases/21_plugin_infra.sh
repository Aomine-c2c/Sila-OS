#!/usr/bin/env bash
# Phase 21: Plugin Infrastructure Deployment
# Installs capability-sandboxed plugin manager and API definitions
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 21] Installing KAIROS Capability-Based Plugin Infrastructure..."

mkdir -p "${TARGET_ROOTFS}/usr/lib/python3.12/site-packages/kairos_plugins"
mkdir -p "${TARGET_ROOTFS}/etc/kairos/plugins.d"

cp "${ROOT_DIR}/plugins/plugin_host.py" "${TARGET_ROOTFS}/usr/lib/python3.12/site-packages/kairos_plugins/plugin_host.py"
cp "${ROOT_DIR}/plugins/__init__.py" "${TARGET_ROOTFS}/usr/lib/python3.12/site-packages/kairos_plugins/__init__.py"

echo "[Phase 21] Plugin infrastructure provisioned."
