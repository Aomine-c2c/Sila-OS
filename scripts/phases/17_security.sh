#!/usr/bin/env bash
# Phase 17: Security Hardening & Mandatory Access Control
# Deploys AppArmor profiles, kernel sysctl security parameters, and strict file permissions
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 17] Hardening System Security & Enforcing Mandatory Access Control..."

# 1. Staging directories
mkdir -p "${TARGET_ROOTFS}/etc/apparmor.d"
mkdir -p "${TARGET_ROOTFS}/etc/sysctl.d"
mkdir -p "${TARGET_ROOTFS}/etc/kairos/vault"
mkdir -p "${TARGET_ROOTFS}/var/log/audit"

# 2. Deploy AppArmor profile for risk daemon
cp "${ROOT_DIR}/config/security/apparmor.kairos-riskd" "${TARGET_ROOTFS}/etc/apparmor.d/usr.libexec.kairos.kairos-riskd"

# 3. Deploy kernel security sysctl settings
cp "${ROOT_DIR}/config/security/99-kairos-security.conf" "${TARGET_ROOTFS}/etc/sysctl.d/99-kairos-security.conf"

# 4. Enforce strict permissions on security-sensitive assets
chmod 0700 "${TARGET_ROOTFS}/etc/kairos/vault"
chmod 0700 "${TARGET_ROOTFS}/var/log/audit"
chmod 0600 "${TARGET_ROOTFS}/etc/shadow" 2>/dev/null || true
chmod 0644 "${TARGET_ROOTFS}/etc/passwd" 2>/dev/null || true
chmod 0644 "${TARGET_ROOTFS}/etc/group" 2>/dev/null || true
chmod 0440 "${TARGET_ROOTFS}/etc/sudoers.d"/* 2>/dev/null || true
chmod 0644 "${TARGET_ROOTFS}/etc/sysctl.d/99-kairos-security.conf"
chmod 0644 "${TARGET_ROOTFS}/etc/apparmor.d/usr.libexec.kairos.kairos-riskd"

echo "[Phase 17] MAC policies, sysctl kernel hardening, and permissions successfully deployed."
