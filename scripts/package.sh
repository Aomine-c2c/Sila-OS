#!/usr/bin/env bash
# KAIROS Package & Component Bundler
# Prepares package trees, overlays, and sandboxed application bundles.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PKG_NAME="${1:-all}"

echo "================================================================================"
echo " ◈ KAIROS OS Package Management & Packaging Engine"
echo " Target Package: ${PKG_NAME}"
echo "================================================================================"

mkdir -p packages/bin packages/overlays packages/manifests

# Generate package archive for custom KAIROS binaries
echo "[*] Packaging core KAIROS control, risk, and update utilities..."
tar -czf packages/bin/kairos-core-tools-0.1.0.tar.gz -C bin kairos-control kairos-install kairos-update

echo "[*] Packaging trading and risk gatekeeper daemons..."
tar -czf packages/bin/kairos-trading-daemons-0.1.0.tar.gz -C services kairos-riskd.py kairos-watchdog.py

echo "[*] Generating package manifest index..."
cat << 'EOF' > packages/manifests/packages.json
{
  "repository": "kairos-core",
  "version": "0.1.0",
  "packages": [
    {
      "name": "kairos-core-tools",
      "version": "0.1.0",
      "description": "KAIROS OS Control, Installer, and Recovery Tools",
      "architecture": "x86_64"
    },
    {
      "name": "kairos-trading-daemons",
      "version": "0.1.0",
      "description": "KAIROS Immutable Risk Gatekeeper and Health Watchdog",
      "architecture": "x86_64"
    }
  ]
}
EOF

echo "[+] Packaging completed. Manifest and tarballs available in packages/."
