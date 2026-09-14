# KAIROS Operating System — Core System Applications & Privileged Architecture

## 1. Overview & Architectural Principles

KAIROS OS defines 14 core system applications providing administrative, monitoring, recovery, and configuration controls for institutional trading and quantitative research workstations.

To guarantee system stability, prevent unauthorized privilege escalation, and enforce auditability:
1. **Zero Privileged Code in UI/Clients**: Neither desktop UI widgets, application windows, nor command palettes directly invoke `sudo`, setuid binaries, or raw destructive kernel/system calls.
2. **Controlled System Service (`kairos-sysd`)**: All privileged and dangerous operations are delegated across a UNIX domain socket boundary (`/run/kairos/sysd.sock`) to a hardened systemd daemon.
3. **Explicit Role-Based Access Control (RBAC)**:
   - `any`: Read-only telemetry, system identity, monitor status, and baseline configuration readable by any authenticated user.
   - `trader`: Session configurations, monitor scaling, audio balance, and user-space startup daemons manageable by members of `trader`, `research`, or `wheel`.
   - `admin`: Mutating system profiles, cycling network interfaces, modifying DNS, taking Btrfs snapshots, reloading firewall rules, rollback points, and service restarts gated strictly by `wheel` (or UID 0).
4. **Observable & Auditable**: Every request dispatched through `kairos-sysd`—whether approved or denied—records structured JSON audit trails to `/var/log/audit/kairos-sysd.log`.

---

## 2. The 14 Core System Applications

| # | Application | ID | CLI Invocation | Privilege Requirement | Observable Output / Scope |
|---|---|---|---|---|---|
| **01** | **System Settings** | `settings` | `kairos app settings` | Read: Any, Set: Admin (`wheel`) | Real-time scheduler tuning (`nohz_full`), CPU governor (`performance`), IRQ pinning. |
| **02** | **Network Manager** | `network` | `kairos app network` | Read: Any, Cycle/DNS: Admin | Physical interfaces, sub-millisecond gateway latency, packet loss, DNS resolution. |
| **03** | **Display Settings** | `display` | `kairos app display` | Read: Any, Scale: Trader | Wayland DRM/KMS outputs, HiDPI scaling, refresh rates, multi-monitor topology. |
| **04** | **Audio Settings** | `audio` | `kairos app audio` | Read: Any, Volume/Mute: Trader | PipeWire 1.0 pro-audio graph, ALSA sink volumes, mute state. |
| **05** | **Users** | `users` | `kairos app users` | Read: Any, Lock: Admin | Local & system account inventory, shell attributes, UID/GID permission boundaries. |
| **06** | **Storage** | `storage` | `kairos app storage` | Read: Any, Snapshot: Admin | Btrfs subvolumes (`@`, `@home`, `@snapshots`, `@vault`), LUKS2 encryption state. |
| **07** | **Security** | `security` | `kairos app security` | Read: Any, Reload: Admin | Security control audit (AppArmor, nftables default-drop, vault integrity, lockdown). |
| **08** | **Updates** | `updates` | `kairos app updates` | Read: Any, Rollback: Admin | Certified reproducible release channels, ed25519 image signatures, atomic rollback. |
| **09** | **Services** | `services` | `kairos app services` | Read: Any, Restart: Admin | Monitored system daemons (`kairos-riskd`, `kairos-watchdog`, `systemd-networkd`). |
| **10** | **Startup Applications** | `startup` | `kairos app startup` | Read: Any, Toggle: Trader | Hyprland session autostart hooks (`waybar`, `mako`, `swayidle`, `cliphist`). |
| **11** | **Hardware Information** | `hardware` | `kairos app hardware` | Read: Any | CPU topology, AVX-512 extensions, NUMA balancing, GPU acceleration, PCIe fabric. |
| **12** | **Logs** | `logs` | `kairos app logs` | Read: Any | Append-only audit records, privileged daemon actions, zero-slippage timer logs. |
| **13** | **Recovery** | `recovery` | `kairos app recovery` | Read: Any, Test: Admin | Fallback initramfs (`/boot/initramfs-kairos-fallback.img`), disaster recovery profiles. |
| **14** | **About KAIROS** | `about` | `kairos app about` | Read: Any | OS identity, release tier, real-time kernel specification, design philosophy. |

---

## 3. Privileged Daemon Architecture (`kairos-sysd`)

### 3.1 IPC & Socket Protocol
`kairos-sysd` binds to `/run/kairos/sysd.sock` with permission mode `0666` (world-connectable), but leverages Linux kernel peer credential inspection:
```python
ucred = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
pid, uid, gid = struct.unpack("3i", ucred)
```
The caller's identity is immutable and cannot be forged by user-space environment variables.

### 3.2 Audit Logging
All dispatch actions write JSON records to `/var/log/audit/kairos-sysd.log` (with fallback to `/run/kairos/sysd_audit.log`):
```json
{
  "timestamp_utc": "2026-09-14T13:04:27Z",
  "caller_uid": 1000,
  "action": "storage.create_snapshot",
  "authorized": true,
  "details": "Executed for caller PID 14201"
}
```
Attempted unauthorized actions (e.g. an unprivileged user requesting `updates.rollback` or `users.lock_account`) immediately log `authorized: false` with the caller UID and return an explicit `Access Denied` error payload.

---

## 4. Execution & Usage

### 4.1 CLI & Application Launcher
Users and UI launchers access applications through the unified CLI:
```bash
# List all 14 core applications
kairos app

# Inspect specific application
kairos app settings
kairos app network
kairos app storage
kairos app security
kairos app about

# Structured JSON output for UI integration
kairos app hardware --json
kairos app services --json
```

### 4.2 Automated Testing
The entire suite is verified via unit and boundary tests:
```bash
python3 -m unittest tests/test_core_applications.py
```
Validates:
- All 14 applications registered and responding.
- Proper role checks and authorization denials for unprivileged users.
- Structured audit log emission.
- Root execution authorization.
