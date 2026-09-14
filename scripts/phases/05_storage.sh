#!/usr/bin/env bash
# Phase 5: Storage Architecture & Subvolume Setup
# Validates storage scripts, zram configuration, fstab generation, and safe failure handling.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 5] Deploying KAIROS Storage Architecture & zram Swap Configuration..."

# 1. Validate storage provisioner script dry-run safety
bash "${ROOT_DIR}/scripts/storage/setup_storage.sh" /dev/null true false true

# 2. Configure zram-generator for compressed in-RAM swap (prevents disk paging latency spikes)
mkdir -p "${TARGET_ROOTFS}/etc/systemd/zram-generator.conf.d"
cat << 'EOF' > "${TARGET_ROOTFS}/etc/systemd/zram-generator.conf.d/zram.conf"
[zram0]
zram-size = min(ram / 2, 8192)
compression-algorithm = zstd
swap-priority = 100
fs-type = swap
EOF

# 3. Configure production Btrfs subvolume fstab template with safe mount options
cat << 'EOF' > "${TARGET_ROOTFS}/etc/fstab"
# /etc/fstab: KAIROS OS Subvolume Mount Table
# <file system>             <mount point>       <type>  <options>                                                               <dump>  <pass>
LABEL=KAIROS_BOOT           /boot/efi           vfat    umask=0077,shortname=winnt,errors=remount-ro                            0       2
LABEL=KAIROS_ROOT           /                   btrfs   subvol=@,rw,noatime,compress=zstd:1,space_cache=v2,errors=remount-ro    0       0
LABEL=KAIROS_ROOT           /home               btrfs   subvol=@home,rw,noatime,compress=zstd:1,space_cache=v2                  0       0
LABEL=KAIROS_ROOT           /.snapshots         btrfs   subvol=@snapshots,rw,noatime,compress=zstd:1,space_cache=v2             0       0
LABEL=KAIROS_ROOT           /var/log            btrfs   subvol=@var_log,rw,noatime,compress=zstd:1,space_cache=v2               0       0
LABEL=KAIROS_ROOT           /var/kairos/vault   btrfs   subvol=@vault,rw,noatime,compress=zstd:1,space_cache=v2                 0       0
tmpfs                       /tmp                tmpfs   defaults,nosuid,nodev,noexec,size=4G                                    0       0
EOF

# 4. Deploy storage management scripts to system binary paths
mkdir -p "${TARGET_ROOTFS}/usr/local/bin"
cp "${ROOT_DIR}/scripts/storage/setup_storage.sh" "${TARGET_ROOTFS}/usr/local/bin/kairos-storage-setup"
cp "${ROOT_DIR}/scripts/storage/kairos_storage.py" "${TARGET_ROOTFS}/usr/local/bin/kairos-storage-mgr"
chmod +x "${TARGET_ROOTFS}/usr/local/bin/kairos-storage-setup" "${TARGET_ROOTFS}/usr/local/bin/kairos-storage-mgr"

echo "[Phase 5] Storage architecture and memory tiering configuration successfully deployed."
