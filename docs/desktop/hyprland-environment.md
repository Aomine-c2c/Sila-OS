# KAIROS Desktop Architecture & Hyprland Integration Guide

## 1. Overview & Architectural Role

**Hyprland is the foundation of the KAIROS desktop environment, not the final desktop itself.**

KAIROS is an operating system engineered for quantitative trading, high-frequency execution monitoring, and financial research. As such, the graphical layer is deliberately decoupled from monolithic desktop suites (GNOME/KDE) to guarantee:
1. **Zero Unnecessary Overhead**: No background indexers, telemetry trackers, or complex desktop shells competing with market data feeds.
2. **Deterministic Multi-Monitor Windows**: Explicit workspace bindings so charting and risk monitors never shift unexpectedly.
3. **Independent OS Stability**: The graphics stack is completely isolated. If Hyprland, Waybar, or any desktop utility crashes or fails to start, **the core operating system remains 100% operational, immediately recoverable via rescue TTY or SSH**.

```
+-------------------------------------------------------------------------------+
|                       KAIROS Graphical Workstation Layer                      |
+-------------------------------------------------------------------------------+
| Hyprland Wayland Compositor (wlroots / KMS atomic / zero-copy DRM leasing)    |
|   + Session Supervisor: /usr/libexec/kairos/kairos-session-watchdog.sh        |
+-------------------------------------------------------------------------------+
| Desktop Utilities & Daemons:                                                  |
|   * Terminal:       foot (Primary zero-lag Wayland) / kitty (Fallback)        |
|   * Status Bar:     Waybar (Risk status, latency jitter, market tickers, tray)|
|   * Launcher:       Wofi (Cyan minimal modal application runner)               |
|   * Notifications:  Mako (P0 critical risk alerts + toast notifications)      |
|   * Auth Agent:     polkit-gnome (PolicyKit privilege escalation)             |
|   * Idle & Locker:  swayidle + swaylock (Auto-lock after 10m, screen off 15m)|
|   * Background:     swaybg (Minimalist slate-black OLED #0a0c10)             |
|   * Clipboard:      wl-clipboard + cliphist (Super + V interactive history)   |
|   * Screenshots:    grim + slurp (Full screen or interactive selection)       |
|   * Media/Audio:    pamixer + playerctl (Dedicated XF86 hardware keys)        |
|   * Network UI:     nm-applet (System tray integration + nm-connection-editor)|
+-------------------------------------------------------------------------------+
| Linux Kernel (DRM/KMS) -> Systemd Multi-User -> Safe TTY Fallback             |
+-------------------------------------------------------------------------------+
```

---

## 2. Desktop Utilities & Integrated Daemons

| Subsystem | Utility | Binary Path | Function in KAIROS | Failure Resilience |
| :--- | :--- | :--- | :--- | :--- |
| **Compositor** | Hyprland | `/usr/bin/Hyprland` | Tiling Wayland window manager & display compositor | Drops to clean bash login shell on TTY1 |
| **Session Supervisor** | Watchdog | `/usr/libexec/kairos/kairos-session-watchdog.sh` | Supervises desktop daemons; auto-restarts failed utilities | Loops every 3s; independent background subshell |
| **Terminal** | Foot / Kitty | `/usr/bin/foot`, `/usr/bin/kitty` | Primary high-performance terminal emulator | Fallback cascade (`foot \|\| kitty`) |
| **Application Launcher** | Wofi | `/usr/bin/wofi` | Keyboard-first search launcher (`Super + Space`) | Non-daemon, on-demand invocation |
| **Notification Daemon** | Mako | `/usr/bin/mako` | Urgent risk violation alerts and system telemetry | Supervised; critical alerts persist without timeout |
| **Clipboard Manager** | wl-clipboard + cliphist | `/usr/bin/wl-copy`, `/usr/bin/cliphist` | Zero-leak clipboard manager with history (`Super + V`) | Independent background store pipeline |
| **Screenshot Utility** | Grim + Slurp | `/usr/bin/grim`, `/usr/bin/slurp` | Instant atomic screen buffer capture to clipboard | Non-daemon; direct Wayland protocol client |
| **Authentication Agent**| Polkit GNOME | `/usr/libexec/polkit-gnome-authentication-agent-1` | Graphical privilege authorization for admin tasks | Supervised by session watchdog |
| **Wallpaper / BG** | Swaybg | `/usr/bin/swaybg` | Pure dark aesthetic (`#0a0c10`) with zero RAM overhead | Supervised by session watchdog |
| **Idle Management** | Swayidle | `/usr/bin/swayidle` | Standby detection (lock at 10m, DPMS off at 15m) | Supervised; resumes instantly on input event |
| **Screen Locker** | Swaylock | `/usr/bin/swaylock` | Secure screen locking (`Super + Escape` or idle) | Pam-authenticated; prevents display snooping |
| **Audio Controls** | Pamixer + Playerctl | `/usr/bin/pamixer`, `/usr/bin/playerctl` | Volume increment/decrement, mute toggle, track control | Integrated into hardware keys and Waybar |
| **Network Controls** | nm-applet | `/usr/bin/nm-applet` | Network connection management & tray status | Supervised in system tray; CLI fallback via `kairos network` |

---

## 3. Dedicated Financial Workspaces

KAIROS provides **5 deterministic workspaces** tailored to institutional trading workflow:

1. **Workspace 1 [Quant / Execution]** (`Super + 1`):
   - Primary shell terminals (`foot`), tmux sessions, strategy code editors, build engines.
2. **Workspace 2 [Market Data & Charts]** (`Super + 2`):
   - Real-time market data feeds, candlestick charting, Level 2 depth-of-book windows.
3. **Workspace 3 [Risk & Telemetry]** (`Super + 3`):
   - Live risk gatekeeper monitoring, system telemetry, audit trail journal loggers.
4. **Workspace 4 [Research & Analytics]** (`Super + 4`):
   - Jupyter notebooks, Python exploratory data science, backtesting visualizations.
5. **Workspace 5 [Communications]** (`Super + 5`):
   - Institutional chat, broker communication portals, team alerts.

---

## 4. Complete Keybinding Reference

All keybindings prioritize **keyboard-first ergonomics**, minimizing reliance on mouse navigation during rapid market movements.

### 4.1 Application Launchers & Session Control
| Keybinding | Action / Command | Description |
| :--- | :--- | :--- |
| `Super + Return` | `foot \|\| kitty` | Launch primary low-latency terminal |
| `Super + Shift + Return` | `foot -e tmux` | Launch terminal attached to default tmux multiplexer |
| `Super + Space` | `wofi --show drun` | Open fuzzy application launcher |
| `Super + E` | `foot -e lf \|\| thunar` | Open lightweight terminal file manager |
| `Super + Q` | `killactive` | Gracefully close active window |
| `Super + Shift + Q` | `hyprctl kill` | Force-kill unresponsive trading window |
| `Super + Escape` | `swaylock ...` | Immediately lock the screen |
| `Super + Shift + Escape` | `exit` | Gracefully terminate Wayland session and return to console |
| `Super + R` | `foot -e kairos system info` | Launch KAIROS system telemetry in a terminal |

### 4.2 Clipboard & Screenshots
| Keybinding | Action / Command | Description |
| :--- | :--- | :--- |
| `Super + V` | `cliphist list \| wofi ...` | Interactive clipboard history picker (copies selection) |
| `Print` or `Super + Print` | `grim - \| wl-copy` | Capture full display and save to clipboard |
| `Super + Shift + S` | `grim -g "$(slurp)" - \| wl-copy` | Interactive rectangular region screenshot to clipboard |
| `Shift + Print` | `grim -g "$(slurp)" - \| wl-copy` | Alternative interactive region screenshot to clipboard |

### 4.3 Hardware Audio & Media Controls
| Keybinding | Action / Command | Description |
| :--- | :--- | :--- |
| `XF86AudioRaiseVolume` | `pamixer -i 5` | Increase master volume by 5% |
| `XF86AudioLowerVolume` | `pamixer -d 5` | Decrease master volume by 5% |
| `XF86AudioMute` | `pamixer -t` | Toggle audio mute |
| `XF86AudioPlay` | `playerctl play-pause` | Play / pause media playback |
| `XF86AudioNext` | `playerctl next` | Next audio track |
| `XF86AudioPrev` | `playerctl previous` | Previous audio track |

### 4.4 Window Navigation & Tiling
| Keybinding | Action / Direction | Description |
| :--- | :--- | :--- |
| `Super + H / J / K / L` | Left / Down / Up / Right | Focus adjacent window (Vim navigation) |
| `Super + Arrow Keys` | Left / Down / Up / Right | Focus adjacent window (Standard navigation) |
| `Super + Shift + H/J/K/L`| Left / Down / Up / Right | Swap active window with adjacent window |
| `Super + F` | Fullscreen (Toggle) | Fullscreen active window (0-gaps) |
| `Super + Shift + F` | Monocle Mode | Maximize active window while preserving gaps/bar |
| `Super + T` | Floating (Toggle) | Toggle floating state for active window |
| `Super + S` | Toggle Split | Toggle horizontal vs vertical dwindle tiling split |
| `Super + LMB Drag` | Mouse Move | Move floating or tiled window |
| `Super + RMB Drag` | Mouse Resize | Resize window dynamically |

### 4.5 Multi-Monitor & Workspace Switching
| Keybinding | Action | Description |
| :--- | :--- | :--- |
| `Super + 1 .. 5` | Switch Workspace | Instantly switch to workspace 1 through 5 |
| `Super + Shift + 1 .. 5` | Move Window to Workspace | Move active window to workspace 1 through 5 |
| `Super + comma (,)` | `focusmonitor, -1` | Shift focus to the left/previous monitor |
| `Super + period (.)` | `focusmonitor, +1` | Shift focus to the right/next monitor |
| `Super + Shift + comma` | `movewindow, mon:-1` | Move active window to left/previous monitor |
| `Super + Shift + period`| `movewindow, mon:+1` | Move active window to right/next monitor |

---

## 5. Fault Isolation & Crash Recovery Strategy

KAIROS adheres to the **Independent OS Stability** architectural invariant:

1. **Subsystem Isolation**:
   - The Wayland display server and Hyprland compositor run entirely as unprivileged user session processes.
   - If Hyprland crashes, `systemd` or the user session drops safely to standard Linux virtual terminal (`tty1` or `tty2`).
2. **Watchdog Auto-Healing**:
   - The session watchdog (`/usr/libexec/kairos/kairos-session-watchdog.sh`) continuously polls `waybar`, `mako`, `polkit-gnome`, `swayidle`, and `nm-applet`. If any utility terminates, it is restarted within 3 seconds without causing window disruption or session loss.
3. **Headless / Rescue Guarantee**:
   - Graphical failure **never prevents system boot**.
   - Kernel parameter `kairos.mode=fallback` automatically boots with `nomodeset` into a safe recovery shell.
   - Core trading engines (`kairos-riskd`, `kairos-watchdog`) run as dedicated systemd system services independent of the graphical desktop.
