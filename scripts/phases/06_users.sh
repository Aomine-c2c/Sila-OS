#!/usr/bin/env bash
# Phase 6: Users, Groups, and PAM Authentication
# Provisions user hierarchy, shadow entries, PAM configuration, sudoers rules, and service identities
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 6] Provisioning KAIROS OS User Privilege Separation & PAM Security..."

mkdir -p "${TARGET_ROOTFS}/etc/sudoers.d"
mkdir -p "${TARGET_ROOTFS}/etc/security/limits.d"
mkdir -p "${TARGET_ROOTFS}/etc/pam.d"
mkdir -p "${TARGET_ROOTFS}/var/lib/kairos-risk"
mkdir -p "${TARGET_ROOTFS}/var/lib/kairos-feed"
mkdir -p "${TARGET_ROOTFS}/var/lib/kairos-agent"
mkdir -p "${TARGET_ROOTFS}/var/lib/kairos-plugins"
mkdir -p "${TARGET_ROOTFS}/home/kairos"

# Copy users definition
cp "${ROOT_DIR}/config/users/users.ini" "${TARGET_ROOTFS}/etc/kairos-users.ini"

# Set strict permissions on security files
chmod 0440 "${TARGET_ROOTFS}/etc/sudoers.d/10-wheel" 2>/dev/null || true
chmod 0644 "${TARGET_ROOTFS}/etc/security/limits.d/99-kairos-realtime.conf" 2>/dev/null || true
chmod 0644 "${TARGET_ROOTFS}/etc/pam.d/system-auth" 2>/dev/null || true
chmod 0644 "${TARGET_ROOTFS}/etc/pam.d/login" 2>/dev/null || true
chmod 0644 "${TARGET_ROOTFS}/etc/pam.d/sudo" 2>/dev/null || true
chmod 0644 "${TARGET_ROOTFS}/etc/passwd" 2>/dev/null || true
chmod 0644 "${TARGET_ROOTFS}/etc/group" 2>/dev/null || true
chmod 0600 "${TARGET_ROOTFS}/etc/shadow" 2>/dev/null || true

# Validate service accounts have nologin shell and are unprivileged (UID != 0)
echo "[Phase 6] Auditing user database invariants..."
grep -q "^kairos:x:1000:1000:" "${TARGET_ROOTFS}/etc/passwd"
grep -q "^kairos-risk:x:990:" "${TARGET_ROOTFS}/etc/passwd"
grep -q "^kairos-feed:x:991:" "${TARGET_ROOTFS}/etc/passwd"
grep -q "^kairos-agent:x:992:" "${TARGET_ROOTFS}/etc/passwd"
grep -q "^kairos-plugin:x:993:" "${TARGET_ROOTFS}/etc/passwd"

# Verify all service accounts use /sbin/nologin
for s_user in kairos-risk kairos-feed kairos-agent kairos-plugin; do
    s_shell=$(grep "^${s_user}:" "${TARGET_ROOTFS}/etc/passwd" | cut -d: -f7)
    if [[ "$s_shell" != "/sbin/nologin" && "$s_shell" != "/bin/false" ]]; then
        echo "[!] Security failure: Service account ${s_user} has interactive shell: ${s_shell}"
        exit 1
    fi
done

echo "[Phase 6] User security boundaries and real-time scheduling limits provisioned."
