# Contributing to KAIROS OS

Thank you for your interest in contributing to **KAIROS OS**. KAIROS is an operating system engineered for mission-critical financial systems, quantitative research, and algorithmic execution. Because stability and security are paramount, all contributions must adhere to strict engineering invariants.

---

## ◈ Core Engineering Invariants

Before submitting any code, verify that your changes uphold these invariants:

1. **Independent OS Stability**: The operating system must remain fully bootable, manageable, and stable even if all trading, research, AI, and adaptive modules are disabled.
2. **The Unbypassable Risk Pipeline**:
   $$\text{Signal} \longrightarrow \text{Decision} \longrightarrow \mathbf{Risk} \longrightarrow \text{Execution} \longrightarrow \text{Broker}$$
   Under no circumstance may an AI agent, plugin, or strategy bypass or weaken the `RiskGatekeeper`.
3. **No Faking Functionality**: Do not introduce mock implementations or placeholders in place of real system components.
4. **Reproducibility**: Build artifacts, kernel configs, and packages must be deterministic and verifiable.

---

## ◈ Development Workflow

1. **Autonomous Development Loop**:
   $$\text{INSPECT} \longrightarrow \text{UNDERSTAND} \longrightarrow \text{PLAN} \longrightarrow \text{IMPLEMENT} \longrightarrow \text{BUILD} \longrightarrow \text{TEST} \longrightarrow \text{HARDEN} \longrightarrow \text{DOCUMENT}$$
2. **Branching Strategy**:
   - `main`: Protected, always releasable and buildable.
   - `feature/<name>`: Focused development branches.
   - `fix/<issue>`: Bug fixes and security patches.
3. **Code Quality**:
   - Python: Follow PEP 8 and write unit tests for all non-trivial logic in `tests/`.
   - Shell: Use `bash` with `set -euo pipefail`. Validate scripts with shellcheck when available.
   - Configuration files: Use strict TOML, INI, or JSON format.

---

## ◈ Architecture Decision Records (ADRs)

If your contribution introduces an architectural change (e.g. changing the init system, adding a kernel patch, modifying IPC protocols, altering the desktop compositor, or modifying risk parameters):
- You **must** create an ADR in `docs/adr/`.
- Follow the template in `docs/adr/template.md`.

---

## ◈ Running Verification

Before submitting a Pull Request, run the local verification suite:
```bash
./scripts/check_deps.sh
./scripts/test.sh
```
All automated tests must pass.
