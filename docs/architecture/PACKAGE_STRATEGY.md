# KAIROS Software Layer & Package Strategy

## 1. Executive Summary & Strategy Philosophy

KAIROS OS avoids reinventing low-level package managers. Instead, it engineers a unified, policy-driven **KAIROS Software Layer** over robust, standardized Linux package backends:
1. **Base & Development Systems (`dnf`)**: Minimal RPM foundation providing reproducible glibc, systemd, compiler toolchains (`gcc`, `clang`, `rustc`), and low-latency real-time kernel builds.
2. **Desktop & Charting Applications (`flatpak`)**: Sandboxed, containerized desktop software (`com.tradingview.Desktop`, `org.mozilla.firefox`) with strictly enforced Wayland, audio, and network permission profiles (`/etc/kairos/sandbox/sandbox.ini`).
3. **Quantitative Research Ecosystem (`python / wheels / arrow`)**: High-throughput vectorized data science, factor analytics, and exploratory notebook tools (`polars`, `pyarrow`, `scipy`, `jupyterlab`).
4. **Trading & System Daemons (`kairos native`)**: Low-latency, real-time daemons (`kairos-riskd`, `kairos-feedd`, `kairos-sysd`) managed with hardware memory locking and real-time FIFO/RR scheduling.

---

## 2. Software Taxonomy & Tiered Categories

KAIROS classifies all software into six explicit functional tiers:

| Tier | Purpose | Default State | Backend | Mutability / Invariant |
|---|---|---|---|---|
| **CORE** | Kernel, systemd, glibc, Hyprland, `kairos-sysd` | Installed | `dnf` / `kairos` | **IMMUTABLE**: Cannot be uninstalled or replaced without kernel lockdown violation. |
| **OPTIONAL** | Institutional charting, hardened browsers, office viewers | User-choice | `flatpak` | Sandboxed per-app; no direct raw hardware access. |
| **TRADING** | Immutable Risk Gatekeeper, Level 1/2 Market Feed Gateway | Installed | `kairos` | Protected; requires real-time priority & non-bypassable risk engine. |
| **RESEARCH** | Factor analytics, Arrow/Parquet backtesting, JupyterLab | Installed / User | `python` | Clamped to `Nice=10` and `MemoryMax=4G` to prevent trading interference. |
| **DEVELOPMENT** | C++23/Rust toolchain, eBPF perf tools, cmake | Installed | `dnf` | Standard developer tools for institutional algorithmic strategy compilation. |
| **EXPERIMENTAL** | Prototype quantum annealing, LLM order reasoners | Available | `kairos` | **STRICTLY SANDBOXED**: Zero privilege escalation. **Never permitted to replace critical system components.** |

---

## 3. The Critical Safety Invariant

> **CRITICAL SECURITY INVARIANT:**
> An experimental package (or any 3rd-party plugin) is **strictly forbidden from silently or explicitly replacing a critical system component** (such as `kairos-base`, `kairos-sysd`, `kairos-risk-engine`, `systemd`, `glibc`, or `kernel`).

Any attempt to install an experimental package with replacement flags targeting protected components is intercepted at the `kairos-sysd` boundary and immediately blocked with an audit trail alert:
```text
[BLOCKED / DENIED] CRITICAL SECURITY INVARIANT VIOLATION:
Experimental package 'experimental-quantum-annealer' attempted to replace critical system component 'kairos-base'. Operation BLOCKED.
```

---

## 4. Software Layer CLI Commands

Users and operators manage the entire software catalog through `kairos package`:

```bash
# 1. List all packages across all 6 tiers
kairos package list

# 2. Filter by tier
kairos package list --category TRADING
kairos package list --category EXPERIMENTAL

# 3. Search the registry by keyword
kairos package search risk
kairos package search chart

# 4. Inspect detailed package metadata
kairos package info kairos-risk-engine
kairos package info tradingview-desktop

# 5. Install a package (Delegated to kairos-sysd)
kairos package install tradingview-desktop

# 6. Remove an optional package (Protected against removing CORE)
kairos package remove tradingview-desktop

# 7. Update repository and installed components
kairos package update
```

---

## 5. Sandboxing Policy Specification (`sandbox.ini`)
Configured at `/etc/kairos/sandbox/sandbox.ini`:
```ini
[Policy]
default-filesystem-permission = none
allow-x11 = false
allow-wayland = true
allow-pulseaudio = true
allow-network = false

[Sandboxes.FinancialCharts]
app-id = com.tradingview.Desktop
filesystem = xdg-download:ro
network = true
wayland = true
```
