#!/usr/bin/env bash
# Phase 16: Package Management & Application Sandboxing (Arch Linux Base)
# Configures pacman package management, sandbox rules, and isolation profiles
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 16] Deploying Arch Linux Package Management and Application Sandbox Policies..."

# Create directory structure
mkdir -p "${TARGET_ROOTFS}/etc/kairos/sandbox"
mkdir -p "${TARGET_ROOTFS}/etc/kairos/packages"
mkdir -p "${TARGET_ROOTFS}/usr/share/kairos/packages"
mkdir -p "${TARGET_ROOTFS}/etc/pacman.d"
mkdir -p "${TARGET_ROOTFS}/var/lib/pacman"

# Deploy sandbox policies
cp "${ROOT_DIR}/config/packages/sandbox.ini" "${TARGET_ROOTFS}/etc/kairos/sandbox/sandbox.ini"

# Deploy package manifest
cp "${ROOT_DIR}/packages/manifests/packages.json" "${TARGET_ROOTFS}/usr/share/kairos/packages/packages.json"
ln -sf "/usr/share/kairos/packages/packages.json" "${TARGET_ROOTFS}/etc/kairos/packages/packages.json"

# Configure pacman for KAIROS OS
cat << 'EOF' > "${TARGET_ROOTFS}/etc/pacman.conf"
# KAIROS OS Pacman Configuration
# Arch Linux-based package manager configuration

[options]
RootDir = /var/lib/pacman
CacheDir = /var/cache/pacman/pkg
HoldPkg = pacman glibc
SyncDir = /var/lib/pacman/sync
LogFile = /var/log/pacman.log
GPGDir = /etc/pacman.d/gnupg
Architecture = native
Color = always
CheckSpace
VerbosePkgLists
UseSysroot = /

[core]
Server = https://archive.archlinux.org/core/os/x86_64
Server = https://mirror.rackspace.com/archlinux/core/os/x86_64

[extra]
Server = https://archive.archlinux.org/extra/os/x86_64
Server = https://mirror.rackspace.com/archlinux/extra/os/x86_64

[community]
Server = https://archive.archlinux.org/community/os/x86_64
Server = https://mirror.rackspace.com/archlinux/community/os/x86_64

[multilib]
Server = https://archive.archlinux.org/multilib/os/x86_64
Server = https://mirror.rackspace.com/archlinux/multilib/os/x86_64

[multilib-testing]
Server = https://archive.archlinux.org/multilib-testing/os/x86_64

[nonprism]
Server = https://archlinux.org/nonprism/os/x86_64
EOF

# Create pacman hooks for KAIROS
mkdir -p "${TARGET_ROOTFS}/usr/share/libalpm/hooks"

cat << 'EOF' > "${TARGET_ROOTFS}/usr/share/libalpm/hooks/kairos-immutable.hook"
# KAIROS Immutable System Hook
# Prevents package removal of immutable components
[trigger]
type = package
operation = remove
target = kairos-*

[action]
description = Preventing removal of KAIROS immutable package
when = pretransaction
exec = /usr/bin/kairos-protect %t %n
EOF

echo "[Phase 16] Arch Linux package management and sandboxing policies configured."