# KAIROS Operating System - GPU Compatibility & Hardware Graphics Matrix

## 1. Architectural Overview

KAIROS adopts **Wayland** as its primary display architecture, completely decoupling the window management and rendering pipeline from legacy X11 protocol vulnerabilities and architectural bottlenecks.

The graphics stack operates through direct kernel-space interfaces via the **Direct Rendering Manager (DRM)** and **Kernel Mode Setting (KMS)**, communicating through hardware-accelerated **Generic Buffer Management (GBM)**.

```
+-------------------------------------------------------------------------+
|                  KAIROS Trading Shell / Quant Lab UI                    |
+-------------------------------------------------------------------------+
|      Hyprland Wayland Compositor (KMS / wlroots-native architecture)     |
+-------------------------------------------------------------------------+
| Wayland Protocols:                                                      |
|   - wp-fractional-scale-v1 (HiDPI dynamic scaling)                     |
|   - wp-tearing-control-v1 (Zero-lag rendering for high-frequency charts)|
|   - linux-dmabuf-v1 (Zero-copy GPU buffer sharing)                     |
|   - linux-drm-syncobj-v1 (Explicit synchronization)                     |
+-------------------------------------------------------------------------+
| Mesa 3D Graphics Library / Hardware Drivers (Vulkan / OpenGL EGL / GBM) |
+-------------------------------------------------------------------------+
| Direct Rendering Manager (DRM / KMS) Kernel Subsystem                   |
|   - Primary DRM Nodes:  /dev/dri/card0, /dev/dri/card1                  |
|   - Render DRM Nodes:   /dev/dri/renderD128, /dev/dri/renderD129        |
+-------------------------------------------------------------------------+
| Hardware Layer: Intel Arc/Iris | AMD Radeon | NVIDIA RTX | VirtIO-GPU   |
+-------------------------------------------------------------------------+
```

---

## 2. Multi-Vendor GPU Compatibility Matrix

KAIROS strictly avoids hardcoding a single vendor. The hardware detection engine (`kairos gpu info`) dynamically evaluates PCI bus classes (`0x0300`, `0x0302`, `0x0380`) and DRM driver bindings.

| Vendor | GPU Architecture / Models | Kernel Driver | Userspace Driver (Mesa / NV) | Support Tier | Default Settings |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Intel** | Arc (Alchemist, Battlemage), Meteor Lake, Raptor Lake, Alder Lake | `xe` (new) or `i915` | Mesa Iris (`crocus`/`iris`), ANV Vulkan | **Tier 1 (Optimal)** | Native GBM, atomic KMS, zero-copy buffer sharing |
| **Intel** | UHD 620/630, Skylake, Kaby Lake, Haswell | `i915` | Mesa Iris / i965 | **Tier 1 (Optimal)** | Full hardware acceleration, dynamic power management |
| **AMD** | RDNA 3 (RX 7000), RDNA 2 (RX 6000), RDNA 1 (RX 5000) | `amdgpu` | Mesa RadeonSI, RADV Vulkan | **Tier 1 (Optimal)** | FreeSync / VRR, tear-free atomic KMS, native GBM |
| **AMD** | GCN 1.0 - 5.0 (Vega, Polaris, RX 400/500) | `amdgpu` | Mesa RadeonSI, RADV Vulkan | **Tier 1 (Optimal)** | Robust open-source KMS/DRM stack |
| **NVIDIA** | GeForce RTX 40/30/20 Series, Ada Lovelace, Ampere, Turing | `nvidia` (Proprietary) | NVIDIA NV-GBM, EGL-Wayland | **Tier 1 (Supported)** | Requires `nvidia-drm.modeset=1`, `NVreg_PreserveVideoMemoryAllocations=1` |
| **NVIDIA** | Older GeForce (GTX 900/1000 Series / Nouveau) | `nouveau` | Mesa Nouveau, NVK Vulkan | **Tier 2 (Compatible)**| Open-source kernel driver, basic hardware 2D/3D acceleration |
| **VirtIO / QEMU**| Paravirtualized VirtIO-GPU 3D (`virgl`) | `virtio-gpu` | Mesa Virgl | **Tier 1 (VM Default)**| Host 3D passthrough, zero-lag emulated desktop in QEMU/KVM |
| **VMware** | VMware Workstation / ESXi SVGA3D | `vmwgfx` | Mesa VMware SVGA3D | **Tier 1 (VMware)** | Full 3D guest acceleration |
| **Microsoft** | WSLg DirectX 12 vGPU | `dxgkrnl` | Mesa D3D12 / WSLg | **Tier 1 (WSL Accelerated)** | Hardware D3D12 passthrough for Windows container dev |
| **Generic / Fallback** | Universal Framebuffer / Bochs / Cirrus / SimpleDRM | `simpledrm` / `bochs-drm` | Mesa LLVMpipe (CPU Software) | **Tier 3 (Safe Fallback)** | Guaranteed display output on any machine without discrete driver |

---

## 3. Display, Scaling & Multi-Monitor Architecture

Quantitative trading terminals and financial analytics environments require multi-display determinism and ultra-clear typography:

1. **Multi-Monitor Layouts**:
   - Monitored dynamically via DRM hotplug events (`udev`).
   - Workspaces are deterministically mapped to specific outputs (e.g. Workspace 1 for Terminal/Quant Lab, Workspace 2 for High-Frequency Order Execution).
   - Display positioning and refresh rates configured in `/etc/hypr/hyprland.conf`:
     ```ini
     monitor = DP-1, preferred, 0x0, 1.25
     monitor = DP-2, preferred, 2560x0, 1.25
     monitor = , preferred, auto, 1.0
     ```

2. **Fractional Scaling (HiDPI)**:
   - Full support for `wp-fractional-scale-v1` Wayland protocol.
   - Eliminates blurriness on 1440p (1.25x) and 4K (1.5x, 1.75x) high-density monitors.

3. **Subpixel Typography & Rendering**:
   - Primary sans-serif font: Inter & Noto Sans VF.
   - Monospace font: JetBrains Mono / Cascadia Code.
   - Freetype subpixel LCD anti-aliasing with Fontconfig geometry tuning.

4. **Zero-Lag Cursor & Pointer Rendering**:
   - Hardware cursor plane overlay via DRM KMS.
   - Default theme: `Adwaita` / `Bibata Modern Ice` at 24px.

---

## 4. Input Subsystem & Libinput Tuning

The input architecture uses `libinput` over Linux kernel `evdev` devices:

- **Keyboards**:
  - Repeat rate: `50` characters/sec.
  - Repeat delay: `200` ms (optimized for command line & code navigation).
  - CapsLock remapped to Escape (`caps:escape`) for vi/neovim speed.
- **Mice**:
  - Acceleration profile: `flat` (raw 1:1 sensor input, zero artificial curve or smoothing).
  - Sensitivity: `0` (true sensor hardware reporting).
- **Touchpads**:
  - `natural_scroll = true`
  - `tap-to-click = true`
  - `disable_while_typing = true`
  - 3-finger horizontal swipe for workspace switching.

---

## 5. Productivity Daemons: Clipboard & Screenshots

Wayland isolates window surfaces, preventing unprivileged apps from sniffing keystrokes or screen buffers. KAIROS provides secure desktop integration:

1. **Clipboard Subsystem**:
   - Engine: `wl-clipboard` (`wl-copy`, `wl-paste`).
   - Persistent Daemon: `cliphist` integration via background listener.
   - Hotkey: `Super + V` opens an interactive fuzzy clipboard history.

2. **Screenshot Subsystem**:
   - Engine: `grim` (Wayland DRM screen capture) + `slurp` (interactive geometry selection).
   - Keybindings:
     - `Super + Print`: Fullscreen snapshot directly copied to clipboard.
     - `Super + Shift + S` or `Super + Shift + Print`: Interactive region selector copied to clipboard.

---

## 6. Telemetry & Verification Commands

KAIROS includes first-class CLI telemetry commands to audit graphics, displays, and input devices:

```bash
# Audit GPU hardware, driver acceleration, and DRM nodes
kairos gpu info

# Audit Wayland compositor status, connected monitors, scaling, and desktop features
kairos display info

# Audit keyboard, mouse, and touchpad low-latency configurations
kairos input info
```
