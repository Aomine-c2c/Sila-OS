# KAIROS Operating System — Service Architecture Specification

## 1. Overview & Tiered Service Taxonomy

KAIROS OS isolates system components into six decoupled functional tiers. Each tier operates within dedicated systemd targets, user identities, resource boundaries, and failure domains.

```
                   ┌────────────────────────────────────────┐
                   │        KAIROS Hardware / Kernel        │
                   └───────────────────┬────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                     │
           [SYSTEM SERVICES]                     [DESKTOP SERVICES]
         (kairos-system.target)                (kairos-desktop.target)
       - kairos-sysd (PID 1102)               - greetd (UID 1201)
       - kairos-watchdog (PID 1105)           - hyprland-session
       - systemd-networkd                     - pipewire pro-audio
                    │                                     │
        ┌───────────┴───────────┐                         │
        │                       │                         │
[TRADING SERVICES]      [RESEARCH SERVICES]               │
(kairos-trading.target) (kairos-research.target)          │
- kairos-riskd (RR/90)  - kairos-researchd                │
- kairos-feedd          (Nice=10, Sandboxed)              │
        │                                                 │
        ├───────────────────────┐                         │
        │                       │                         │
  [AI SERVICES]        [ADAPTIVE SERVICES]                │
(kairos-ai.target)    (kairos-adaptive.target)            │
- kairos-agentd       - kairos-adaptived                  │
(Advisory Sandbox)    (Bounded AEI Heuristics)            │
```

---

## 2. Decoupled Service Tiers & Invariants

### 2.1 SYSTEM SERVICES (`kairos-system.target`)
- **`kairos-sysd.service`**: Privileged system daemon mediating hardware, storage, and security operations over `/run/kairos/sysd.sock` with `SO_PEERCRED` verification.
- **`kairos-watchdog.service`**: High-precision timer jitter, hardware telemetry, and latency slip supervisor.
- **`systemd-networkd.service`**: Real-time deterministic network configuration.

### 2.2 DESKTOP SERVICES (`kairos-desktop.target`)
- **`greetd.service`**: Secure institutional greeter and session initiator.
- **`hyprland-session.service`**: Wayland compositor, window management, and status bar (`waybar`).
- **`pipewire.service`**: Low-latency audio subsystem.

### 2.3 TRADING SERVICES (`kairos-trading.target`)
- **`kairos-riskd.service`**: Non-bypassable hardware-locked Risk Gatekeeper daemon running with real-time FIFO/Round-Robin scheduling priority (`RR/90`) and locked memory (`LimitMEMLOCK=infinity`).
- **`kairos-feedd.service`**: Dedicated market data ingestion ringbuffer running under unprivileged user `kairos-feed` (UID 991).
- **Failure Boundary**: Trading services run completely decoupled from GUI windows. If a desktop app or compositor crashes, `kairos-riskd` continues protecting open positions and trailing stops uninterrupted.

### 2.4 RESEARCH SERVICES (`kairos-research.target`)
- **`kairos-researchd.service`**: Factor model calculations, backtesting jobs, and Apache Arrow/Parquet caches (`/var/cache/kairos/market_data`).
- **Isolation & Resource Quota**: Operates under user `kairos` (GID `research`), clamped with `Nice=10` and `MemoryMax=4G`. Heavy vectorized research calculations can never starve the trading engine or cause CPU jitter on core market threads.

### 2.5 AI SERVICES (`kairos-ai.target`)
- **`kairos-agentd.service`**: Autonomous AI reasoning agent runtime under dedicated account `kairos-agent` (UID 992).
- **Safety Invariant**: AI agents operate in an advisory capacity only. They have zero direct execution authority or raw broker sockets.
- **Crash Invariant**: **A failed AI service must not crash the trading engine or desktop.**

### 2.6 ADAPTIVE SERVICES (`kairos-adaptive.target`)
- **`kairos-adaptived.service`**: Adaptive Evolution Intelligence (AEI) monitoring scheduling slips and queue depths to adapt runtime heuristics (e.g. sysctl busy poll budgets).
- **Safety Invariant**: AEI operations are strictly clamped within bounded ranges.
- **Crash Invariant**: **A failed adaptive service must not crash the OS or modify immutable risk boundaries.**

---

## 3. Service Lifecycle Management Commands

Administrative and observability actions are integrated into `kairos service`:

| Command | Purpose | Authorization |
|---|---|---|
| `kairos service list` | List all managed services across all 6 tiers | Any |
| `kairos service list --category TRADING` | Filter services by tier (SYSTEM, DESKTOP, TRADING, RESEARCH, AI, ADAPTIVE) | Any |
| `kairos service status <service>` | Detailed health, uptime, dependencies, restart policy, and limits | Any |
| `kairos service start <service>` | Start an inactive service | Admin (`wheel` / root) |
| `kairos service stop <service>` | Stop a service (Protected: `kairos-riskd` cannot be killed while live) | Admin (`wheel` / root) |
| `kairos service restart <service>` | Perform a graceful service restart | Admin (`wheel` / root) |
| `kairos service logs <service> [-n N]` | Stream recent service journal logs | Any |

---

## 4. Startup Ordering & Dependency Matrix

| Service | After / Dependencies | PartOf Target | Restart Policy | Resource Limits |
|---|---|---|---|---|
| `kairos-sysd` | `local-fs.target`, `systemd-sysctl` | `kairos-system.target` | `always` (1s) | `TasksMax=256` |
| `kairos-watchdog` | `kairos-sysd.service` | `kairos-system.target` | `always` (1s) | Latency monitored |
| `kairos-riskd` | `kairos-sysd.service`, `network.target` | `kairos-trading.target` | `always` (1s) | `LimitMEMLOCK=infinity`, `RR/90` |
| `kairos-feedd` | `kairos-riskd.service`, `network-online.target` | `kairos-trading.target` | `always` (2s) | `MemoryMax=1G`, `CPUQuota=100%` |
| `kairos-researchd` | `kairos-sysd.service` | `kairos-research.target` | `on-failure` (5s) | `MemoryMax=4G`, `Nice=10` |
| `kairos-agentd` | `kairos-riskd.service`, `kairos-sysd.service` | `kairos-ai.target` | `always` (3s) | `MemoryMax=2G`, `CPUQuota=150%` |
| `kairos-adaptived` | `kairos-watchdog.service`, `kairos-sysd.service` | `kairos-adaptive.target` | `always` (2s) | `MemoryMax=512M`, `CPUQuota=50%` |
