# ADR-XXXX: [Short title of solved problem and decision]

* **Status**: [Proposed | Accepted | Rejected | Deprecated | Superseded by ADR-XXXX]
* **Date**: YYYY-MM-DD
* **Authors**: [Name/Team]
* **Technical Area**: [Kernel | Security | Desktop | Trading | Storage | Networking]

---

## Context and Problem Statement
[Describe the context and problem being addressed. Include technical constraints, performance requirements, or system invariants.]

## Considered Options
1. [Option 1]
2. [Option 2]
3. [Option 3]

## Decision Outcome
Chosen option: "[Option X]", because [justification explaining why this choice best fits KAIROS requirements, low latency, stability, and security invariants].

### Consequences
* **Positive Consequences**:
  - [Benefit 1]
  - [Benefit 2]
* **Negative Consequences**:
  - [Trade-off 1]
  - [Trade-off 2]

## Compliance with KAIROS Core Invariants
- [ ] **Independent OS Stability**: Does the OS remain stable if this feature is disabled?
- [ ] **Risk Gatekeeper Unbypassability**: Does this touch the financial pipeline? If yes, is Risk respected?
- [ ] **Security Boundaries**: Are privileges strictly bounded?
