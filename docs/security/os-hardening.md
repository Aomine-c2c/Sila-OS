# KAIROS Operating System Security Hardening Baseline

## 1. Overview & Objectives
KAIROS OS is an engineered operating environment handling sensitive financial execution logic, real capital, and proprietary quantitative models. Security hardening must be applied **before** introducing higher-level desktop or automation components.

Hardening adheres to four core principles:
1. **Least Privilege**: Components run with the minimum required capabilities; no daemon runs as root unless strictly unavoidable.
2. **Defensive Perimeter**: The default network policy is **DROP**, preventing unauthorized ingress.
3. **Memory & Kernel Protection**: Kernel attack surfaces (BPF, ptrace, dmesg, kptr) are restricted by default.
4. **Transparent Usability**: Security controls are thoroughly documented so developers and quant operators understand system behavior without feeling blocked.

---

## 2. Hardening Audit Matrix

The automated hardening audit (`./scripts/security-audit`) continuously validates the operating system against the following benchmarks:

| Domain | Control | Implementation | Audit Verdict |
|---|---|---|---|
| **Users & Accounts** | Single Root Identity | Verified only `root` has UID 0 | **PASS** |
| **Service Isolation** | No Interactive Shells | `kairos-risk`, `kairos-feed`, `kairos-agent`, `kairos-plugin` set to `/sbin/nologin` | **PASS** |
| **Sensitive Assets** | Permissions & Shadow | `/etc/shadow` restricted to 0600 / 0000; TPM2 vault restricted to 0700 | **PASS** |
| **Privilege Escalation** | Sudo Escrow | Password challenge required; no global `NOPASSWD: ALL` | **PASS** |
| **Firewall (nftables)** | Default Drop Ingress | Default input/forward policies set to `drop`; loopback & WireGuard accepted | **PASS** |
| **Kernel Hardening** | ASLR & Ptrace Shield | `kptr_restrict=2`, `dmesg_restrict=1`, `yama.ptrace_scope=2` | **PASS** |
| **Network Defense** | Reverse Path Filtering | `rp_filter=1`, redirects disabled, ICMP broadcast ignore | **PASS** |
| **Filesystem Safety** | Symlink / Hardlink Shield | `fs.protected_hardlinks=1`, `fs.protected_symlinks=1` | **PASS** |
| **Logging & Telemetry** | Protected System Logs | Journald persistent logs stored under protected `/var/log/` | **PASS** |
| **Mandatory Access Control** | AppArmor Risk Daemon | Socket and filesystem boundary enforcement via AppArmor profile | **PASS** |

---

## 3. Kernel Hardening Specification (`99-kairos-security.conf`)

System-wide security kernel parameters are located in `/etc/sysctl.d/99-kairos-security.conf`:

```ini
# 1. Kernel Pointer & Memory Address Obfuscation
kernel.kptr_restrict = 2
kernel.dmesg_restrict = 1
kernel.yama.ptrace_scope = 2
kernel.unprivileged_bpf_disabled = 1
net.core.bpf_jit_harden = 2

# 2. Filesystem Symlink, Hardlink & FIFO Attack Mitigations
fs.protected_hardlinks = 1
fs.protected_symlinks = 1
fs.protected_fifos = 2
fs.protected_regular = 2
fs.suid_dumpable = 0

# 3. Network Perimeter & Spoofing Defense
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.log_martians = 1
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1

# 4. IPv6 Hardening
net.ipv6.conf.all.accept_redirects = 0
net.ipv6.conf.default.accept_redirects = 0
net.ipv6.conf.all.accept_source_route = 0
net.ipv6.conf.default.accept_source_route = 0
```

---

## 4. Operational Considerations & Developer Workflow

To ensure that security controls do not disrupt everyday development:
- **Debugging & Profiling**: `kernel.yama.ptrace_scope = 2` prevents unprivileged processes from attaching to arbitrary processes. Developers debugging their own binaries may run debuggers under their own user session or escalate via `sudo gdb` when analyzing trading daemons.
- **Dmesg Access**: Unprivileged users cannot read `dmesg` directly. System logs should be viewed using `journalctl` (members of `wheel` / `administrators` have access).
- **Service Management**: Workstation operators (`kairos`) can restart trading services (`systemctl restart kairos-feed`) without password prompts, minimizing friction while keeping root privileges safe.

---

## 5. Security Audit Verification Tool

The `./scripts/security-audit` utility provides a terminal report grading security health into `[PASS]`, `[WARN]`, and `[FAIL]`:

```bash
# Run comprehensive security validation
./scripts/security-audit
```

Exit Code Behavior:
- `0`: All critical invariants met (`PASS`).
- `1`: One or more security invariants violated (`FAIL`). System build must halt until resolved.
