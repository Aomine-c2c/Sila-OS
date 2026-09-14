# ADR-0002: Independent OS Stability Invariant

* **Status**: Accepted
* **Date**: 2026-09-14
* **Authors**: KAIROS Architecture Team
* **Technical Area**: System Architecture & Service Management

---

## Context and Problem Statement
KAIROS OS incorporates specialized trading infrastructure, high-throughput market data caches, sandboxed plugins, local AI reasoning agents, and adaptive evolution feedback loops. If any of these specialized application components crashes or misbehaves, the underlying operating system must remain rock-solid, fully responsive, and securely manageable.

## Decision Outcome
Chosen option: **Enforce strict separation between OS foundational services and domain-specific trading/AI subsystems.**
- The base OS boots into a fully functional environment without starting any trading services.
- Trading, AI, and research components run as unprivileged systemd user services or sandboxed system units.
- Failure of `kairos-riskd` or trading algorithms triggers safe shutdown of order pipes without crashing kernel, display, or management interfaces.

### Consequences
* **Positive Consequences**:
  - System recovery and remote management remain operable during trading errors.
  - Clear fault boundaries for debugging and auditing.
* **Negative Consequences**:
  - Requires clean IPC interfaces (UNIX domain sockets) rather than monolithic in-kernel or deep system hooks.
