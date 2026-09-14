#!/usr/bin/env bash
# Phase 3: Kernel Configuration and Low-Latency Tuning
# Verifies kernel config fragments and installs sysctl low-latency configurations into the target rootfs
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 3] Deploying KAIROS low-latency kernel configuration & sysctl tuning..."

# Verify kernel config fragment presence
KERNEL_FRAG="${ROOT_DIR}/config/kernel/config-kairos-rt.fragment"
if [[ ! -f "$KERNEL_FRAG" ]]; then
    echo "[!] Missing kernel configuration fragment: $KERNEL_FRAG" >&2
    exit 1
fi

# Deploy sysctl low-latency parameters to target rootfs
mkdir -p "${TARGET_ROOTFS}/etc/sysctl.d"
cp "${ROOT_DIR}/config/kernel/99-kairos-sysctl.conf" "${TARGET_ROOTFS}/etc/sysctl.d/99-kairos-sysctl.conf"

# Deploy CPU governor tuning systemd unit template
mkdir -p "${TARGET_ROOTFS}/etc/systemd/system"
cat << 'EOF' > "${TARGET_ROOTFS}/etc/systemd/system/kairos-cpu-governor.service"
[Unit]
Description=KAIROS CPU Governor Performance Lock
After=sysinit.target

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'for g in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do [ -f "$g" ] && echo performance > "$g"; done'
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

echo "[Phase 3] Low-latency kernel profile and sysctl rules installed into rootfs."
