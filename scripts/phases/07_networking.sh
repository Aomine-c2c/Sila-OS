#!/usr/bin/env bash
# Phase 7: Networking Stack & Firewall
# Configures systemd-networkd, low-latency socket defaults, nftables security, and network health monitoring
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 7] Configuring KAIROS Low-Latency Network Stack, nftables & Monitoring..."

mkdir -p "${TARGET_ROOTFS}/etc/nftables"
mkdir -p "${TARGET_ROOTFS}/etc/systemd/network"
mkdir -p "${TARGET_ROOTFS}/etc/systemd/timesyncd.conf.d"
mkdir -p "${TARGET_ROOTFS}/etc/sysctl.d"
mkdir -p "${TARGET_ROOTFS}/usr/local/bin"
mkdir -p "${TARGET_ROOTFS}/run/kairos"

# 1. Deploy nftables rule configuration
cp "${ROOT_DIR}/config/network/nftables.conf" "${TARGET_ROOTFS}/etc/nftables/nftables.conf"

# 2. Deploy systemd-networkd profiles (Wired DHCP, Wired Static Example, Wireless DHCP)
cp "${ROOT_DIR}/config/network/20-wired-dhcp.network" "${TARGET_ROOTFS}/etc/systemd/network/20-wired-dhcp.network"
cp "${ROOT_DIR}/config/network/25-wired-static.network.example" "${TARGET_ROOTFS}/etc/systemd/network/25-wired-static.network.example"
cp "${ROOT_DIR}/config/network/30-wireless-dhcp.network" "${TARGET_ROOTFS}/etc/systemd/network/30-wireless-dhcp.network"

# 3. Deploy stratum-1 time synchronization configuration
cp "${ROOT_DIR}/config/network/timesyncd.conf" "${TARGET_ROOTFS}/etc/systemd/timesyncd.conf"

# 4. Deploy low-latency sysctl TCP & socket tuning
cp "${ROOT_DIR}/config/network/99-kairos-network-tuning.conf" "${TARGET_ROOTFS}/etc/sysctl.d/99-kairos-network-tuning.conf"

# 5. Deploy network monitoring daemon & utilities
cp "${ROOT_DIR}/scripts/network/kairos_netmon.py" "${TARGET_ROOTFS}/usr/local/bin/kairos-netmon"
chmod +x "${TARGET_ROOTFS}/usr/local/bin/kairos-netmon"

# 6. Set proper permissions
chmod 0644 "${TARGET_ROOTFS}/etc/nftables/nftables.conf"
chmod 0644 "${TARGET_ROOTFS}/etc/systemd/network"/*.network*
chmod 0644 "${TARGET_ROOTFS}/etc/systemd/timesyncd.conf"
chmod 0644 "${TARGET_ROOTFS}/etc/sysctl.d/99-kairos-network-tuning.conf"

echo "[Phase 7] Network stack, packet filter rules, and monitoring daemon deployed successfully."
