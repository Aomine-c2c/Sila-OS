# KAIROS Desktop Shell Architecture & IPC Specification

## 1. Executive Summary

The KAIROS Desktop Shell provides a **native, lightweight, modular desktop environment** designed specifically for high-frequency quantitative trading, portfolio risk control, and data research.

**This is NOT a web application or browser dashboard pretending to be an OS.**
It is an orchestrated Linux desktop environment interfacing through defined IPC protocols:
- **Display Layer**: Hyprland Wayland compositor with atomic KMS.
- **Top Status Bar**: Custom `Waybar` displaying live market quotes, Risk Gatekeeper status, broker connectivity, latency jitter, audio, network, battery, and clock.
- **Application & Strategy Launcher**: `Wofi` running in modal application runner mode (`Super + Space`).
- **Command Palette & Action Engine**: `kairos_cmd.py` invoked via `Super + P`, resolving typed, permission-checked commands into system actions.
- **Session Supervisor**: `kairos-session-watchdog.sh` auto-restarting crashed shell components within 3 seconds.

```
+-------------------------------------------------------------------------------+
|                       KAIROS Top Status Bar (Waybar)                          |
|  [◈ KAIROS] [1:Quant 2:Mkt 3:Risk 4:Res 5:Comms] [⌘ CMD] [🛡️ RISK: LOCKED]   |
|  [Center: SPY 504.20 ▲ | BTC 64,120 ▲]                                        |
|  [Right: ⚡ BROKERS: OK | ⚙ AEI: OPTIMAL | ⚡ 0.12ms | 🔊 65% | 󰈀 ETH | 12:00] |
+-------------------------------------------------------------------------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+------------------------+                     +------------------------+
|  KAIROS Command Engine |                     |  KAIROS IPC State      |
|  (kairos_cmd.py)       |                     |  (kairos_shell_state)  |
|  Super + P             |                     |  /run/kairos/*.json    |
+------------------------+                     +------------------------+
            |                                               |
  (Permission Check)                               (Read-Only Telemetry)
            |                                               |
            v                                               v
+-------------------------------------------------------------------------------+
|                      Linux Kernel & OS Core Services                          |
|  - Hyprland Window Manager (Workspaces, Monocle, Tiling)                      |
|  - Immutable Risk Gatekeeper Daemon (kairos-riskd / risk.sock)                |
|  - Network Latency Telemetry Daemon (kairos-netmon)                           |
|  - System Latency & Hardware Watchdog (kairos-watchdog)                       |
|  - Hardware Subsystem (DRM/KMS, Mesa, WirePlumber, PAM, Systemd Logind)       |
+-------------------------------------------------------------------------------+
```

---

## 2. Shell Modular Architecture & IPC Boundaries

The KAIROS desktop shell operates across strict architectural boundaries:
1. **Read-Only Telemetry**: The UI layer receives updates by polling or listening to IPC state exports (`/run/kairos/shell_state.json` and `/var/run/kairos/risk_status.txt`).
2. **Strict Separation of Concerns**: UI components **never** directly place broker trades or modify kernel sysctl parameters.
3. **Immutable Risk Gatekeeper Boundary**: Trading orders can only be proposed by trading strategies or AI agents; they must pass the `RiskGatekeeper` pipeline before broker routing. The shell only observes and displays risk telemetry.

### Telemetry Subsystems Provided:
- **System**: CPU utilization, RAM usage, cores, architecture, uptime.
- **Network**: Link state, active IP address, default gateway latency, packet loss, DNS resolution.
- **Audio**: PipeWire / WirePlumber master volume, mute status via `pamixer`.
- **Battery**: AC power vs battery percentage, charging state.
- **Market**: Real-time market state, quotes (SPY, QQQ, BTC/USD, US10Y).
- **Risk**: Hard drawdown limits, position clamps, violation counters from `kairos-riskd`.
- **Brokers**: Primary (FIX), backup (DMA), and institutional WebSocket gateways.
- **Adaptive**: Adaptive Evolution Intelligence (AEI) busy poll budget and latency heuristics.
- **Positions**: Live asset inventory, entry prices, unrealized profit/loss.
- **Plugins**: Capability-sandboxed trading plugins (`read:market_data`, `compute:features`, `emit:signal`).

---

## 3. KAIROS Command Palette (`kairos-cmd`)

The command interface allows keyboard-first control over the operating system (`Super + P`).
Commands resolve into **strongly-typed actions** with role-based access control (RBAC):

| Command | Category | Role Required | Action Performed |
| :--- | :--- | :--- | :--- |
| `open markets` | Navigation | `trader` | Switches Hyprland view to Workspace 2 (Market Data & Real-Time Charts) |
| `open execution` | Navigation | `trader` | Switches Hyprland view to Workspace 1 (Execution Terminals & Quant Shells) |
| `open research` | Navigation | `research` | Switches Hyprland view to Workspace 4 (Jupyter Notebooks & Data Science) |
| `open automation`| Navigation | `trader` | Spawns algorithmic strategy execution review terminal |
| `open agents` | Navigation | `research` | Spawns AI advisory reasoning harness inspection |
| `open system` | Navigation | `trader` | Switches Hyprland view to Workspace 3 (Risk & Telemetry) |
| `open development`| Navigation | `trader` | Spawns developer terminal attached to tmux |
| `open adaptive` | Navigation | `research` | Inspects Adaptive Evolution Intelligence (AEI) heuristics |
| `show positions` | Telemetry | `trader` | Displays active portfolio positions, entry prices, and PnL |
| `show risk` | Telemetry | `trader` | Displays RiskGatekeeper limits, drawdown, and circuit breaker status |
| `show brokers` | Telemetry | `trader` | Displays broker gateway link states and wire latencies |
| `show plugins` | Telemetry | `research` | Displays loaded sandboxed plugins and granted capabilities |
| `show system` | Telemetry | `trader` | Displays hardware utilization, CPU, memory, and uptime |
| `lock` | Session | `trader` | Engages PAM-authenticated `swaylock` screen lock |
| `logout` | Session | `trader` | Gracefully terminates active Wayland compositor session |
| `shutdown` | System Power | `wheel` (Admin) | Safely powers off the operating system via `systemd` logind |
| `reboot` | System Power | `wheel` (Admin) | Safely reboots the operating system via `systemd` logind |

---

## 4. Top Status Bar Modules

The top bar is implemented via `Waybar` (`/etc/kairos/shell/waybar.json` and `/etc/kairos/shell/waybar.css`):
1. **Left Modules**:
   - `custom/logo`: KAIROS logo (Click launches `kairos system info`).
   - `hyprland/workspaces`: Interactive indicator for workspaces 1 through 5.
   - `custom/palette_btn`: `⌘ CMD` quick-action button triggering the command palette.
   - `custom/risk_status`: Live color-coded risk gatekeeper indicator (Click reveals full risk telemetry).
2. **Center Modules**:
   - `custom/market_ticker`: Real-time stock, index, and crypto price quotes (Click displays positions).
3. **Right Modules**:
   - `custom/broker_status`: Real-time broker gateway health (Click displays broker latencies).
   - `custom/adaptive_status`: AEI autonomous runtime optimization indicator.
   - `custom/jitter`: Sub-millisecond timer and network jitter.
   - `pulseaudio`: Interactive audio volume control and mute toggle.
   - `network`: IP address, interface status, and network diagnostic tool launcher.
   - `battery`: Dynamic power/battery level indicator.
   - `cpu`: Real-time CPU core utilization (Click launches `htop`).
   - `memory`: RAM usage in gigabytes.
   - `clock`: High-precision UTC clock.
   - `tray`: System tray for background utilities (`nm-applet`, etc.).

---

## 5. Security & Fault Resilience Invariants

1. **Permission Awareness**:
   - Administrative commands (`shutdown`, `reboot`) enforce `wheel` group membership or UID 0.
   - Unauthorized attempts yield exit code `13` (Permission Denied).
2. **No Direct Trading Manipulation**:
   - Commands like `show positions` and `show risk` query verified read-only IPC state caches.
   - There is no command in the UI palette that can bypass risk limits or send unvalidated orders to brokers.
3. **Non-Blocking OS Boot**:
   - All shell daemons (`waybar`, `mako`, `wofi`, `nm-applet`) run strictly inside user sessions.
   - If any component crashes, `kairos-session-watchdog.sh` automatically relaunches it within 3 seconds.
   - If Wayland fails completely, the operating system remains 100% operational on standard Linux virtual consoles.
