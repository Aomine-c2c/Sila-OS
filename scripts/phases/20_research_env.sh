#!/usr/bin/env bash
# Phase 20: Research Environment Provisioning
# Prepares quantitative analytics directories, parquet cache directories, and profiles
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 20] Setting up Quantitative Research & Analytics Workspace..."

mkdir -p "${TARGET_ROOTFS}/etc/kairos/research"
mkdir -p "${TARGET_ROOTFS}/var/cache/kairos/market_data"
chmod 1777 "${TARGET_ROOTFS}/var/cache/kairos/market_data"

cp "${ROOT_DIR}/config/research/research_env.ini" "${TARGET_ROOTFS}/etc/kairos/research/research_env.ini"

echo "[Phase 20] Research environment staged successfully."
