#!/usr/bin/env bash
# KAIROS Minimal Linux OS Builder
# Assembles the minimal bootable Linux operating system root filesystem (FHS compliant).
# No desktop bloatware: provides kernel, systemd/init, networking, device management (udev),
# time synchronization (timesyncd), logging (journald), user accounts, PAM, and kairos system diagnostic.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ROOTFS="${ROOT_DIR}/build/rootfs"
BUILD_LOG="${ROOT_DIR}/build/logs/build_minimal_rootfs.log"
mkdir -p "${ROOT_DIR}/build/logs"

echo "================================================================================" | tee "$BUILD_LOG"
echo " ◈ KAIROS Minimal Linux OS Rootfs Assembly" | tee -a "$BUILD_LOG"
echo " Target Rootfs: ${ROOTFS}" | tee -a "$BUILD_LOG"
echo "================================================================================" | tee -a "$BUILD_LOG"

# 1. Establish Linux Standard Base Filesystem Hierarchy (FHS)
echo "[*] Creating FHS directory hierarchy..." | tee -a "$BUILD_LOG"
mkdir -p "${ROOTFS}"/{boot,etc,home,root,usr,var,opt,run,tmp,dev,proc,sys,mnt,media,srv}
mkdir -p "${ROOTFS}"/usr/{bin,sbin,lib,lib64,include,share,local}
mkdir -p "${ROOTFS}"/usr/share/{man,doc,misc,zoneinfo}
mkdir -p "${ROOTFS}"/var/{log,cache,spool,lib,tmp,run,lock}
mkdir -p "${ROOTFS}"/etc/{systemd,udev,pam.d,security,network,profile.d,kairos}
mkdir -p "${ROOTFS}"/etc/systemd/{system,journald.conf.d,timesyncd.conf.d,network}

# Symlinks for merged /usr standard
ln -snf usr/bin "${ROOTFS}/bin"
ln -snf usr/sbin "${ROOTFS}/sbin"
ln -snf usr/lib "${ROOTFS}/lib"
ln -snf usr/lib64 "${ROOTFS}/lib64"
ln -snf ../run "${ROOTFS}/var/run"
ln -snf ../run/lock "${ROOTFS}/var/lock"

# Set standard Linux permissions
echo "[*] Setting standard filesystem permissions..." | tee -a "$BUILD_LOG"
chmod 0755 "${ROOTFS}"
chmod 1777 "${ROOTFS}/tmp" "${ROOTFS}/var/tmp"
chmod 0700 "${ROOTFS}/root"
chmod 0755 "${ROOTFS}/home"
chmod 0755 "${ROOTFS}/etc"
chmod 0755 "${ROOTFS}/boot"

# 2. System Identity (/etc/os-release & /etc/hostname)
echo "[*] Generating KAIROS system identity (/etc/os-release)..." | tee -a "$BUILD_LOG"
cat << 'EOF' > "${ROOTFS}/etc/os-release"
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
EOF
ln -snf ../etc/os-release "${ROOTFS}/usr/lib/os-release"

echo "kairos-node" > "${ROOTFS}/etc/hostname"

cat << 'EOF' > "${ROOTFS}/etc/hosts"
127.0.0.1   localhost localhost.localdomain kairos-node
::1         localhost localhost.localdomain kairos-node ip6-localhost ip6-loopback
EOF

# 3. Mounts & Filesystem Configuration (/etc/fstab)
echo "[*] Configuring /etc/fstab..." | tee -a "$BUILD_LOG"
cat << 'EOF' > "${ROOTFS}/etc/fstab"
# /etc/fstab: static file system information.
# <file system>    <mount point>   <type>      <options>                         <dump> <pass>
LABEL=KAIROS_ROOT  /               btrfs       defaults,noatime,subvol=@          0      0
LABEL=KAIROS_BOOT  /boot           vfat        defaults,noatime,umask=0077        0      2
LABEL=KAIROS_HOME  /home           btrfs       defaults,noatime,subvol=@home      0      0
LABEL=KAIROS_SNAP  /snapshots      btrfs       defaults,noatime,subvol=@snapshots 0      0
LABEL=KAIROS_LOG   /var/log        btrfs       defaults,noatime,subvol=@var_log   0      0
LABEL=KAIROS_VAULT /etc/kairos/vault btrfs     defaults,noatime,subvol=@vault     0      0
tmpfs              /tmp            tmpfs       defaults,noatime,mode=1777         0      0
devpts             /dev/pts        devpts      gid=5,mode=620                     0      0
proc               /proc           proc        defaults                           0      0
sysfs              /sys            sysfs       defaults                           0      0
EOF
chmod 0644 "${ROOTFS}/etc/fstab"

# 4. User Accounts, Groups, and Authentication
echo "[*] Configuring users, groups, and authentication..." | tee -a "$BUILD_LOG"
cat << 'EOF' > "${ROOTFS}/etc/passwd"
root:x:0:0:root:/root:/bin/bash
bin:x:1:1:bin:/bin:/sbin/nologin
daemon:x:2:2:daemon:/sbin:/sbin/nologin
systemd-network:x:192:192:systemd Network Management:/:/sbin/nologin
systemd-resolve:x:193:193:systemd Resolver:/:/sbin/nologin
systemd-timesync:x:194:194:systemd Time Synchronization:/:/sbin/nologin
systemd-coredump:x:999:999:systemd Core Dumper:/:/sbin/nologin
nobody:x:65534:65534:Kernel Overflow User:/:/sbin/nologin
kairos-risk:x:990:1003:KAIROS Risk Gatekeeper Daemon:/var/lib/kairos-risk:/sbin/nologin
kairos:x:1000:1000:KAIROS Workstation Operator:/home/kairos:/bin/bash
EOF

cat << 'EOF' > "${ROOTFS}/etc/group"
root:x:0:
bin:x:1:
daemon:x:2:
sys:x:3:
adm:x:4:
tty:x:5:
disk:x:6:
wheel:x:10:kairos
systemd-network:x:192:
systemd-resolve:x:193:
systemd-timesync:x:194:
systemd-coredump:x:999:
nobody:x:65534:
trader:x:1001:kairos
quant:x:1002:kairos
riskadmin:x:1003:kairos-risk
operator:x:1004:kairos
kairos:x:1000:
EOF

# Shadow passwords (root password locked/empty, operator user set)
cat << 'EOF' > "${ROOTFS}/etc/shadow"
root:*LK*:19700:0:99999:7:::
kairos:$6$rounds=4096$kairos$eP4d0Qh0GkKq7x3hK/eH9Vj8QW.NlM9g2z8Y3b1K7s0V2w5m6C8.d4A1f3E5g7h9:19700:0:99999:7:::
kairos-risk:!:19700:0:99999:7:::
EOF
chmod 0600 "${ROOTFS}/etc/shadow"

# Home directory for operator
mkdir -p "${ROOTFS}/home/kairos"
chmod 0750 "${ROOTFS}/home/kairos"

# 5. Device Management, Time Synchronization & Logging Services
echo "[*] Configuring Device Management (udev), Time Sync, and Journald..." | tee -a "$BUILD_LOG"

# Time synchronization (systemd-timesyncd)
cat << 'EOF' > "${ROOTFS}/etc/systemd/timesyncd.conf"
[Time]
NTP=time.cloudflare.com time.google.com pool.ntp.org
FallbackNTP=0.pool.ntp.org 1.pool.ntp.org
PollIntervalMinSec=16
PollIntervalMaxSec=128
EOF

# Logging (systemd-journald)
cat << 'EOF' > "${ROOTFS}/etc/systemd/journald.conf"
[Journal]
Storage=persistent
Compress=yes
SystemMaxUse=1G
SystemKeepFree=2G
SyncIntervalSec=5m
RateLimitIntervalSec=30s
RateLimitBurst=10000
EOF

# Networking (systemd-networkd)
cat << 'EOF' > "${ROOTFS}/etc/systemd/network/10-default-dhcp.network"
[Match]
Name=en* eth* virtio*

[Network]
DHCP=yes
IPv6PrivacyExtensions=kernel

[DHCPv4]
RouteMetric=100
UseMTU=true
EOF

# 6. First-Boot Diagnostic Utility (kairos system info)
echo "[*] Installing 'kairos' first-boot diagnostic utility into /usr/bin/kairos..." | tee -a "$BUILD_LOG"
cp "${ROOT_DIR}/bin/kairos" "${ROOTFS}/usr/bin/kairos"
chmod +x "${ROOTFS}/usr/bin/kairos"
ln -snf ../usr/bin/kairos "${ROOTFS}/bin/kairos"

# Install first-boot motd banner
cat << 'EOF' > "${ROOTFS}/etc/motd"

  ◈========================================================================◈
   ██╗  ██╗ █████╗ ██╗██████╗  ██████╗ ███████╗   ██████╗ ███████╗
   ██║ ██╔╝██╔══██╗██║██╔══██╗██╔═══██╗██╔════╝  ██╔═══██╗██╔════╝
   █████╔╝ ███████║██║██████╔╝██║   ██║███████╗  ██║   ██║███████╗
   ██╔═██╗ ██╔══██║██║██╔══██╗██║   ██║╚════██║  ██║   ██║╚════██║
   ██║  ██╗██║  ██║██║██║  ██║╚██████╔╝███████║  ╚██████╔╝███████║
   ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═════╝ ╚══════╝
  ◈========================================================================◈
   Welcome to KAIROS OS Minimal Operating System Substrate
   Purpose-built for Low-Latency Quantitative Research & Financial Execution.
   
   To view complete system status, run:
     # kairos system info
  ◈========================================================================◈

EOF

# Add kairos system info execution on login profile
cat << 'EOF' > "${ROOTFS}/etc/profile.d/01-kairos-info.sh"
#!/bin/sh
if [ -t 0 ] && [ -x /usr/bin/kairos ]; then
    /usr/bin/kairos system info
fi
EOF
chmod +x "${ROOTFS}/etc/profile.d/01-kairos-info.sh"

echo "================================================================================" | tee -a "$BUILD_LOG"
echo "[+] Minimal KAIROS root filesystem successfully constructed at: ${ROOTFS}" | tee -a "$BUILD_LOG"
echo "================================================================================" | tee -a "$BUILD_LOG"
