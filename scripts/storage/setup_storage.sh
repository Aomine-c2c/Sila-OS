#!/usr/bin/env bash
# KAIROS Storage Partitioning, Encryption & Subvolume Provisioner
# Standards: GPT + EFI (FAT32) + Optional LUKS2 (Argon2id) + Btrfs Subvolumes
#
# SAFETY INVARIANT:
# Never format or alter block devices without explicit confirmation:
#   --confirm-destructive-format
set -euo pipefail

TARGET_DISK="${1:-/dev/null}"
DRY_RUN="${2:-true}"
ENABLE_ENCRYPTION="${3:-false}"
ENABLE_DATA_SUBVOL="${4:-false}"
CONFIRMATION="${5:-false}"

echo "================================================================================"
echo " ◈ KAIROS OS Storage Architecture Provisioner"
echo " Target Disk       : ${TARGET_DISK}"
echo " Dry Run Mode      : ${DRY_RUN}"
echo " Encryption (LUKS2): ${ENABLE_ENCRYPTION}"
echo " Data Subvolume    : ${ENABLE_DATA_SUBVOL}"
echo " Confirmation Flag : ${CONFIRMATION}"
echo "================================================================================"

# Subvolume layout specification
SUBVOLUMES=(
    "@:Root OS Tree (Read-only capable for transactions)"
    "@home:User Home Directories & Research Workspaces"
    "@snapshots:Transactional Rollback & Recovery Point Data"
    "@var_log:Persistent System Audit & Latency Telemetry Logs"
    "@vault:Encrypted High-Security Trading Credential Store"
)

if [[ "$ENABLE_DATA_SUBVOL" == "true" ]]; then
    SUBVOLUMES+=("@data:High-throughput quantitative tick database & market cache")
fi

echo "[*] Target Subvolume Architecture:"
for entry in "${SUBVOLUMES[@]}"; do
    subvol="${entry%%:*}"
    desc="${entry#*:}"
    printf "  - %-15s : %s\n" "$subvol" "$desc"
done

# Enforce Dry-Run Safety
if [[ "$DRY_RUN" == "true" ]]; then
    echo ""
    echo "[+] DRY RUN MODE ACTIVE: Verifying partitioning syntax & layout."
    echo "[+] No destructive changes were written to any block device."
    echo "[+] Pass --confirm-destructive-format to write to real target device."
    exit 0
fi

# Mandatory Destructive Action Gate
if [[ "$CONFIRMATION" != "--confirm-destructive-format" ]]; then
    echo ""
    echo "[!] CRITICAL ERROR: Destructive disk format operation blocked!"
    echo "    To overwrite ${TARGET_DISK}, you MUST explicitly pass the flag:"
    echo "    --confirm-destructive-format"
    echo "    Refusing to alter storage device."
    exit 1
fi

if [[ ! -b "$TARGET_DISK" && ! -f "$TARGET_DISK" ]]; then
    echo "[!] Error: Target ${TARGET_DISK} is not a valid block device or image file."
    exit 1
fi

echo "[*] Initializing GPT partition table on ${TARGET_DISK}..."
parted -s "$TARGET_DISK" mklabel gpt
parted -s "$TARGET_DISK" mkpart "ESP" fat32 1MiB 513MiB
parted -s "$TARGET_DISK" set 1 esp on
parted -s "$TARGET_DISK" mkpart "KAIROS_DATA" 513MiB 100%

# Determine partition names (handles loop0p1 vs sda1)
if [[ "$TARGET_DISK" =~ [0-9]$ ]]; then
    PART_ESP="${TARGET_DISK}p1"
    PART_ROOT="${TARGET_DISK}p2"
else
    PART_ESP="${TARGET_DISK}1"
    PART_ROOT="${TARGET_DISK}2"
fi

echo "[*] Formatting EFI System Partition (FAT32) -> ${PART_ESP}..."
mkfs.vfat -F32 -n "KAIROS_BOOT" "$PART_ESP"

BTRFS_TARGET="$PART_ROOT"
CRYPT_NAME="kairos-crypt"

# Handle LUKS2 Full Disk Encryption
if [[ "$ENABLE_ENCRYPTION" == "true" ]]; then
    echo "[*] Initializing LUKS2 Encryption Container on ${PART_ROOT}..."
    PASSPHRASE="${KAIROS_CRYPT_PASSPHRASE:-kairos}"
    echo -n "$PASSPHRASE" | cryptsetup luksFormat --type luks2 --cipher aes-xts-plain64 --key-size 512 --hash sha512 --pbkdf argon2id "$PART_ROOT" -
    echo "[*] Opening LUKS2 Encrypted Volume as /dev/mapper/${CRYPT_NAME}..."
    echo -n "$PASSPHRASE" | cryptsetup open "$PART_ROOT" "$CRYPT_NAME" -
    BTRFS_TARGET="/dev/mapper/${CRYPT_NAME}"
fi

echo "[*] Formatting Btrfs Filesystem on ${BTRFS_TARGET}..."
mkfs.btrfs -f -L "KAIROS_ROOT" "$BTRFS_TARGET"

echo "[*] Creating Transactional Subvolume Hierarchy..."
MNT_DIR=$(mktemp -d)
mount -o rw,noatime,compress=zstd:1,space_cache=v2 "$BTRFS_TARGET" "$MNT_DIR"

btrfs subvolume create "$MNT_DIR/@"
btrfs subvolume create "$MNT_DIR/@home"
btrfs subvolume create "$MNT_DIR/@snapshots"
btrfs subvolume create "$MNT_DIR/@var_log"
btrfs subvolume create "$MNT_DIR/@vault"

if [[ "$ENABLE_DATA_SUBVOL" == "true" ]]; then
    btrfs subvolume create "$MNT_DIR/@data"
fi

umount "$MNT_DIR"
rm -rf "$MNT_DIR"

if [[ "$ENABLE_ENCRYPTION" == "true" ]]; then
    echo "[*] Closing LUKS2 container..."
    cryptsetup close "$CRYPT_NAME"
fi

echo "================================================================================"
echo " ◈ KAIROS Storage Architecture Provisioned Successfully"
echo "================================================================================"
