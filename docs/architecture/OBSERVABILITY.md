# KAIROS Centralized Observability Architecture

The **KAIROS Centralized Observability Subsystem** provides dense, actionable, low-overhead monitoring across all 12 operational domains of the operating system without bloating the system with unnecessary dashboard micro-frontends or high-overhead scrapers.

---

## 1. Monitored Domains (12 Subsystems)

| Subsystem Domain | Monitored Indicators | Enforcement SLA / Health Criteria |
|---|---|---|
| **1. OS** | Load averages (1m, 5m, 15m), memory utilization, architecture, uptime | Load avg within CPU core envelope, swap zero |
| **2. Kernel** | RT preemption (`PREEMPT_RT`), scheduling jitters, timer slips, busy poll | p99 jitter < 25us, zero scheduler slips |
| **3. Services** | Service lifecycle, state, PID, memory, CPU, restart count | Health contract active, auto-restart isolated |
| **4. Desktop** | Hyprland Wayland compositor, Waybar status bar, display scaling, input latency | Frame timing 60-144Hz, zero input latency drops |
| **5. Network** | Link carriers, gateway RTT, packet loss, NIC ringbuffer drops, DNS benchmark | Gateway RTT < 0.20ms, packet loss = 0.0% |
| **6. Storage** | LUKS2 encryption, Btrfs subvolume health, mount table, SMART telemetry | Zero reallocated sectors, discard async active |
| **7. Trading** | MarketD tick volume, StrategyD registry, execution mode (Simulation/Paper/Live) | Ticks > 10,000/sec, feed drop rate = 0.0% |
| **8. Brokers** | Interactive Brokers (FIX 4.4), CME DMA, Crypto WebSocket, wire latencies | Continuous heartbeat, FIX latency < 2.0ms |
| **9. Risk** | Hardware-locked RiskGatekeeper, drawdown bounds, position sizing limits | Hard drawdown limit strictly enforced (3.0%) |
| **10. Execution** | ExecutionD order routing, fill latency, realized slippage, rejection rate | Slippage < 2.0 bps, fill latency < 1.0ms |
| **11. Plugins** | Sandboxed capability modules, permissions (`market.read`, `features.emit`) | Strict sandboxing, zero broker credential access |
| **12. Agents & AEI** | AI reasoning advisory tier & Adaptive Evolution Wheel state | Advisory only, stepped 60° rotation on validation |

---

## 2. Mandatory Service Health Contract

Every registered KAIROS service exposes:
- `name`: Unique service identifier (e.g. `kairos-riskd`)
- `category`: Subsystem tier (`SYSTEM`, `DESKTOP`, `TRADING`, `RESEARCH`, `AI`, `ADAPTIVE`)
- `health`: Operational rating (`HEALTHY`, `DEGRADED`, `CRITICAL`, `HALTED`)
- `version`: Semantic version string
- `uptime`: Elapsed uptime duration
- `dependencies`: Upstream requirements and ordering
- `resource_usage`: Memory consumption (MB), CPU allocation (%), thread count
- `last_error`: Null or structured error dictionary (message, timestamp, level)

---

## 3. Log Sanitization & Secret Scrubbing Invariant

KAIROS strictly guarantees that **logs and telemetry streams never contain credentials, API secrets, private keys, or passwords**.
- The `LogSanitizer` engine enforces high-performance regex redaction:
  - Private Keys: `-----BEGIN [A-Z ]+ PRIVATE KEY-----` → `[REDACTED_PRIVATE_KEY]`
  - Generic Secrets / API Keys: `(api_key|secret|password|auth_token)=...` → `\1=[REDACTED_SECRET]`
  - Bearer HTTP Tokens: `Bearer <token>` → `Bearer [REDACTED_BEARER_TOKEN]`
  - FIX Protocol Credentials: Tag 96/554 → `[REDACTED_FIX_CREDENTIAL]`
  - High-entropy Hex Keys: 64-character hashes → `[REDACTED_HEX_KEY]`
  - Mnemonic Seed Phrases: 12-24 word strings → `[REDACTED_MNEMONIC]`

---

## 4. Log Rotation & Audit Integrity

- **Logrotate Policy (`/etc/logrotate.d/kairos`)**:
  - `/var/log/kairos/*.log`: Daily rotation, 7 backups, max size 25MB, compressed, permissions `0640 root:wheel`.
  - `/var/log/audit/*.log`: Daily rotation, 30 backups, max size 50MB, compressed, permissions `0600 root:root`.
- Protected audit records in `/var/log/audit` are immutable, append-only, and restricted from ordinary user access.

---

## 5. CLI Observability Suite

Operators and automation inspect the operating system using 5 core commands:

```bash
# 1. Comprehensive, dense operational summary across all domains
kairos status [--json]

# 2. Multi-domain health matrix across all 12 subsystems with SLAs
kairos health [--json]

# 3. Deep diagnostic latency, memory, filesystem, and invariant probes
kairos diagnostics [--json]

# 4. Secret-scrubbed service and system logs
kairos logs [--service <name>] [--lines <n>] [--json]

# 5. Chronological operational event timeline
kairos events [--limit <n>] [--json]
```
