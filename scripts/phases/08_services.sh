#!/usr/bin/env bash
# Phase 8: System Services Setup
# Installs core system daemons, watchdog units, and service presets into rootfs
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TARGET_ROOTFS="${ROOT_DIR}/build/rootfs"

echo "[Phase 8] Deploying KAIROS Core System Services and Daemons..."

mkdir -p "${TARGET_ROOTFS}/usr/libexec/kairos"
mkdir -p "${TARGET_ROOTFS}/etc/systemd/system/multi-user.target.wants"

# Copy daemon binaries/scripts into /usr/libexec/kairos
for daemon in kairos-watchdog.py kairos-riskd.py kairos-feedd.py kairos-researchd.py kairos-agentd.py kairos-adaptived.py; do
    if [ -f "${ROOT_DIR}/services/${daemon}" ]; then
        cp "${ROOT_DIR}/services/${daemon}" "${TARGET_ROOTFS}/usr/libexec/kairos/${daemon}"
        chmod +x "${TARGET_ROOTFS}/usr/libexec/kairos/${daemon}"
    fi
done

# Copy privileged system daemon and core applications runner
cp "${ROOT_DIR}/scripts/services/kairos_sysd.py" "${TARGET_ROOTFS}/usr/libexec/kairos/kairos_sysd.py"
chmod +x "${TARGET_ROOTFS}/usr/libexec/kairos/kairos_sysd.py"

cp "${ROOT_DIR}/scripts/apps/kairos_apps.py" "${TARGET_ROOTFS}/usr/libexec/kairos/kairos_apps.py"
chmod +x "${TARGET_ROOTFS}/usr/libexec/kairos/kairos_apps.py"

# Deploy systemd units and targets
for unit in kairos-sysd.service kairos-watchdog.service kairos-riskd.service kairos-feedd.service kairos-researchd.service kairos-agentd.service kairos-adaptived.service kairos-system.target kairos-desktop.target kairos-trading.target kairos-research.target kairos-ai.target kairos-adaptive.target; do
    if [ -f "${ROOT_DIR}/config/services/${unit}" ]; then
        cp "${ROOT_DIR}/config/services/${unit}" "${TARGET_ROOTFS}/etc/systemd/system/${unit}"
        if [[ "${unit}" == *.service ]]; then
            ln -sf "/etc/systemd/system/${unit}" "${TARGET_ROOTFS}/etc/systemd/system/multi-user.target.wants/${unit}"
        fi
    fi
done

# Deploy logrotate observability configuration
mkdir -p "${TARGET_ROOTFS}/etc/logrotate.d"
if [ -f "${ROOT_DIR}/config/system/logrotate.kairos" ]; then
    cp "${ROOT_DIR}/config/system/logrotate.kairos" "${TARGET_ROOTFS}/etc/logrotate.d/kairos"
    chmod 644 "${TARGET_ROOTFS}/etc/logrotate.d/kairos"
fi

# Stage observability Python modules into rootfs
mkdir -p "${TARGET_ROOTFS}/usr/lib/kairos/system/observability"
cp -r "${ROOT_DIR}/system/observability/"* "${TARGET_ROOTFS}/usr/lib/kairos/system/observability/"

echo "[Phase 8] Tiered system services, targets, and daemons successfully configured."
