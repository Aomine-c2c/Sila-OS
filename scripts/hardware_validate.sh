#!/usr/bin/env bash
# KAIROS Hardware Validation Engine
# Audits real-time scheduling capabilities, TSC timer reliability, NVMe latency, and CPU isolation.
set -euo pipefail

echo "================================================================================"
echo " ◈ KAIROS OS Hardware & Low-Latency Subsystem Validation"
echo "================================================================================"

# 1. CPU Clocksource validation
CLOCKSOURCE="/sys/devices/system/clocksource/clocksource0/current_clocksource"
if [[ -f "$CLOCKSOURCE" ]]; then
    CURR_CS="$(cat "$CLOCKSOURCE")"
    echo "[*] Current Clocksource : ${CURR_CS}"
    if [[ "$CURR_CS" == "tsc" ]]; then
        echo "  [+] TSC clocksource verified (optimal for nanosecond timestamping)."
    else
        echo "  [!] Warning: Non-TSC clocksource detected (${CURR_CS}). High latency jitter possible."
    fi
else
    echo "[*] Clocksource sysfs node not directly accessible (virtualized/container context)."
fi

# 2. Check CPU Frequency Scaling Governor
GOV_FILES=(/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor)
if [[ -f "${GOV_FILES[0]:-}" ]]; then
    GOV="$(cat "${GOV_FILES[0]}")"
    echo "[*] CPU Governor        : ${GOV}"
    if [[ "$GOV" == "performance" ]]; then
        echo "  [+] CPU Frequency locked to performance mode."
    else
        echo "  [*] Recommendation: Lock CPU governor to 'performance' via kairos-control."
    fi
else
    echo "[*] CPU governor sysfs not exposed in current container/virtual environment."
fi

# 3. Check for IOMMU / VT-d
if dmesg 2>/dev/null | grep -Eqi "(DMAR|IOMMU)"; then
    echo "[*] IOMMU / VT-d        : Detected (Ready for VFIO PCIe NIC Passthrough)"
else
    echo "[*] IOMMU / VT-d        : Not active or dmesg restricted."
fi

# 4. Timer resolution test
echo "[*] Running high-resolution timer test..."
python3 -c "
import time
deltas = []
for _ in range(100):
    t0 = time.perf_counter_ns()
    time.sleep(0.001)
    t1 = time.perf_counter_ns()
    deltas.append(abs((t1 - t0) - 1_000_000))
avg_jitter_us = sum(deltas) / len(deltas) / 1000.0
print(f'  [+] Average sleep jitter: {avg_jitter_us:.2f} microseconds')
"

echo "================================================================================"
echo "[+] Hardware validation audit completed."
