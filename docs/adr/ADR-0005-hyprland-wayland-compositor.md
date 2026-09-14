# ADR-0005: Hyprland Wayland Compositor Selection

* **Status**: Accepted
* **Date**: 2026-09-14
* **Authors**: KAIROS Architecture Team
* **Technical Area**: Desktop & Display Engineering

---

## Context and Problem Statement
Professional traders and quantitative researchers rely on multi-monitor setups (typically 2 to 6 displays) with dense financial charts, order books, execution terminals, and risk monitors. Legacy X11 compositors suffer from tearing, per-monitor mixed DPI scaling issues, and lack modern security isolation between windows (any X11 client can log keystrokes from other windows).

## Decision Outcome
Adopt **Hyprland** (Wayland) as the primary desktop compositor:
- **Zero-Tearing DRM/KMS**: Hardware-accelerated presentation via Vulkan/OpenGL.
- **Dynamic & Deterministic Tiling**: Configurable workspace pinning per monitor (`workspace = 1, monitor:DP-1`).
- **Security Isolation**: Wayland protocol isolates window input, preventing malicious applications or compromised plugins from keylogging trading credentials.
- **KAIROS Shell**: Integrated Waybar bar displaying real-time financial ticker ribbons, market latency, and risk status.

### Consequences
* **Positive Consequences**:
  - Fluid animations, multi-DPI monitor support, and input security.
* **Negative Consequences**:
  - Requires Wayland-compatible applications (XWayland fallback provided for legacy financial software).
