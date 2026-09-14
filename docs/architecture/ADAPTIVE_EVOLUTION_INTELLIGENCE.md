# Adaptive Evolution Intelligence (AEI)

Adaptive Evolution Intelligence (AEI) is the long-term, self-governing adaptive intelligence engine of the KAIROS Operating System. It provides controlled, verifiable, and reversible evolution of system, strategy, and execution parameters over time.

---

## Core Axioms

1. **"No autonomous self-modification without validation."**
   No change is ever applied directly to production without passing automated statistical, walk-forward, and simulated stress testing.
2. **"Rollback is memory."**
   Every reverted adaptation is indexed into episodic memory with root cause diagnoses and performance telemetry so the system never repeats past errors.
3. **"A failed adaptation becomes knowledge."**
   Negative hypothesis tests are preserved permanently to refine generation boundaries and bayesian priors.

---

## The 11-Stage Adaptation Loop

```
  [ OBSERVE ] ──> Telemetry sampling (execution, market, strategy, risk)
       │
  [ DIAGNOSE ] ──> Anomaly, drift, and degradation detection
       │
   [ MEASURE ] ──> Quantify regret, information ratio, decay, and novelty
       │
  [ GENERATE ] ──> Synthesize candidate mutation within permitted bounds
       │
    [ TEST ] ──> Simulation, replay, and walk-forward verification
       │
  [ VALIDATE ] ──> Hard security gate check & score threshold evaluation
       │
   [ SHADOW ] ──> Real-time parallel shadow execution against live feeds
       │
   [ DEPLOY ] ──> Atomic production state update & baseline snapshot
       │
   [ MONITOR ] ──> Post-deployment telemetry & drift surveillance
       │
 [ ACCEPT / ROLLBACK ] ──> Verify performance criteria or revert atomically
       │
  [ MEMORIZE ] ──> Index candidate, outcome, and telemetry into knowledge base
```

### Loop Stage Definitions

1. **OBSERVE**: Continuously ingests streaming telemetry from `marketd`, `strategyd`, `riskd`, and `executiond`.
2. **DIAGNOSE**: Identifies regime shifts, deterioration anomalies, or drift flags across active strategies and models.
3. **MEASURE**: Computes quantitative impact metrics: Sharpe/Sortino decay, execution slippage, latency degradation, regret scores, and statistical drift (KS / PSI / Wasserstein).
4. **GENERATE**: Creates candidate parameter vectors targeting permitted subsystems using Bayesian optimization, evolutionary strategies, or heuristic search.
5. **TEST**: Runs the candidate against replay datasets, synthetic stress scenarios, and out-of-sample regimes.
6. **VALIDATE**: Assesses candidate performance against baseline metrics (fitness score, drawdown constraints) and applies the **Hard Security Gate**.
7. **SHADOW**: Executes candidate alongside active baseline in a read-only shadow deployment to observe behavior on live ticks without risking capital.
8. **DEPLOY**: Atomically applies validated candidate parameters to target subsystems while recording full rollback states.
9. **MONITOR**: Tracks live post-deployment performance against SLA expectations.
10. **ACCEPT / ROLLBACK**:
    - **Accept**: If performance metrics meet or exceed criteria, the candidate becomes the new `BASELINE`.
    - **Rollback**: If degradation or risk thresholds are breached, the system atomically restores `rollback_state` and marks candidate as `ROLLED_BACK`.
11. **MEMORIZE**: Persists the adaptation record, reasons, telemetry, and outcome into `aei_knowledge.jsonl` to enrich long-term system memory.

---

## Monitored Signals

AEI continuously tracks eight core operational signals:

| Signal | Description | Detection Mechanism |
|---|---|---|
| `performance_deterioration` | Strategy return decay, win-rate erosion, Sharpe decay | Rolling metrics vs. benchmark thresholds |
| `market_regime_changes` | Volatility shift, trend-to-mean-reversion transition | GARCH, Markov switching, HMM classifiers |
| `drift` | Feature or concept drift between training and inference | Population Stability Index (PSI), KS test |
| `regret` | Opportunity cost of counterfactual decisions | Regret minimization matching vs. optimal choices |
| `novelty` | Unprecedented order book dynamics or market events | Isolation forests, autoencoder reconstruction error |
| `uncertainty` | Epistemic/aleatoric uncertainty in model predictions | Ensemble variance, MC dropout distributions |
| `execution_degradation` | Slippage increase, rejection rate rise, latency spikes | Execution telemetry vs. broker SLA models |
| `fitness_deterioration` | Compound deterioration of multi-objective fitness | Pareto frontier rank collapse |

---

## Parameter Mutation Boundaries

### Permitted Targets

AEI is strictly constrained to proposing and applying mutations to the following 8 areas:

1. **Indicator Parameters** (e.g., lookback windows, smoothing alphas, exponential moving average spans)
2. **Strategy Thresholds** (e.g., entry/exit z-scores, RSI triggers, breakout bands)
3. **Strategy Weights** (e.g., ensemble allocation weights, multi-strategy portfolio capital weights)
4. **Strategy Routing** (e.g., matching strategies to detected regimes)
5. **Feature Selection** (e.g., dynamic feature mask activation/deactivation)
6. **Confidence Thresholds** (e.g., model signal minimum confidence filter)
7. **Execution Timing** (e.g., order slicing schedules, TWAP/VWAP interval pacing)
8. **Position-Size Multipliers** (e.g., fractional Kelly multipliers, volatility scalar within risk limits)

### Hard Security Invariants (PROHIBITED Targets)

AEI **MUST NOT** modify, bypass, or propose changes to:

- ❌ **Risk Hard Limits** (Max position sizes, global drawdown halts, max leverage)
- ❌ **Credentials** (API keys, secrets, private signing keys, TPM tokens)
- ❌ **Permissions** (RBAC, sudoers, IPC capabilities, daemon authorization tokens)
- ❌ **Security Policies** (AppArmor profiles, nftables rules, seccomp filters)
- ❌ **Audit Integrity** (Audit log chains, JournalD records, telemetry logs)
- ❌ **Kill Switch** (Emergency manual or automated trading shutdown triggers)
- ❌ **Core Execution Safety** (Pre-trade checks, double-order deduplication, stale data checks)

Any proposal targeting a prohibited target is rejected immediately by the `AEISecurityGate` with a security audit event logged.

---

## Adaptation Schema

Every adaptation event must contain all nine mandatory fields:

```json
{
  "adaptation_id": "adapt-5b4d7c81a93e",
  "reason": "Execution degradation: Fill slippage exceeded 4.2 bps",
  "baseline": {
    "execution_timing": { "slice_interval_ms": 500, "aggressiveness": 0.8 }
  },
  "candidate": {
    "execution_timing": { "slice_interval_ms": 850, "aggressiveness": 0.5 }
  },
  "evidence": {
    "signal": "execution_degradation",
    "recent_slippage_bps": 4.8,
    "target_slippage_bps": 2.5
  },
  "validation_result": {
    "passed": true,
    "score": 0.884,
    "simulation_runs": 1000,
    "max_drawdown_delta": -0.002
  },
  "deployment_scope": "strategy:kairos.twap_execution",
  "performance": {
    "post_deploy_slippage_bps": 2.1,
    "improvement_pct": 56.25
  },
  "rollback_state": {
    "slice_interval_ms": 500,
    "aggressiveness": 0.8
  }
}
```

---

## Candidate Lifecycle

```
             ┌───────────┐
             │ BASELINE  │
             └─────┬─────┘
                   │ Candidate generation
                   ▼
             ┌───────────┐
             │ CANDIDATE │
             └─────┬─────┘
                   │ Test & Security Gate Validation
                   ▼
             ┌───────────┐
             │ VALIDATED │
             └─────┬─────┘
                   │ Non-intrusive feed shadowing
                   ▼
             ┌───────────┐
             │  SHADOW   │
             └─────┬─────┘
                   │ Live deployment
                   ▼
             ┌───────────┐
      ┌─────>│ DEPLOYED  │
      │      └─────┬─────┘
      │            │ Performance check
      │      ┌─────┴──────────┐
Accept│      │ Criteria met?  │
      │      └─────┬──────────┘
      │            │
      │      Yes ┌─┴─┐ No (or degradation)
      └──────────┤   ├──────────────┐
                 └───┘              ▼
                             ┌─────────────┐
                             │ ROLLED_BACK │
                             └─────────────┘
```

---

## CLI Integration

Administrators and automated controllers interact with AEI via the unified `kairos adaptive` command suite:

```bash
# Display operational state, active adaptations, and memory stats
kairos adaptive status

# Trigger an 11-stage adaptation cycle
kairos adaptive cycle --signal performance_deterioration --target strategy_weights

# View history of applied adaptations
kairos adaptive history

# Inspect episodic memory and rollback lessons
kairos adaptive memory

# Manually trigger an atomic rollback
kairos adaptive rollback <adaptation_id>

# Run security gate invariant validation
kairos adaptive verify-security
```

---

## Security Invariant Guarantee

The `AEISecurityGate` operates at both the code and daemon IPC layer:
1. Static and dynamic checks block any mutation containing prohibited keywords or targets.
2. The `kairos_sysd` IPC boundary enforces `adaptive.trigger_cycle` and `adaptive.rollback` permissions.
3. AppArmor confinement denies arbitrary disk modification or network access to the adaptive engine.
4. Risk hard limits are stored in immutable kernel-restricted or root-only configuration paths unreachable by AEI workers.
