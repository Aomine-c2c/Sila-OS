# ADR-0003: Unbypassable Trading Risk Gatekeeper Pipeline

* **Status**: Accepted
* **Date**: 2026-09-14
* **Authors**: KAIROS Architecture Team
* **Technical Area**: Trading Architecture & Security Isolation

---

## Context and Problem Statement
Autonomous execution systems, machine learning agents, and quantitative strategies operating on market data can produce catastrophic errors (e.g. runaway order loops, erroneous position scaling, fat-finger pricing, algorithmic hallucinations). The operating system must guarantee that NO order reaches a broker or execution gateway without explicit verification by an isolated risk gatekeeper.

## Decision Outcome
Chosen option: **Enforce the strict unbypassable pipeline**:
$$\text{Signal} \longrightarrow \text{Decision} \longrightarrow \mathbf{Risk} \longrightarrow \text{Execution} \longrightarrow \text{Broker}$$

- The execution daemon (`ExecutionEngine`) only accepts order payloads cryptographically or IPC-signed by `kairos-riskd`.
- Neither AI agents nor third-party plugins have access to network sockets connected to brokers.
- Risk parameters (max position size, drawdown limits, price deviation bounds) are locked at startup and cannot be relaxed at runtime by AI or user-space scripts without authenticated operator intervention.

### Consequences
* **Positive Consequences**:
  - Eliminates rogue strategy and runaway algorithm risks.
  - Provable financial safety guarantees.
* **Negative Consequences**:
  - Adds a small microsecond-level IPC hop for risk evaluation (mitigated by UNIX domain sockets and shared memory buffers).
