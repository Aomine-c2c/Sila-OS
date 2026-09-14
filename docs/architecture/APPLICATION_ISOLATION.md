# KAIROS Application Isolation & Sandbox Security Architecture

## 1. Executive Summary & Core Invariants

In high-frequency quantitative trading and institutional research operating systems, arbitrary or compromised code (e.g. untrusted charting libraries, Python wheels, algorithmic plugins, or autonomous AI tools) presents catastrophic systemic risk.

KAIROS OS enforces **Defense-in-Depth Application Isolation** built on native Linux kernel mechanisms:
- **Mount & User Namespaces** (`bubblewrap`, Landlock, read-only system binds).
- **Network Namespaces & Packet Filters** (`unshare --net`, nftables per-UID cgroups).
- **Device Cgroups & Minimal /dev** (No raw PCI, NVMe, or network device registers).
- **Hardware-Protected Secrets** (TPM2-locked vault; zero API/broker private keys accessible in user-space).
- **Abstract IPC & Socket Isolation** (Abstract socket namespace banned; dedicated UNIX sockets only).
- **System Call Restrictions** (Seccomp-BPF strict whitelist filtering).
- **Process & Resource Sandboxing** (Cgroups v2 memory clamps, CPU quotas, `NoNewPrivileges`).

---

## 2. Tiered Classification & Confinement Matrix

| Parameter | TRUSTED_SYSTEM | NORMAL_APP | UNTRUSTED_APP | PLUGIN | AI_TOOL |
|---|---|---|---|---|---|
| **Representative** | `kairos-sysd`, `kairos-riskd` | Terminal, Waybar, Text Editor | TradingView, Web Browser | Strategy Plugin, Custom Signal | `kairos-agentd`, LLM Reasoners |
| **User Identity** | `root` / `kairos-risk` | `kairos` (Operator) | `kairos-sandbox` | `kairos-plugin` (UID 993) | `kairos-agent` (UID 992) |
| **Filesystem Access** | Full System / Audited | Operator `$HOME` | `/tmp` scratch only | Read-Only restricted root | `/tmp/workspace` scratch |
| **Network Access** | Filtered LAN / Dedicated | Full LAN/WAN | Filtered HTTP/S | **NONE (`--unshare-net`)** | **UNIX domain sockets only** |
| **Device Access** | Direct KMS/DRM, NVMe | DRM/KMS, Audio, Input | Direct Render Only (GPU) | **NONE** (No device access) | **NONE** (Compute only) |
| **Credentials / Keys** | Hardware Vault (TPM2) | Operator Keyring | **DENIED** | **STRICTLY DENIED** | **STRICTLY DENIED** |
| **Risk Config Write** | Admin Authorized | Denied | **DENIED** | **STRICTLY DENIED** | **STRICTLY DENIED** |
| **Seccomp Policy** | Base Filter | Default Desktop Filter | Strict (`SCMP_ACT_ERRNO`) | Strict (`SCMP_ACT_ERRNO`) | Strict (`SCMP_ACT_ERRNO`) |
| **Memory / CPU Clamp** | Dedicated / Unclamped | 4 GB | 2 GB / 200% CPU | 1 GB / 100% CPU | 2 GB / 150% CPU |

---

## 3. The Five Absolute Security Invariants

The KAIROS security architecture enforces five strict invariant boundaries:

1. **NO BROKER CREDENTIAL ACCESS**:
   Plugins, untrusted apps, and AI agents **never** receive raw broker API keys, FIX credentials, or private trading keys. Only `kairos-riskd` and the low-level broker execution driver possess broker connectivity.
2. **NO ROOT / PRIVILEGE ESCALATION**:
   All untrusted apps, plugins, and AI tools run with `NoNewPrivileges=yes` and `--nosuid`. Setuid binaries and `sudo` are physically unmapped from their namespace mount tables.
3. **NO RISK CONFIGURATION MUTATION**:
   The `RiskGatekeeper` rules and limits are immutable in hardware memory. Plugins and AI agents cannot adjust drawdown limits, max position sizes, or circuit breakers.
4. **NO ARBITRARY SYSTEM EXECUTION**:
   Strict Seccomp-BPF filters block system manipulation calls (`ptrace`, `bpf`, `kexec_load`, `mount`, `reboot`, `init_module`). Code cannot trace other processes or tamper with kernel modules.
5. **NO ACCESS TO PROTECTED FILESYSTEMS**:
   Critical paths (`/etc/kairos/vault`, `/etc/kairos/risk`, `/etc/shadow`, `/var/log/audit`, `/boot`, `/sys/firmware/efi`) are omitted or mounted `0o000` inaccessible in isolated namespaces.

---

## 4. Evaluation of Linux Isolation Mechanisms

1. **Bubblewrap (`bwrap`) & Mount Namespaces**:
   - Evaluated as the premier unprivileged containerizer for normal and untrusted applications.
   - Provides clean chroots using unprivileged user namespaces without requiring a setuid helper daemon.
2. **Landlock LSM**:
   - Modern Linux unprivileged access control module.
   - Enforces granular path rules at the process level directly in user-space.
3. **Seccomp-BPF (Secure Computing with Berkeley Packet Filters)**:
   - Evaluated and implemented to filter system calls before execution.
   - Restricts plugins and AI tools from debugging, module loading, or modifying network namespaces.
4. **AppArmor & SELinux**:
   - Mandatory Access Control (MAC) profiles applied to background daemons (`/etc/apparmor.d/usr.libexec.kairos.kairos-riskd`).
5. **Cgroups v2 (Control Groups)**:
   - Enforces hard memory ceilings (`MemoryMax`) and CPU throttles (`CPUQuota`) to prevent resource exhaustion attacks.

---

## 5. CLI Verification & Confinement Directives

Operators can inspect and generate sandbox confinement profiles using `kairos sandbox`:

```bash
# 1. Inspect sandbox profiles across all 5 tiers
kairos sandbox profiles

# 2. Test policy enforcement for plugins
kairos sandbox check --tier PLUGIN --secret
# Returns: [DENIED] SECURITY VIOLATION: PLUGIN is strictly denied access to broker credentials.

kairos sandbox check --tier PLUGIN --path /etc/kairos/vault
# Returns: [DENIED] SECURITY VIOLATION: Path '/etc/kairos/vault' is protected system substrate.

kairos sandbox check --tier AI_TOOL --risk
# Returns: [DENIED] SECURITY VIOLATION: AI_TOOL cannot modify immutable Risk Gatekeeper configuration.

# 3. Generate Bubblewrap execution command & Seccomp filters
kairos sandbox generate --tier PLUGIN --binary /usr/bin/python3
```
