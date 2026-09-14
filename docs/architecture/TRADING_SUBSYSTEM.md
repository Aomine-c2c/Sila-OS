# KAIROS Trading Subsystem Architecture

## 1. Architectural Philosophy

The KAIROS Trading Subsystem is built as a **hardened, headless service layer** that operates entirely independent of the Wayland compositor, Hyprland window manager, or desktop shell.

### Core Design Principles
1. **Compositor Decoupling**: A crash in Hyprland, Waybar, or an untrusted user interface component has zero impact on active trading feeds, risk gates, strategy evaluation, or broker connections.
2. **Deterministic Unidirectional Pipeline**:
   $$\text{Market Data (MarketD)} \longrightarrow \text{StrategyD} \longrightarrow \text{Decision Snapshot} \longrightarrow \text{RiskD} \longrightarrow \text{ExecutionD} \longrightarrow \text{BrokerD} \longrightarrow \text{JournalD}$$
3. **Non-Bypassable Risk Enforcement**: All trading intentions are converted into immutable typed `DecisionSnapshot` objects. `ExecutionD` strictly requires positive validation from `RiskD` before any order payload is dispatched to `BrokerD`.
4. **Immutable Audit Trail**: Every state transition—strategy order proposals, pre-trade risk evaluations, broker fills, or risk rejections—is synchronously journaled via `JournalD` to an append-only verifiable ledger (`/var/log/kairos/trading_journal.log`).

---

## 2. Daemon & Service Architecture

```
                                  ┌───────────────────────────┐
                                  │   Raw Exchange / Venues   │
                                  │   (CME, NASDAQ, IBKR FIX) │
                                  └─────────────┬─────────────┘
                                                │
                                                ▼
                                  ┌───────────────────────────┐
                                  │          MarketD          │
                                  │  (Normalized Tick Engine) │
                                  └─────────────┬─────────────┘
                                                │
                                                ▼
                                  ┌───────────────────────────┐
                                  │         StrategyD         │
                                  │ (Multi-Mode Engine & Reg) │
                                  └─────────────┬─────────────┘
                                                │
                                                ▼
                                    [ Decision Snapshot ]
                                                │
                                                ▼
                                  ┌───────────────────────────┐
                                  │           RiskD           │
                                  │ (Hardware Risk Gatekeeper)│
                                  └─────────────┬─────────────┘
                                                │
                       ┌────────────────────────┴────────────────────────┐
                       │                                                 │
                  [APPROVED]                                         [REJECTED]
                       ▼                                                 ▼
        ┌─────────────────────────────┐                    ┌───────────────────────────┐
        │         ExecutionD          │                    │         JournalD          │
        │  (Routing & Order Slicing)  │                    │ (Append-Only Audit Trail) │
        └──────────────┬──────────────┘                    └───────────────────────────┘
                       │                                                 ▲
                       ▼                                                 │
        ┌─────────────────────────────┐                                  │
        │           BrokerD           │                                  │
        │ (Normalized FIX / DMA GW)   ├──────────────────────────────────┘
        └──────────────┬──────────────┘       (Fill / Execution Report)
                       │
                       ▼
        ┌─────────────────────────────┐
        │  Institutional Execution    │
        │      (FIX 4.4 / DMA)        │
        └─────────────────────────────┘
```

---

## 3. Subsystem Component Specifications

### 3.1 MarketD (`trading.subsystem.MarketD`)
Ingests heterogeneous market feeds (multicast ITCH, direct FIX market data, binary websocket) and normalizes every market tick into a strict 11-field data structure:

```python
@dataclasses.dataclass
class NormalizedMarketTick:
    symbol: str               # e.g., 'SPY', 'BTC/USD'
    bid: float                # Top of book best bid
    ask: float                # Top of book best ask
    mid: float                # (bid + ask) / 2.0
    spread: float             # ask - bid
    volume: float             # Aggregate volume or last trade size
    timestamp: float          # Epoch float timestamp (seconds)
    provider: str             # e.g., 'CME_DMA', 'NASDAQ_ITCH'
    sequence: int             # Monotonically increasing sequence number
    quality: str              # 'PRISTINE', 'FILTERED', 'DEGRADED'
    latency: float            # Ingest-to-normalize latency (microseconds)
```

### 3.2 StrategyD (`trading.subsystem.StrategyD`)
Manages the lifecycle, registration, and evaluation of quantitative strategies:
- **Registration & Versioning**: Strategies are tagged with semantic versioning (`1.4.0`), unique IDs, and metadata.
- **Dynamic Parameters**: Allows runtime adjustment of mathematical parameters (thresholds, stop losses, window sizes) with audit tracking.
- **Enable / Disable Toggle**: Strategies can be safely enabled or disabled at runtime.
- **Execution Modes**:
  - `SIMULATION`: Backtest and historical replay evaluation.
  - `PAPER`: Live market data feeds with simulated broker fills.
  - `LIVE`: Live market data feeds with direct real-capital routing.

### 3.3 RiskD (`trading.subsystem.RiskD`)
The pre-trade gatekeeper. It enforces hard invariants regardless of caller privileges:
- **Drawdown Circuit Breaker**: Halts order routing when portfolio or intraday drawdown exceeds configured thresholds (e.g. 3.0%).
- **Maximum Order / Position Ceilings**: Prevents rogue strategies or algorithmic fat-finger spikes from exceeding defined notional sizes.
- **Limit Price Sanity**: Ensures all limit orders contain strictly positive, non-zero values.
- **Hardware Kill Switch**: Instant global trade revocation.

### 3.4 ExecutionD (`trading.subsystem.ExecutionD`)
Coordinates the pipeline:
1. Receives typed `DecisionSnapshot` from `StrategyD`.
2. Evaluates order against `RiskD`.
3. If approved, hands execution to `BrokerD` with risk-adjusted quantities.
4. If rejected, records `RISK_REJECTED` in `JournalD` and halts the trade.

### 3.5 BrokerD (`trading.subsystem.BrokerD`)
Abstracts multi-venue execution endpoints (Interactive Brokers FIX 4.4, CME DMA, Crypto Institutional Gateways). Returns normalized `BrokerExecutionReport` records:
- `execution_id`
- `order_id`
- `broker_name`
- `symbol`
- `side`
- `filled_quantity`
- `fill_price`
- `status` (`FILLED`, `PARTIALLY_FILLED`, `REJECTED`)
- `timestamp`

### 3.6 JournalD (`trading.subsystem.JournalD`)
Maintains an append-only JSONL event journal (`/var/log/kairos/trading_journal.log`). Events logged include:
- `STRATEGY_REGISTERED`
- `STRATEGY_TOGGLED`
- `STRATEGY_MODE_CHANGED`
- `STRATEGY_PARAMS_UPDATED`
- `RISK_EVALUATION`
- `BROKER_EXECUTION`

---

## 4. CLI Control Interface

The KAIROS system tool (`kairos`) exposes high-level trading controls:

| Command | Action | Description |
|---|---|---|
| `kairos trade status` | Inspection | Telemetry of MarketD, StrategyD, RiskD, ExecutionD, BrokerD, and JournalD |
| `kairos trade tick [symbol]` | Ingestion Probe | Displays normalized tick with all 11 standardized attributes |
| `kairos trade strategies` | Strategy Inventory | Lists registered strategies, versions, current mode, and parameters |
| `kairos trade strategy <id> toggle <enable\|disable>` | Strategy Control | Enables or disables an active strategy |
| `kairos trade strategy <id> mode <SIMULATION\|PAPER\|LIVE>` | Strategy Mode | Transitions strategy between SIMULATION, PAPER, and LIVE |
| `kairos trade journal [-n N]` | Audit Query | Reads recent structured execution and decision journal records |

All commands support `--json` for machine-readable piping.

---

## 5. Security & Isolation Matrix

| Subsystem Component | Process Privilege | Network Access | Compositor Dependency |
|---|---|---|---|
| `kairos-feedd` (`MarketD`) | `kairos-trader` | Inbound Multicast / WebSockets | **NONE (Headless)** |
| `kairos-strategyd` (`StrategyD`) | `kairos-trader` | Loopback IPC only | **NONE (Headless)** |
| `kairos-riskd` (`RiskD`) | `kairos-risk` (Locked) | Denied (No external net) | **NONE (Headless)** |
| `kairos-brokerd` (`BrokerD`) | `kairos-broker` | Outbound TLS / FIX only | **NONE (Headless)** |
| `JournalD` | `root` / `syslog` | Local append-only disk | **NONE (Headless)** |
| Desktop Shell / Hyprland | `trader` | Local Wayland display | Decoupled client only |
