# KAIROS Capability-Based Plugin Platform Architecture

## 1. Overview & Core Philosophy

The KAIROS Plugin Platform empowers traders, quantitative researchers, and software engineers to extend the OS through sandboxed, capability-gated modules.

Plugins are **capability modules**, not arbitrary scripts or unchecked extensions. They run within isolated process containers (`IsolationTier.PLUGIN`) and communicate exclusively through typed, permission-checked IPC interfaces.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     KAIROS PLUGIN PLATFORM ARCHITECTURE                 │
├─────────────────────────────────────────────────────────────────────────┤
│  Categories (12 Certified Capability Domains):                          │
│  [Market Data] [Broker]    [Strategy]   [Indicator]                     │
│  [Research]    [AI]        [Analytics]  [News]                          │
│  [Sentiment]   [Charts]    [Workspace]  [System Automation]             │
├─────────────────────────────────────────────────────────────────────────┤
│  Plugin Manifest Model:                                                 │
│  - id, name, version, type ("capability-module")                        │
│  - permissions: explicitly granted capability tokens                    │
│  - denied: mandatory immutable explicit prohibitions                    │
│  - provides: published capabilities exported by plugin                  │
│  - dependencies: declared package / service constraints                 │
│  - security_level: SANDBOXED_RESTRICTED | CAPABILITY_GATED | CERTIFIED   │
│  - signature: ed25519 / sha256 cryptographic publisher hash            │
├─────────────────────────────────────────────────────────────────────────┤
│  Security Invariants (HARD OS ENFORCEMENT):                             │
│  - Plugins NEVER automatically receive unrestricted privileges          │
│  - Plugins CANNOT execute live orders (order.execute is blocked)        │
│  - Plugins CANNOT modify pre-trade Risk limits (risk.modify is blocked) │
│  - Plugins CANNOT access live broker credentials or private keys        │
│  - Plugins CANNOT bypass RiskD or write to /etc/kairos/vault            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Plugin Categories

KAIROS classifies plugins into 12 capability domains:
1. **Market Data**: Normalized tick feeds, synthetic depth, alternative venues.
2. **Broker**: Execution adapters (always routed through `RiskD` gatekeeper).
3. **Strategy**: Quantitative alpha generation, signal models.
4. **Indicator**: Technical analysis, microstructure indicators, orderbook skew.
5. **Research**: Vectorized factor libraries, backtesting metrics, replay hooks.
6. **AI**: Local LLM reasoning tools, autonomous advisory agents.
7. **Analytics**: Real-time regime classification, volatility surface forecasting.
8. **News**: Financial wire feeds, RSS aggregators, macro data calendars.
9. **Sentiment**: NLP sentiment extractors, entity linkers.
10. **Charts**: GPU-accelerated Wayland visualizers, 3D surface charts.
11. **Workspace**: Multi-monitor Hyprland layout automations, tiling matrices.
12. **System Automation**: Kernel IRQ tuning, low-latency CPU governor automation.

---

## 3. Plugin Manifest Specification

Every plugin package (`.kpx` or directory) must bundle a valid, signed manifest:

```yaml
id: kairos.regime-detector
name: Market Regime Detector
version: 1.0.0
category: Analytics
type: capability-module
permissions:
  - market.read
  - strategy.read
  - telemetry.read
denied:
  - order.execute
  - risk.modify
  - credential.read
provides:
  - regime.classification
  - volatility.forecast
dependencies:
  kairos.core: ">=1.0.0"
security_level: SANDBOXED_RESTRICTED
signature: "sha256:36e99337a37c25468c7d17bcc7042f3fbda706fa83e8745700f88dcdb4924d1f"
signer: "KAIROS Certified Publisher"
```

### Mandatory Explicit Denials
To eliminate privilege escalation, plugin manifests **must explicitly declare** the denial of critical OS privileges:
- `order.execute`
- `risk.modify`
- `credential.read`

Any plugin attempting to request these permissions or omitting their explicit denial is **instantly rejected** during installation and verification.

---

## 4. Cryptographic Signature & Verification Strategy

1. **Canonical Serialization**: Manifest attributes (`id`, `name`, `version`, `category`, `permissions`, `denied`, `provides`, `security_level`) are canonicalized and sorted deterministically.
2. **Cryptographic Hashing**: Signatures are verified against the certified KAIROS publisher key seed.
3. **Tamper Detection**: If any permission or capability is modified post-signing, signature verification fails and the plugin is placed into `ERROR` state and refused execution.

---

## 5. Lifecycle State Machine

```
[UNINSTALLED] ──(install)──> [INSTALLED] ──(verify)──> [ENABLED] <──(enable)──┐
      ▲                            │                                           │
      │                            ▼                                           │
  (remove)                     [ERROR]                                     (disable)
      │                                                                        │
      └────────────────────────────────────────────────────────── [DISABLED] ──┘
```

- **Install**: Ingests manifest, verifies cryptographic signature, stages files, registers in `/var/lib/kairos/plugins/installed/`.
- **Verify**: Audit of declared permissions, capability containment, and cryptographic hashes.
- **Enable / Disable**: Runtime activation/deactivation via `kairos-sysd` IPC without system restart.
- **Remove**: Clean uninstallation and purge of plugin assets.

---

## 6. CLI Management Commands

Operators and traders manage plugins via the unified `kairos plugin` interface:

```bash
# List all active plugins
kairos plugin list

# Search plugin catalog
kairos plugin search regime

# Inspect plugin manifest, security audit, and permissions
kairos plugin info kairos.regime-detector

# Install certified plugin
kairos plugin install kairos.news-sentiment-nlp

# Enable / disable plugins dynamically
kairos plugin disable kairos.regime-detector
kairos plugin enable kairos.regime-detector

# Remove plugin
kairos plugin remove kairos.news-sentiment-nlp
```
