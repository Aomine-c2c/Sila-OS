# KAIROS Design System & Visual Language Specification

## 1. Visual Philosophy & Core Invariants

The KAIROS design system establishes a **calm, precise, information-dense, and highly disciplined** visual language for an operating system engineered for quantitative trading, financial data analytics, and autonomous system health.

```
       MINIMAL  +  TECHNICAL  +  CALM  +  INFORMATION-DENSE
```

### 1.1 Strict Aesthetic Boundaries ("What We Avoid")
- **NO Generic Crypto Aesthetics**: No neon glowing purple/magenta laser lines, speculative rocket icons, or dark neon hyper-saturation.
- **NO Excessive Glassmorphism or Heavy Blurs**: Transparent blurs consume GPU cycles and degrade text legibility during fast order book updates.
- **NO Gratuitous Rounded Cards**: Maximum border radius is restrained to `4px` (`sharp: 2px`).
- **NO Decorative Charts**: Graphs must serve an operational purpose (e.g. latency jitter, drawdown trajectory); no decorative sparklines filling empty space.
- **NO Gaming UI Elements**: No angled sci-fi polygonal frames or distracting micro-animations.
- **DEFAULT TO LIGHT MODE**: Default system theme is a calm, high-contrast, paper-precise Light Mode (`#f8fafc`). Dark Mode (`#0a0c10`) is provided as an ergonomic option for low-light trading pits.

---

## 2. Design Tokens

The complete token specification is formally defined in [`config/desktop/kairos-design-tokens.json`](file:///c:/Users/armut/404/OS/config/desktop/kairos-design-tokens.json) and exported to CSS custom properties in [`config/desktop/kairos-tokens.css`](file:///c:/Users/armut/404/OS/config/desktop/kairos-tokens.css).

### 2.1 Typography
- **Monospace (Data / Code / Tickers)**: `'JetBrains Mono', 'Roboto Mono', 'SF Mono', monospace`
- **Sans-Serif (Labels / Navigation)**: `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- **Scale**:
  - `xs`: `11px` (Telemetry indicators, timestamp offsets)
  - `sm`: `12px` (Waybar modules, table data cells)
  - `base`: `13px` (Terminal output, command palette results)
  - `md`: `14px` (Section headers, modal inputs)
  - `lg`: `16px` (Dialog titles, alert summaries)
  - `xl`: `18px` (Display headers)
- **Line Heights**: Dense (`1.2`) for high-frequency financial data tables; Normal (`1.4`) for narrative documentation.

### 2.2 Spacing & Layout Rhythm
- `2xs`: `2px` (Tight table row padding, micro badges)
- `xs`: `4px` (Window gaps in Hyprland, button icon spacing)
- `sm`: `6px` (Outer Hyprland gaps, pill margins)
- `md`: `8px` (Standard card padding, form input padding)
- `lg`: `12px` (Modal headers, sidebar spacing)
- `xl`: `16px` (Window margins)
- `2xl`: `24px` (Workspace panel separation)

### 2.3 Borders & Elevation
- **Border Radii**:
  - `none`: `0px` (Waybar bar, terminal borders)
  - `sharp`: `2px` (Buttons, workspace pills, table entries)
  - `standard`: `4px` (Dialog windows, Mako toasts, Wofi prompt)
- **Border Width**: `1px` standard hairline; `2px` for active window borders and keyboard focus rings.
- **Elevation**: Flat, non-blurred subtle shadows (`0 1px 2px rgba(15,23,42,0.05)` in Light Mode; `0 1px 2px rgba(0,0,0,0.3)` in Dark Mode).

### 2.4 Surfaces & Color Matrix

| Token Role | Light Mode (Default) | Dark Mode (Optional) | Semantic Usage |
| :--- | :--- | :--- | :--- |
| `surface-base` | `#f8fafc` (Slate 50) | `#0a0c10` (True Black/Slate) | Root desktop background & wallpaper |
| `surface-panel`| `#ffffff` (Pure White) | `#11141b` (Deep Slate) | Top bar, terminal background, windows |
| `surface-elevated`| `#f1f5f9` (Slate 100) | `#181c26` (Muted Slate) | Active cards, command palette popover |
| `surface-sunken`| `#e2e8f0` (Slate 200) | `#06080a` (OLED Black) | Inactive tabs, scroll tracks |
| `border-subtle`| `#e2e8f0` (Slate 200) | `#1e2330` | Inactive window borders, dividers |
| `border-default`| `#cbd5e1` (Slate 300) | `#333b4f` | Active cards, input borders |
| `border-focus` | `#0284c7` (Sky Blue) | `#00f0ff` (Cyan) | Keyboard focus ring, active window border |
| `text-primary` | `#0f172a` (Slate 900) | `#f1f5f9` (Slate 100) | Primary headers, data figures, code |
| `text-secondary`| `#475569` (Slate 600) | `#94a3b8` (Slate 400) | Labels, descriptions, table headers |
| `text-muted` | `#64748b` (Slate 500) | `#64748b` | Timestamps, inactive shortcuts |

### 2.5 Status States
- **Nominal / Healthy**:
  - Light: Text `#059669` (Emerald 600), Bg `#ecfdf5`, Border `#10b981`
  - Dark: Text `#00ff88` (Bright Emerald), Bg `rgba(0,255,136,0.12)`, Border `#00ff88`
- **Warning / Caution**:
  - Light: Text `#d97706` (Amber 600), Bg `#fffbeb`, Border `#f59e0b`
  - Dark: Text `#ffd700` (Gold), Bg `rgba(255,215,0,0.12)`, Border `#ffd700`
- **Critical / Risk Breach**:
  - Light: Text `#dc2626` (Red 600), Bg `#fef2f2`, Border `#ef4444`
  - Dark: Text `#ff3366` (Crimson), Bg `rgba(255,51,102,0.15)`, Border `#ff3366`
- **Informational / Sync**:
  - Light: Text `#0284c7` (Sky 600), Bg `#f0f9ff`, Border `#38bdf8`
  - Dark: Text `#00f0ff` (Cyan), Bg `rgba(0,240,255,0.12)`, Border `#00f0ff`

---

## 3. Core Iconography & The Adaptive Ring

The core identity of KAIROS is anchored by the **Adaptive Evolutionary Ring**, an original mechanical/evolutionary symbol embodying the 6 phases of runtime adaptation:

```
                  [1. OBSERVE]
                       │
          [6. LEARN] ──┼── [2. DIAGNOSE]
                 \     │     /
                  \    │    /
          [5. DEPLOY] ─┴─ [3. ADAPT]
                       │
                 [4. VALIDATE]
```

### The 6 Stages of the Adaptive Ring:
1. **OBSERVE**: Continuous hardware telemetry, packet latency, and order flow metrics capture.
2. **DIAGNOSE**: Deterministic identification of scheduling jitter, link saturation, or queue bottlenecks.
3. **ADAPT**: Safe, bounded runtime parameter adjustment (e.g. tuning `net.core.busy_poll`).
4. **VALIDATE**: Verification through immutable `RiskGatekeeper` invariants and integrity checks.
5. **DEPLOY**: Atomic execution of the optimized heuristic.
6. **LEARN**: Model parameter retention and baseline convergence.

Vector Source: [`config/desktop/icons/kairos-adaptive-ring.svg`](file:///c:/Users/armut/404/OS/config/desktop/icons/kairos-adaptive-ring.svg)

---

## 4. Official System Icon Concepts

The 15 official technical icon concepts are authored in [`config/desktop/icons/kairos-icons.svg`](file:///c:/Users/armut/404/OS/config/desktop/icons/kairos-icons.svg):

| Icon Concept | Symbol ID | Semantic Meaning in KAIROS | Visual Motif |
| :--- | :--- | :--- | :--- |
| **KAIROS** | `#icon-kairos` | System identity & adaptive kernel core | Concentric precision reticle with 4 cardinal indexers |
| **Market** | `#icon-market` | Live market feeds & order book depth | Stepped order book bars with price level dot |
| **Strategy** | `#icon-strategy` | Algorithmic logic & execution rules | Dual interconnected decision nodes with logic bridge |
| **Signal** | `#icon-signal` | High-confidence alpha indicator | Single-cycle discrete electrocardiogram pulse |
| **Execution** | `#icon-execution` | Low-latency order strike | Precision crosshair with directional execution vector |
| **Risk** | `#icon-risk` | Hardened immutable RiskGatekeeper | Chiseled protective shield with central lock divider |
| **Broker** | `#icon-broker` | FIX gateway & direct market access | Inter-exchange connection port with dual packet beacons |
| **Research** | `#icon-research` | Quantitative analytics & Jupyter | Structured computational laboratory ledger |
| **AI** | `#icon-ai` | Sandboxed advisory reasoning | Central node surrounded by 4 orbital neural satellites |
| **Plugin** | `#icon-plugin` | Sandboxed capability extension | Modular 4-pin interlock socket |
| **Adaptive** | `#icon-adaptive` | Adaptive Evolution Intelligence (AEI)| Continuous evolutionary gear ring |
| **Rollback** | `#icon-rollback` | Transactional Btrfs snapshot restore | Counter-clockwise rewind vector with anchor point |
| **System** | `#icon-system` | Linux kernel & CPU/memory substrate| Microprocessor die with 8 bus traces |
| **Security** | `#icon-security` | Cryptographic vault & TPM2 state | Hardened padlock with precision keyway |
| **Workspace**| `#icon-workspace` | Multi-monitor deterministic display | Tiling workstation display partition grid |

---

## 5. Theme Switching Architecture

The KAIROS design system enables deterministic switching between **Light Mode** (default) and **Dark Mode** via:
1. Desktop Command: `kairos theme set light` or `kairos theme set dark`.
2. Automatic generation of `/etc/kairos/shell/theme.css` and updates to `waybar.css` and `foot.ini`.
3. Non-disruptive hot-reloading without terminating active trading applications or Wayland window surfaces.
