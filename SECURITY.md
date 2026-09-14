# Security Policy: KAIROS OS

## 1. Security Architecture & Threat Model

KAIROS OS is deployed in environments handling high-frequency market data, proprietary trading algorithms, sensitive cryptographic API keys, and order execution pipes. The attack surface is defended using a defense-in-depth model:

1. **Mandatory Access Control (MAC)**: AppArmor profiles enforce strict confinement for risk daemons and external-facing plugins. Raw socket creation is explicitly denied for unprivileged processes.
2. **Encrypted Vault Storage**: Sensitive trading credentials, broker certificates, and private keys reside in `/etc/kairos/vault` on an encrypted Btrfs subvolume protected with TPM2 sealing.
3. **Immutable Rootfs & Transactional Snapshots**: The base system is mounted read-only during standard operations. Changes occur via atomic subvolume snapshots.
4. **Firewall & Network Hardening**: Default-drop inbound filtering via `nftables`. Direct WireGuard tunnels for financial execution connections.
5. **AI Safety Bounds**: Machine learning and AI agents are restricted to read-only advisory capacities. They cannot alter system privileges, modify security configurations, or bypass risk limits.

---

## 2. Supported Versions

| Version | Status | Supported Until |
|---|---|---|
| 0.1.x-alpha | Active Development | Current Milestone |
| 1.0.x-rt | Planned Production | 3 Years Post-GA |

---

## 3. Reporting a Vulnerability

If you discover a security vulnerability in KAIROS OS:

- **Do NOT create a public issue** on GitHub or public trackers.
- Email our security team directly: **`security@kairos-os.org`**
- Please include:
  1. A description of the vulnerability and its potential impact.
  2. Reproduction steps, proof-of-concept script, or relevant log traces.
  3. Information on your environment (kernel version, hardware architecture).

We acknowledge receipt of all vulnerability reports within **24 hours** and provide regular status updates until the fix is released.
