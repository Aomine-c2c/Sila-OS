#!/usr/bin/env bash
# Phase 2: Linux Base & FHS Setup
# Creates the Filesystem Hierarchy Standard (FHS) skeleton and base configuration files
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 2] Constructing KAIROS OS FHS tree in ${TARGET_ROOTFS}..."

# FHS standard directory layout
mkdir -p "${TARGET_ROOTFS}"/{bin,sbin,lib,lib64,usr,etc,var,home,root,proc,sys,dev,run,tmp,opt,mnt,media,boot,srv}
mkdir -p "${TARGET_ROOTFS}"/usr/{bin,sbin,lib,lib64,include,share,local}
mkdir -p "${TARGET_ROOTFS}"/etc/{systemd,udev,pam.d,security,kairos,network}
mkdir -p "${TARGET_ROOTFS}"/var/{log,cache,spool,lib,tmp}

# Set safe permissions
chmod 1777 "${TARGET_ROOTFS}/tmp"
chmod 0750 "${TARGET_ROOTFS}/root"

# Deploy os-release
cp "${ROOT_DIR}/config/os-release" "${TARGET_ROOTFS}/etc/os-release"
ln -sf "../etc/os-release" "${TARGET_ROOTFS}/usr/lib/os-release"

# Base hostname & hosts
echo "kairos-node" > "${TARGET_ROOTFS}/etc/hostname"
cat << 'EOF' > "${TARGET_ROOTFS}/etc/hosts"
127.0.0.1   localhost localhost.localdomain kairos-node
::1         localhost localhost.localdomain kairos-node ip6-localhost ip6-loopback
EOF

# Base fstab template
cat << 'EOF' > "${TARGET_ROOTFS}/etc/fstab"
# /etc/fstab: static file system information.
# <file system> <mount point>   <type>  <options>       <dump>  <pass>
LABEL=KAIROS_ROOT  /          btrfs   subvol=@,defaults,noatime,compress=zstd:1 0 0
LABEL=KAIROS_BOOT  /boot      vfat    defaults,noatime,umask=0077               0 2
LABEL=KAIROS_HOME  /home      btrfs   subvol=@home,defaults,noatime             0 0
tmpfs              /tmp       tmpfs   defaults,noatime,mode=1777                0 0
EOF

echo "[Phase 2] Linux Base FHS hierarchy and configuration generated successfully."
