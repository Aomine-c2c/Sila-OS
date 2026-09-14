# KAIROS Quantitative Research & Backtesting Environment Architecture

## 1. Overview & Objectives

The KAIROS Quantitative Research Environment provides an institutional-grade, cryptographically audited, and isolated workbench for quantitative researchers, algorithmic traders, and machine learning models.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      KAIROS RESEARCH ENVIRONMENT                        │
├─────────────────────────────────────────────────────────────────────────┤
│  Isolated Sandboxes:                                                    │
│  [ Python Kernel ]  [ Notebook Engine ]  [ Datasets & Historical Feeds ]│
│  [ Feature Engine]  [ Backtesting Eng ]  [ Simulation / Replay Engine ] │
├─────────────────────────────────────────────────────────────────────────┤
│  Tier Separation & Security Boundaries:                                 │
│  RESEARCH: Offline Local, Read-Only Datasets, Zero Broker Credentials   │
│  PAPER:    Streaming Feed Only, Virtual Fill Engine, No Live Creds      │
│  SHADOW:   Mirrored Live Feed, Zero External Orders, Candidate Eval     │
│  LIVE:     Filtered DMA/TLS, Hardware-Locked RiskD Gatekeeper           │
├─────────────────────────────────────────────────────────────────────────┤
│  Cryptographic Manifest & Provenance Tracking (sha256):                 │
│  Dataset • Time Period • Strategy • Parameters • Features • Model       │
│  Random Seed • Tx Costs • Slippage • Metrics Results • Source Commit    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Hard Security Invariants: Tier Separation & Credential Isolation

A foundational tenet of KAIROS OS is the absolute prevention of research code or unverified models from executing unintended trades or accessing private capital.

### Execution Tiers

| Tier | Network Access | Direct Execution | Datasets Access | Broker Credentials | Isolation Mechanism |
|---|---|---|---|---|---|
| **RESEARCH** | `OFFLINE_LOCAL` | **DENIED** | `READ_ONLY` | **STRICTLY PROHIBITED** | Bubblewrap / Landlock Sandboxed Python Kernel |
| **PAPER** | `STREAMING_FEED_ONLY` | **DENIED** (Virtual Fill) | `READ_WRITE` | **DENIED** (Never Provided) | In-Memory Virtual Paper Matching Gateway |
| **SHADOW** | `STREAMING_FEED_ONLY` | **DENIED** (Mirrored Fill) | `READ_ONLY` | **DENIED** (Never Provided) | Parallel Shadow Execution Evaluator |
| **LIVE** | `FILTERED_DMA_TLS` | **AUTHORIZED** | `RESTRICTED` | **ACTIVE** (TPM2 Vault Locked) | Hardware-Locked RiskD Gatekeeper |

> [!CAUTION]
> **Hard Invariant**: Under no circumstance will `RESEARCH`, `PAPER`, or `SHADOW` tiers ever receive or inherit live broker API credentials or private keys. Broker credentials reside solely within `/etc/kairos/vault` accessible only to `brokerd` via privilege-separated IPC guarded by `riskd`.

---

## 3. Experiment Provenance Manifest (11 Mandatory Fields)

Every experiment, backtest, and walk-forward run generates an immutable JSON manifest stored in `/var/lib/kairos/research/experiments/` with a cryptographic `sha256` provenance signature.

Each manifest tracks:
1. **`dataset`**: Dataset ID and content hash (e.g. `ds_spy_5m_2024`, `sha256:...`).
2. **`time_period`**: Exact UTC start and end bounds (`start_date`, `end_date`).
3. **`strategy_version`**: Semantic version of the strategy logic (e.g. `1.4.0`).
4. **`parameters`**: Key-value hyperparameter dictionary (fast/slow windows, entry/exit thresholds).
5. **`features`**: List of engineered factors computed by the `FeatureEngine`.
6. **`model_version`**: Identifier of the model or heuristic weights (e.g. `xgb_regressor_v2`).
7. **`random_seed`**: Fixed pseudorandom seed for exact deterministic reproducibility.
8. **`transaction_costs`**: Basis points or fixed fees modeled per trade.
9. **`slippage_assumptions`**: Slippage model (linear, quadratic, or fixed basis points).
10. **`results`**: Quantitative metrics:
    - CAGR (%)
    - Sharpe Ratio
    - Sortino Ratio
    - Maximum Drawdown (%)
    - Win Rate (%)
    - Profit Factor
    - Total Trades Count
    - Annualized Volatility (%)
11. **`source_commit`**: Exact Git commit SHA or release identifier corresponding to source code.

---

## 4. Supported Validation Methodologies

KAIROS natively provides 5 distinct validation pipelines:
- **`BACKTEST`**: In-sample event-driven simulation over historical OHLCV/tick bars.
- **`WALK_FORWARD`**: Rolling-window optimization with forward anchor re-calibration.
- **`OUT_OF_SAMPLE`**: Strict holdout test on unseen market regimes.
- **`PAPER_TRADING`**: Forward-testing on simulated live tick streams without capital risk.
- **`SHADOW_DEPLOYMENT`**: Parallel production deployment matching live market books to detect fill deviations and slippage drift before live capital allocation.

---

## 5. CLI & SysD IPC Commands

The system management CLI (`kairos`) and system daemon (`kairos_sysd.py`) expose typed, auditable commands:

```bash
# Check status and tier isolation rules
kairos research status

# List institutional datasets available in the research partition
kairos research datasets

# Execute an experiment with full manifest recording
kairos research run --strategy EMA_Cross --dataset ds_spy_5m_2024 --validation BACKTEST

# Audit credential isolation guarantees
kairos research credentials-check

# List logged historical experiments
kairos research experiments
```
