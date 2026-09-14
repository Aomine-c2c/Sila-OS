# KAIROS OS Installer

The KAIROS installer is a terminal-based, interactive installation wizard
that guides the user through all phases of system installation.

---

## Usage

```bash
# Interactive installation (normal)
kairos-install

# Dry-run (no disk changes)
kairos-install --dry-run

# Python direct invocation
python3 installer/kairos_installer.py
python3 installer/kairos_installer.py --dry-run
```

---

## Installation Flow

```
BOOT → HARDWARE DETECTION → LANGUAGE → KEYBOARD → NETWORK →
DISK → ENCRYPTION → USER → HOSTNAME → TIMEZONE →
INSTALL PROFILE → OPTIONAL COMPONENTS → CONFIRM →
INSTALL → BOOTLOADER → HEALTH CHECK → FIRST BOOT
```

| Phase | Description |
|-------|-------------|
| **0. Hardware Detection** | CPU, memory, disks, GPU, firmware mode |
| **1. Language** | System locale (UTF-8) |
| **2. Keyboard** | Keyboard layout |
| **3. Network** | DHCP / Static / Skip |
| **4. Disk** | Target disk selection + partition layout preview |
| **5. Encryption** | LUKS2 passphrase + optional TPM2 enrollment |
| **6. User** | Primary username + password |
| **7. Hostname & Timezone** | System identity |
| **8. Profile** | Installation profile selection |
| **9. Optional Components** | Extras: WireGuard, Docker, YubiKey, etc. |
| **10. Confirm** | Full summary + destructive confirmation gate |
| **11. Install** | Package installation + filesystem setup |
| **12. Bootloader** | systemd-boot (UEFI) or GRUB2 (Legacy) |
| **13. Health Check** | Post-install verification |
| **14. First Boot** | First-boot config + user guidance |

---

## Profiles

| Profile | Description | Disk Est. |
|---------|-------------|-----------|
| **Minimal** | Core OS only. Console + SSH. No desktop. | ~2 GB |
| **Trader** | Full desktop + complete trading stack. | ~8 GB |
| **Quant Research** | Desktop + Python/Jupyter/data stack. | ~12 GB |
| **Developer** | Minimal base + dev tools. Modular. | ~6 GB |
| **Full** | All components: trading, research, AI, dev. | ~20 GB |

### Developer Profile

The Developer profile is **intentionally minimal**. Use `kairos dev enable` to add components:

```bash
kairos dev enable rust
kairos dev enable python-quant
kairos dev enable containers
kairos dev enable kernel-dev
kairos dev status
```

---

## Optional Components

| Component | Description |
|-----------|-------------|
| `wireguard` | WireGuard VPN client integration |
| `yubikey` | YubiKey / FIDO2 hardware token authentication |
| `tpm2` | TPM2 disk unlocking (auto-unlock on trusted boot) |
| `docker` | Docker container runtime |
| `virtualization` | QEMU/KVM virtual machine support |
| `developer-tools` | Full dev toolchain (Rust, Go, LLVM, GDB, Valgrind) |
| `quant-libs` | Full Python quantitative library stack |
| `ai-agents` | KAIROS autonomous AI agent platform |
| `adaptive-intel` | Adaptive Evolution Intelligence (AEI) |
| `zsh-env` | Z-Shell with KAIROS theme & trading aliases |

---

## Disk Layout

For UEFI systems, the installer creates:

```
/dev/sdX1  1 GiB    EFI System Partition (FAT32)
/dev/sdX2  2 GiB    /boot (ext4)
/dev/sdX3  <rest>   LUKS2 encrypted container → Btrfs
```

Btrfs subvolumes inside the encrypted container:

| Subvolume | Mount Point | Purpose |
|-----------|-------------|---------|
| `@` | `/` | Root OS tree |
| `@home` | `/home` | User workspaces |
| `@snapshots` | `/.snapshots` | Atomic rollbacks |
| `@var_log` | `/var/log` | Audit logs |
| `@vault` | `/var/kairos/vault` | Encrypted credential store |
| `@data` | `/data` | High-throughput tick data |

---

## Safety Guarantees

- **No disk modifications without confirmation**
- Destructive operations require typing `YES, DESTROY DATA`
- Dry-run mode (`--dry-run`) makes zero disk changes
- All actions are logged to `/tmp/kairos-install.log`
- Install manifest saved to `/tmp/kairos-install-manifest.json`

---

## Artifacts

| File | Purpose |
|------|---------|
| `/tmp/kairos-install.log` | Full installer session log |
| `/tmp/kairos-install-manifest.json` | Machine-readable install choices |
| `/mnt/etc/kairos/first-boot.json` | First-boot configuration |
| `/mnt/efi/loader/entries/kairos.conf` | Normal boot entry |
| `/mnt/efi/loader/entries/kairos-recovery.conf` | Recovery boot entry |

---

## Recovery Access

After installation, recovery is always accessible:

- **At boot**: Select "KAIROS OS Recovery" from bootloader menu
- **CLI**: `kairos recovery menu`
- **Emergency**: Append `single` to kernel command line
