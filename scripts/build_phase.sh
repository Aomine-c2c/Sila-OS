#!/usr/bin/env bash
# Phase execution router for KAIROS OS build engine
set -euo pipefail

PHASE="${1:-}"

if [[ -z "$PHASE" ]]; then
    echo "[!] Error: No phase provided to build_phase.sh" >&2
    exit 1
fi

PHASE_SCRIPT="scripts/phases/${PHASE}.sh"

if [[ ! -f "$PHASE_SCRIPT" ]]; then
    echo "[*] Phase script ${PHASE_SCRIPT} not yet created. Creating stub and validating phase directory..."
    mkdir -p "scripts/phases"
    cat << 'EOF' > "$PHASE_SCRIPT"
#!/usr/bin/env bash
set -euo pipefail
echo "[+] Executing default phase handler for $(basename "$0")"
exit 0
EOF
    chmod +x "$PHASE_SCRIPT"
fi

echo "================================================================================"
echo " Starting KAIROS Phase: $PHASE"
echo "================================================================================"
bash "$PHASE_SCRIPT"
echo "[+] Successfully completed KAIROS Phase: $PHASE"
