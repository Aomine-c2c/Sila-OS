# KAIROS Minimal Linux Operating System Specification

This document details every customization, configuration file, and permission model implemented in the minimal KAIROS Linux OS root filesystem.

---

## ◈ 1. Minimal Substrate Design Philosophy

In accordance with core architectural directives:
- **Zero Desktop Bloatware**: Excludes X11, Wayland compositors, browsers, audio daemons, and graphical packages.
- **Pure Linux Base**: Focuses exclusively on:
  - Linux Kernel & modules
  - Init / systemd service manager
  - Filesystem standards (FHS 3.0)
  - User privilege separation
  - Interactive shell & PAM authentication
  - Predictable networking (`systemd-networkd`)
  - Persistent logging (`systemd-journald`)
  - Precision time synchronization (`systemd-timesyncd`)
  - Dynamic device management (`systemd-udevd`)
  - First-boot system diagnostic utility (`kairos system info`)

---

## ◈ 2. Filesystem Hierarchy Standard (FHS) & Permissions

| Path | Purpose | Permissions | Ownership |
|---|---|---|---|
| `/boot` | Kernel (`vmlinuz`), initramfs, and UEFI EFI stanzas | `0755` | `root:root` |
| `/etc` | System configuration, service presets, credentials | `0755` | `root:root` |
| `/etc/os-release` | KAIROS OS metadata and release identity | `0644` | `root:root` |
| `/etc/fstab` | Static mountpoints (Btrfs subvolumes, ESP, tmpfs) | `0644` | `root:root` |
| `/etc/shadow` | Cryptographic user password hashes | `0600` | `root:root` |
| `/home` | Operator and researcher workspaces | `0755` | `root:root` |
| `/home/kairos` | Default workstation operator home directory | `0750` | `kairos:kairos` |
| `/root` | Root administrator home directory | `0700` | `root:root` |
| `/usr/bin` | System binaries and the `kairos` diagnostic tool | `0755` | `root:root` |
| `/usr/lib` | Shared libraries and systemd units | `0755` | `root:root` |
| `/var/log` | Persistent system audit and journald logs | `0755` | `root:root` |
| `/var/tmp` | Persistent temporary directory with sticky bit | `1777` | `root:root` |
| `/tmp` | Volatile in-RAM temporary directory (`tmpfs`) | `1777` | `root:root` |
| `/dev` | Device nodes populated by `udev` | `0755` | `root:root` |
| `/proc` | Process information pseudo-filesystem | `0555` | `root:root` |
| `/sys` | Kernel sysfs hardware abstraction tree | `0555` | `root:root` |
| `/run` | Volatile runtime daemon state (`tmpfs`) | `0755` | `root:root` |
| `/opt` | Optional proprietary financial SDK packages | `0755` | `root:root` |
| `/srv` | Local market data feed service trees | `0755` | `root:root` |
| `/mnt`, `/media`| Temporary and removable storage mountpoints | `0755` | `root:root` |

---

## ◈ 3. System Identity Metadata (`/etc/os-release`)

```ini
NAME="KAIROS OS"
PRETTY_NAME="KAIROS OS 0.1.0-minimal (Quant/Trading Engineered Substrate)"
ID=kairos
ID_LIKE="fedora rhel linux"
VERSION="0.1.0-minimal"
VERSION_ID="0.1.0"
VERSION_CODENAME="aethelgard"
HOME_URL="https://kairos-os.org"
SUPPORT_URL="https://kairos-os.org/support"
BUG_REPORT_URL="https://kairos-os.org/issues"
PRIVACY_POLICY_URL="https://kairos-os.org/privacy"
ANSI_COLOR="0;36"
LOGO=kairos-logo
BUILD_ID="20260914"
```

---

## ◈ 4. User Hierarchy & Authentication Model

1. **`root`** (`uid=0`, `gid=0`): System superuser, locked password for direct SSH, managed via sudo.
2. **`kairos`** (`uid=1000`, `gid=1000`): Primary workstation operator with `wheel`, `trader`, `quant`, and `operator` supplemental groups.
3. **`kairos-risk`** (`uid=990`, `gid=1003`): Dedicated system daemon account running the immutable `RiskGatekeeper`. Strictly unprivileged with no login shell (`/sbin/nologin`).
4. Standard systemd service users (`systemd-network`, `systemd-timesync`, `systemd-resolve`, `systemd-coredump`).

---

## ◈ 5. Core Services Configuration

### 5.1 Time Synchronization (`systemd-timesyncd`)
Configured in `/etc/systemd/timesyncd.conf`:
- Synchronizes with stratum-1 and low-latency NTP servers: `time.cloudflare.com`, `time.google.com`, `pool.ntp.org`.
- Short polling intervals (`PollIntervalMinSec=16`, `PollIntervalMaxSec=128`) to minimize clock skew for order timestamping.

### 5.2 Persistent Logging (`systemd-journald`)
Configured in `/etc/systemd/journald.conf`:
- `Storage=persistent` with Zstandard compression.
- Dedicated rate-limiting to capture packet drop bursts without overflowing storage.

### 5.3 Predictable Networking (`systemd-networkd`)
Configured in `/etc/systemd/network/10-default-dhcp.network`:
- Dynamic DHCP across all physical and virtual interfaces (`en*`, `eth*`, `virtio*`).
- Strict IPv6 privacy extensions enabled.

---

## ◈ 6. First-Boot Diagnostic Tool: `kairos system info`

The `kairos` binary is deployed to `/usr/bin/kairos` and automatically executes upon login via `/etc/profile.d/01-kairos-info.sh`.

It queries and reports:
1. **OS Version**: Pretty name, ID, version, codename
2. **Kernel**: Release and build flags
3. **Architecture**: CPU architecture (`x86_64`)
4. **Hostname**: Machine network name
5. **Uptime**: System uptime formatted as human-readable duration
6. **Memory**: Total, used, free, and available RAM
7. **CPU**: Processor model name and logical core count
8. **Storage**: Root mount filesystem type, total size, used, and available space
9. **Network State**: Active network interfaces
10. **Boot Mode**: UEFI vs Legacy BIOS and kernel boot parameters
