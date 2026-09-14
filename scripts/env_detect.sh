#!/usr/bin/env bash
# KAIROS Environment Detection Engine
# Detects host operating system, architecture, kernel version, virtualization support,
# container runtimes, and execution contexts (Bare-Metal, VM, WSL2, Container).
set -euo pipefail

echo "================================================================================"
echo " ◈ KAIROS OS Environment Detection Engine"
echo "================================================================================"

ARCH="$(uname -m 2>/dev/null || echo 'unknown')"
KERNEL="$(uname -r 2>/dev/null || echo 'unknown')"
OS_NAME="$(uname -s 2>/dev/null || echo 'unknown')"

echo "[*] Host Architecture : ${ARCH}"
echo "[*] Kernel Release    : ${KERNEL}"
echo "[*] OS Kernel Name    : ${OS_NAME}"

# Detect execution context
CONTEXT="Native Linux (Bare-Metal / VM)"
if grep -qi "microsoft" /proc/version 2>/dev/null || [[ -n "${WSL_DISTRO_NAME:-}" ]]; then
    CONTEXT="Windows Subsystem for Linux (WSL2)"
elif [[ -f "/.dockerenv" ]] || [[ -f "/run/.containerenv" ]]; then
    CONTEXT="Containerized Environment (Docker/Podman)"
fi
echo "[*] Execution Context : ${CONTEXT}"

# Hardware virtualization detection
VIRT="Not Available"
if grep -Eq "(vmx|svm)" /proc/cpuinfo 2>/dev/null; then
    VIRT="Hardware Virtualization Supported (VT-x/AMD-V)"
fi
echo "[*] CPU Virtualization: ${VIRT}"

# Check available container engines
CONTAINER_ENGINE="None"
if command -v podman >/dev/null 2>&1; then
    CONTAINER_ENGINE="Podman ($(podman --version))"
elif command -v docker >/dev/null 2>&1; then
    CONTAINER_ENGINE="Docker ($(docker --version))"
fi
echo "[*] Container Engine  : ${CONTAINER_ENGINE}"

# Check memory and CPU topology
CPUS="$(nproc 2>/dev/null || echo '1')"
MEM_KB="$(grep MemTotal /proc/meminfo 2>/dev/null | awk '{print $2}' || echo '0')"
MEM_GB=$(( MEM_KB / 1024 / 1024 ))
echo "[*] Logical CPUs      : ${CPUS}"
echo "[*] Physical RAM      : ~${MEM_GB} GB"
echo "================================================================================"
echo "[+] Environment detection complete."
