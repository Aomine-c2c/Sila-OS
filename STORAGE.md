# KAIROS OS Storage Architecture & Specification

## 1. Executive Summary & Strategy
The KAIROS storage architecture is designed to support the demanding workloads of quantitative researchers, algorithmic traders, and autonomous market operators. It guarantees **deterministic I/O latency**, **fail-safe transactional rollbacks**, **hardware-rooted credential protection**, and **non-destructive operational safety**.

### Core Storage Invariants
1. **Safety First**: Destructive disk operations (`mkfs`, `parted`, `cryptsetup format`) are **strictly blocked** by default and require explicit confirmation (`--confirm-destructive-format`). Never wipe disks automatically.
2. **UEFI / GPT Standard**: Modern systems use GPT partition tables with a dedicated FAT32 EFI System Partition (ESP).
3. **Btrfs Subvolume Layering**: All runtime state is organized into isolated Btrfs subvolumes, enabling sub-second snapshot rollbacks without reinstalling the OS.
4. **Transparent Full-Disk Encryption (LUKS2)**: Encryption is applied at the block device level between the physical partition and the filesystem. Enabling encryption does not alter the higher-level OS architecture, subvolume tree, or mount structure.
5. **Fail-Safe Recovery**: Filesystems mount with `errors=remount-ro` to prevent metadata corruption during hardware faults or power cuts. In-RAM compressed swap (`zram`) prevents swapping latency spikes.

---

## 2. Partition Layout

Every KAIROS disk is initialized with a GUID Partition Table (GPT):

| Partition | Type GUID / Name | Filesystem | Recommended Size | Mount Point | Description |
|---|---|---|---|---|---|
| **1** | `C12A7328-F81F-11D2-BA4B-00A0C93EC93B` (ESP) | FAT32 (`vfat`) | 512 MiB - 1 GiB | `/boot/efi` | UEFI bootloaders (`systemd-boot`, GRUB2) and kernels |
| **2** | `0FC63DAF-8483-4772-8E79-3D69D8477DE4` (Linux Filesystem) | LUKS2 or Btrfs | Remainder of Disk | `/` (via subvols) | Encrypted container or raw Btrfs filesystem |

---

## 3. Btrfs Subvolume Hierarchy

KAIROS standardizes on the `@` subvolume prefix convention for atomic snapshots and clear namespace separation:

```
Btrfs Filesystem (LABEL=KAIROS_ROOT)
├── @           --> /                 (Root OS tree, snapshot-capable)
├── @home       --> /home             (User research, code, & workspaces)
├── @snapshots  --> /.snapshots       (Atomic recovery rollbacks)
├── @var_log    --> /var/log          (Persistent system audit & latency logs)
├── @vault      --> /var/kairos/vault (Encrypted trading API keys & credentials)
└── @data       --> /data             (Optional high-throughput tick data cache)
```

### Mount Options Matrix
In `/etc/fstab`, each subvolume is mounted with optimized low-latency options:
```text
LABEL=KAIROS_BOOT           /boot/efi           vfat    umask=0077,shortname=winnt,errors=remount-ro                            0       2
LABEL=KAIROS_ROOT           /                   btrfs   subvol=@,rw,noatime,compress=zstd:1,space_cache=v2,errors=remount-ro    0       0
LABEL=KAIROS_ROOT           /home               btrfs   subvol=@home,rw,noatime,compress=zstd:1,space_cache=v2                  0       0
LABEL=KAIROS_ROOT           /.snapshots         btrfs   subvol=@snapshots,rw,noatime,compress=zstd:1,space_cache=v2             0       0
LABEL=KAIROS_ROOT           /var/log            btrfs   subvol=@var_log,rw,noatime,compress=zstd:1,space_cache=v2               0       0
LABEL=KAIROS_ROOT           /var/kairos/vault   btrfs   subvol=@vault,rw,noatime,compress=zstd:1,space_cache=v2                 0       0
tmpfs                       /tmp                tmpfs   defaults,nosuid,nodev,noexec,size=4G                                    0       0
```
- `noatime`: Disables access time writes, eliminating unnecessary flash/disk wear and write latency.
- `compress=zstd:1`: Fast real-time compression with minimal CPU overhead, improving throughput on NVMe and SATA drives.
- `space_cache=v2`: High-performance free-space tree management.
- `errors=remount-ro`: Freezes write access on storage controller failure, preserving data integrity.

---

## 4. Encryption Architecture (LUKS2)

When encrypted installation is selected:
1. Physical partition `/dev/nvme0n1p2` is formatted as a **LUKS2** container (`aes-xts-plain64`, 512-bit key, Argon2id password-based key derivation).
2. The unlocked mapped device `/dev/mapper/kairos-crypt` is created.
3. The identical Btrfs subvolume hierarchy is created directly inside `/dev/mapper/kairos-crypt`.
4. The system is optionally enrolled with TPM2 via `systemd-cryptenroll --tpm2-device=auto` for seamless, hardware-measured secure boot unlock without human password entry.

Because the encryption layer is strictly transparent (`dm-crypt`), no OS modifications or subvolume adjustments are needed between plaintext and encrypted systems.

---

## 5. Storage Telemetry & CLI Operations

The `kairos` command-line utility provides instant insight into the storage stack:

### Command: `kairos storage info`
Displays discovered block devices, partition types, drive models, rotational attributes (SSD/NVMe vs HDD), LUKS2 encryption status, active Btrfs subvolumes, and SMART disk health.

Example Output:
```text
================================================================================
 ◈ KAIROS OS - Storage Architecture & Telemetry Report
 Strategy: GPT + UEFI (ESP) + LUKS2 Encryption + Btrfs Subvolume Map
================================================================================
 [Block Devices & Partitions]:
   ◈ /dev/nvme0n1 [1.9TB, SSD/NVMe] - FS: None | Label: - | Mount: - (Samsung SSD 990 PRO 2TB)
      ◈ /dev/nvme0n1p1 [512MB, SSD/NVMe] - FS: vfat | Label: KAIROS_BOOT | Mount: /boot/efi
      ◈ /dev/nvme0n1p2 [1.9TB, SSD/NVMe] - FS: crypto_LUKS | Label: - | Mount: -
        └─ Encryption: LUKS2 Container (Active / Unlocked) [aes-xts-plain64]
           ◈ /dev/mapper/kairos-crypt [1.9TB, SSD/NVMe] - FS: btrfs | Label: KAIROS_ROOT | Mount: /, /home, /var/log
--------------------------------------------------------------------------------
 [Standard KAIROS Subvolume Target Hierarchy]:
   * @           -> /                 (Root OS tree, snapshot-capable)
   * @home       -> /home             (User research & quantitative workspaces)
   * @snapshots  -> /.snapshots       (Atomic recovery rollbacks)
   * @var_log    -> /var/log          (System telemetry & audit logs)
   * @vault      -> /var/kairos/vault (Hardware/TPM2 encrypted credential store)
   * @data       -> /data             (Optional high-throughput tick data cache)
 [Active Btrfs Subvolumes on /]: @, @home, @snapshots, @var_log, @vault, @data
--------------------------------------------------------------------------------
 [Disk Health & SMART Assessment]:
   * /dev/nvme0n1: HEALTHY (SMART PASSED)
--------------------------------------------------------------------------------
 [Safety & Recovery Policies]:
   - Non-destructive Default : Explicit confirmation required for format operations
   - Mount Options           : rw,noatime,compress=zstd:1,space_cache=v2,autodefrag
   - Failure Handling        : Automatic remount-ro on filesystem errors
================================================================================
 Storage Diagnostic: PASS | Status: OPERATIONAL
================================================================================
```

---

## 6. Safe Provisioning Workflow

To partition and format a target storage device using the provisioner:

```bash
# Safe Dry-Run (validates layout without disk writes)
kairos-storage-setup /dev/nvme0n1 true false true

# Real Format with LUKS2 encryption and data subvolume (explicit confirmation required)
kairos-storage-setup /dev/nvme0n1 false true true --confirm-destructive-format
```
