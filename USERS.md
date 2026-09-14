# KAIROS OS User, Authentication & Privilege Model

## 1. Architectural Philosophy
KAIROS is an operating system purpose-built for quantitative research, high-frequency execution, and autonomous market operation. Financial systems operating real capital require strict **Least Privilege Architecture**, **Identity Isolation**, and **Audited Privilege Escalation**.

### Core Invariants:
1. **Never Run Trading Daemons as Root**: Trading execution engines, market feed adapters, quantitative bots, and AI agents **must never execute as root** (`UID 0`). They run under dedicated, sandboxed, unprivileged service identities.
2. **Break-Glass Root Only**: Direct root login is disabled in production. Administrative interventions occur via audited `sudo` escalation granted to the `administrators` / `wheel` group.
3. **Hardware & Capability Segregation**: Workstation users access GPU acceleration, audio, and network devices strictly through dedicated UNIX group memberships rather than root permissions.
4. **Sandboxed Plugin Environment**: Third-party trading strategy plugins execute under an unprivileged, resource-capped user identity (`kairos-plugin`) with zero real-time priority (`rtprio=0`) and strict memory ceilings.

---

## 2. User Matrix & Identities

| Account | UID | GID | Shell | Home Directory | Role & Capabilities |
|---|---|---|---|---|---|
| **`root`** | `0` | `0` | `/bin/bash` | `/root` | Break-glass maintenance, kernel bootstrapping, and emergency recovery. |
| **`kairos`** | `1000` | `1000` | `/bin/bash` | `/home/kairos` | Principal workstation operator. Belongs to `wheel`, `desktop`, `audio`, `video`, `network`, `trading`, `research`. |
| **`kairos-risk`** | `990` | `1003` (`riskadmin`) | `/sbin/nologin` | `/var/lib/kairos-risk` | Dedicated daemon identity for the Immutable Risk Gatekeeper. Runs at RT priority 99. |
| **`kairos-feed`** | `991` | `1020` (`trading`) | `/sbin/nologin` | `/var/lib/kairos-feed` | High-throughput multicast / WebSocket market data ingestion daemon. |
| **`kairos-agent`** | `992` | `1021` (`research`) | `/sbin/nologin` | `/var/lib/kairos-agent` | Autonomous AI research assistant & quantitative model trainer. |
| **`kairos-plugin`** | `993` | `1022` (`plugins`) | `/sbin/nologin` | `/var/lib/kairos-plugins` | Sandboxed runtime identity for third-party strategies and community indicators. |

---

## 3. Group Taxonomy & Access Boundaries

Every system capability is gated behind fine-grained UNIX groups:

```
UNIX Groups
├── administrators (GID 10)  --> Audited sudo privilege escalation (alias for wheel)
├── wheel (GID 10)           --> Sudoers capability
├── desktop (GID 1010)       --> Wayland/Hyprland session seat control & IPC
├── audio (GID 63)           --> PipeWire / ALSA sound device nodes
├── video (GID 39)           --> DRI / DRM direct GPU acceleration nodes (/dev/dri/*)
├── network (GID 1013)       --> Interface configuration & WireGuard VPN control
├── trading (GID 1020)       --> Low-latency execution IPC bus & broker gateway sockets
├── research (GID 1021)      --> Historical tick data lake queries & Jupyter notebooks
└── plugins (GID 1022)       --> Strictly throttled strategy container sandbox
```

---

## 4. Privilege Escalation & Sudoers Policy

Sudo privilege escalation is governed by `/etc/sudoers.d/10-wheel`:

```sudoers
# Full administrative capability with password challenge
%wheel ALL=(ALL:ALL) ALL
%administrators ALL=(ALL:ALL) ALL

# Scoped, non-destructive daemon management for operator
kairos ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart kairos-feed, /usr/bin/systemctl restart kairos-agent, /usr/bin/systemctl status *
```

- Operators must authenticate with their personal password to execute administrative commands.
- The `kairos-risk` daemon is strictly prohibited from invoking `sudo`.

---

## 5. Resource Limits & Real-Time Prioritization

Resource allocation is statically defined in `/etc/security/limits.d/99-kairos-realtime.conf`:

```text
# Low-Latency Trading Stack: Uncapped memory locking & RT priority 99
@trading        hard    rtprio          99
@trading        soft    rtprio          95
@trading        hard    memlock         unlimited
@trading        soft    memlock         unlimited
@trading        hard    nofile          1048576
@trading        soft    nofile          1048576

# Quantitative Research: Uncapped memory for in-RAM DataFrame analysis
@research       hard    memlock         unlimited
@research       soft    memlock         unlimited
@research       hard    nofile          524288
@research       soft    nofile          524288

# Immutable Risk Gatekeeper: Guaranteed execution slot
@riskadmin      hard    rtprio          99
@riskadmin      hard    memlock         unlimited

# Strategy Plugins: Capped resources to prevent runaway algorithms
@plugins        hard    rtprio          0
@plugins        soft    rtprio          0
@plugins        hard    nproc           1024
@plugins        soft    nproc           512
@plugins        hard    nofile          8192
@plugins        soft    nofile          4096
@plugins        hard    as              33554432
```

---

## 6. CLI Diagnostics & Telemetry

### 1. `kairos user info`
Inspects the active session, user UID/GID, supplementary group capabilities, and privilege state.

```bash
kairos user info
```

Sample output:
```text
================================================================================
 ◈ KAIROS OS - User Identity & Session Diagnostic
 Principle: Least Privilege Workstation Architecture
================================================================================
 [Current User]       : kairos (UID: 1000)
 [User Description]   : KAIROS Principal Workstation Operator
 [Primary GID]        : 1000
 [Home Directory]     : /home/kairos
 [Login Shell]        : /bin/bash
 [Supplementary Groups]: wheel, desktop, audio, video, network, trading, research
--------------------------------------------------------------------------------
 [Privilege & Capability Assessment]:
   * Administrator Capability : YES (wheel/administrators active)
   * Root Account Direct Run  : NO (Safe unprivileged user)
   * Desktop & Wayland Access : YES (desktop group)
   * Hardware Acceleration    : YES (video/audio groups)
   * High-Speed Trading Sockets: YES (trading group)
   * Quantitative Research    : YES (research group)
--------------------------------------------------------------------------------
 [Session & Authentication Status]:
   * TTY / Display            : wayland-0
   * Sudo Policy Loaded       : /etc/sudoers.d/10-wheel (Audited Escrow)
================================================================================
 User Status: VERIFIED | Security Boundary: ENFORCED
================================================================================
```

### 2. `kairos permissions`
Performs an instant security audit of system groups, service accounts, and resource boundaries.

```bash
kairos permissions
```
