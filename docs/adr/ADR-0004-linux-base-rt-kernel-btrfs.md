# ADR-0004: Linux Base, PREEMPT_RT Kernel & Btrfs Subvolume Hierarchy

* **Status**: Accepted
* **Date**: 2026-09-14
* **Authors**: KAIROS Architecture Team
* **Technical Area**: Kernel & Storage Architecture

---

## Context and Problem Statement
Quantitative trading workstations require deterministic response times for network packet processing and user interactions, while also needing robust transactional filesystem updates and atomic rollback capabilities to prevent system bricking during rapid updates.

## Decision Outcome
1. **Kernel**: Use Linux with the `PREEMPT_RT` patchset, full tickless mode (`CONFIG_NO_HZ_FULL=y`), high-resolution timers (`CONFIG_HZ_1000=y`), and socket busy-polling enabled.
2. **Filesystem**: Standardize on **Btrfs** transactional subvolumes:
   - `@`: Root OS tree (mounted read-only during regular execution)
   - `@home`: User directories and quantitative research notebooks
   - `@snapshots`: Instantaneous atomic recovery points
   - `@var_log`: Persistent system logs and telemetry
   - `@vault`: TPM2-encrypted credential and API key storage
3. **Memory Management**: In-RAM compressed swap using `zram-generator` (zstd) to prevent disk paging latency jitter.

### Consequences
* **Positive Consequences**:
  - Sub-millisecond scheduling latency.
  - Fail-safe atomic updates: rollback is a simple bootloader stanza change.
* **Negative Consequences**:
  - Requires Btrfs-aware tooling during OS installation.
