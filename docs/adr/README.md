# Architecture Decision Records (ADRs)

Architecture Decision Records capture significant technical and design choices made during the development of KAIROS OS.

## ◈ Index of Architecture Decision Records

| ADR | Title | Status | Date |
|---|---|---|---|
| [ADR-0001](ADR-0001-record-architecture-decisions.md) | Record Architecture Decisions | Accepted | 2026-09-14 |
| [ADR-0002](ADR-0002-independent-os-stability.md) | Independent OS Stability Invariant | Accepted | 2026-09-14 |
| [ADR-0003](ADR-0003-unbypassable-risk-pipeline.md) | Unbypassable Trading Risk Gatekeeper Pipeline | Accepted | 2026-09-14 |
| [ADR-0004](ADR-0004-linux-base-rt-kernel-btrfs.md) | Linux Base, PREEMPT_RT Kernel & Btrfs Layout | Accepted | 2026-09-14 |
| [ADR-0005](ADR-0005-hyprland-wayland-compositor.md) | Hyprland Wayland Compositor Selection | Accepted | 2026-09-14 |

---

## ◈ Creating a New ADR

To propose a new architecture decision:
1. Copy [template.md](template.md) to `ADR-XXXX-<title-in-kebab-case>.md`.
2. Document context, decision, consequences, and compliance with KAIROS core invariants.
3. Submit for architectural review.
