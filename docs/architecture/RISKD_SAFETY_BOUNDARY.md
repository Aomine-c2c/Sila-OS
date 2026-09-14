# KAIROS RiskD — Central Safety Boundary & Pre-Trade Risk Engine

## 1. Safety Architecture Overview

`RiskD` is the central safety boundary and hardware-enforced pre-trade risk engine of KAIROS. In accordance with institutional trading invariants, unrestricted or direct execution is strictly prohibited. Every order must follow a non-bypassable sequence:

$$\text{Signal} \longrightarrow \text{DecisionSnapshot} \longrightarrow \mathbf{RiskD} \longrightarrow \text{Execution Validation} \longrightarrow \text{ExecutionD} \longrightarrow \text{BrokerD}$$

```
    ┌─────────────────────────┐
    │  Strategy / AI / Plugin │
    │      (Emits Signal)     │
    └────────────┬────────────┘
                 │
                 ▼
    ┌─────────────────────────┐
    │    DecisionSnapshot     │
    │  (Typed Order Intent)   │
    └────────────┬────────────┘
                 │
                 ▼
    ┌────────────────────────────────────────────────────────┐
    │                         RiskD                          │
    │            (Central Pre-Trade Safety Gate)             │
    │                                                        │
    │  - Max Positions       - Exposure (Gross/Net)          │
    │  - Position Sizing     - Daily Loss & Drawdown Breaker │
    │  - Symbol Limits       - Correlation Group Caps        │
    │  - Spread Limits       - Stale-Data Rejection          │
    │  - Duplicate Filter    - Broker Latency SLA            │
    │  - Emergency Halt      - Close-Only Enforcement        │
    └────────────┬───────────────────────────┬───────────────┘
                 │                           │
            [APPROVED]                  [REJECTED]
                 │                           │
                 ▼                           ▼
    ┌─────────────────────────┐ ┌────────────────────────────┐
    │       ExecutionD        │ │          JournalD          │
    │ (Validation & Slicing)  │ │ (Logged & Execution Halts) │
    └────────────┬────────────┘ └────────────────────────────┘
                 │
                 ▼
    ┌─────────────────────────┐
    │         BrokerD         │
    │ (FIX 4.4 / DMA Gateway) │
    └─────────────────────────┘
```

---

## 2. Risk Operational States

RiskD operates across 5 discrete risk states with dynamic transitions based on portfolio drawdown, margin utilization, and operational status:

| State | Definition | Operating Parameters |
|---|---|---|
| **`SAFE`** | Optimal State | Full trading enabled; portfolio drawdown $< 0.4 \times \text{limit}$, low exposure. |
| **`NORMAL`** | Standard Operations | Active trading within nominal sizing and exposure bounds. |
| **`CAUTION`** | Elevated Risk | Drawdown $\ge 40\%$ of limit or position count $\ge 80\%$ of cap; warning status flagged to Waybar/shell. |
| **`RESTRICTED`** | Near Capacity / Close-Only | Drawdown $\ge 70\%$ of limit or Close-Only mode active. Sizing clamped, new positions throttled. |
| **`HALTED`** | Emergency Halt / Circuit Breaker | Limit breached (loss, drawdown) or manual operator halt. Zero new risk allowed. |

---

## 3. Enforced Safety Rules & Hard Invariants

1. **Maximum Positions**: Limits total open positions across the entire portfolio (default: 10).
2. **Exposure Limits**: Gross ($250,000) and net ($150,000) notional caps enforced pre-trade.
3. **Position Sizing Limits**: Max quantity (100 units) and max order value ($50,000) hard capped.
4. **Daily Loss Circuit Breaker**: Exceeding daily loss ($5,000) or maximum drawdown (3.0%) instantly transitions RiskD to `HALTED`.
5. **Symbol Limits**: Per-symbol exposure cap ($75,000) and blacklisted/restricted asset enforcement.
6. **Correlation Limits**: Concentrated exposure across asset clusters (Crypto, Equity Indices, Semis) cannot exceed group caps ($120,000).
7. **Spread Limits**: Market ticks with bid-ask spreads $> 1.50\%$ are rejected to prevent toxic slippage.
8. **Stale-Data Protection**: Rejects orders evaluated on market data ticks older than 3.0 seconds.
9. **Duplicate-Order Protection**: Idempotency hashing prevents identical orders within a 1.0-second window.
10. **Broker-Health Checks**: Orders rejected if broker gateway disconnects or latency exceeds 500 ms SLA.
11. **Order Validation**: Validates positive non-zero quantity, limit price validity, and side.
12. **Emergency Halt**: Instant, manual or automated trade suspension.
13. **Close-Only Mode**: Only allows orders that strictly reduce existing exposure (`SELL` for long, `BUY` for short).
14. **Strategy Pause**: Individual strategies can be paused without halting the overall trading engine.
15. **Autonomous Mutation Defense**: **AI agents, plugins, and the Adaptive Evolution Intelligence (AEI) cannot bypass or autonomously modify hard risk limits.**

---

## 4. CLI Control & Telemetry (`kairos risk`)

```bash
# 1. View overall RiskD safety state, broker health, and enforced hard limits
kairos risk status

# 2. Trigger an immediate emergency halt
kairos risk halt --reason "Extreme macro volatility event"

# 3. Release emergency halt
kairos risk resume

# 4. Activate Close-Only mode
kairos risk close-only on

# 5. Pause a specific rogue or degrading strategy
kairos risk pause strat-momentum-spy

# 6. Resume strategy
kairos risk unpause strat-momentum-spy
```

All commands support `--json` for programmatic integration.
