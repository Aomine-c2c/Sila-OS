# 0001: Linux Distribution Foundation for KAIROS OS

* **Status**: Accepted
* **Date**: 2026-09-14
* **Authors**: KAIROS Distribution Engineering Team
* **Technical Area**: OS Base, Package Management & Build Pipeline

---

## Context and Problem Statement

KAIROS OS is an operating system engineered for quantitative research, algorithmic trading, and autonomous market operations. To achieve sub-millisecond scheduling latency, reproducible compilation, transactional updates, and robust packaging, we must select an initial upstream Linux distribution foundation.

The base foundation dictates:
1. Package ecosystem maturity and availability of low-latency/real-time tooling.
2. Tooling for creating deterministic, reproducible root filesystems and Live ISOs.
3. Systemd, Wayland, and modern compiler toolchain compatibility.
4. Transactional filesystem and subvolume management capabilities.
5. Upstream maintenance, security responsiveness, and containerized bootstrap feasibility.

---

## Evaluated Options

### Option 1: Debian / Ubuntu Base (`debootstrap` / Live-Build)
* **Pros**: Ubiquitous package availability, stable package base, well-understood `debootstrap` mechanics.
* **Cons**: Conservative release cadence results in aged kernels, glibc, and toolchains; backporting cutting-edge PREEMPT_RT patches and bleeding-edge Wayland/Hyprland graphics drivers is laborious. PPA sprawl degrades build reproducibility.

### Option 2: Arch Linux Base (`pacstrap` / `archiso`)
* **Pros**: Rolling release with bleeding-edge upstream kernels, seamless `PREEMPT_RT` packaging (AUR/chaotic-aur), native Wayland/Hyprland packages with zero friction.
* **Cons**: Volatile moving target makes long-term build reproducibility difficult without rigid date-stamped archive mirrors; enterprise support and production stability contracts are harder to formalize.

### Option 3: Alpine Linux Base (`apk` / `mkinitfs`)
* **Pros**: Extremely lightweight, small attack surface, musl libc.
* **Cons**: `musl` libc introduces compatibility barriers and significant performance regressions with proprietary financial exchange SDKs, vectorized NumPy/Polars wheels, and CUDA/ROCm GPU acceleration drivers.

### Option 4: Fedora / Red Hat Enterprise Linux Base (`dnf` / `lorax` / `mkosi` / Container-derived) - **CHOSEN**
* **Pros**:
  1. **Enterprise Reliability with Modern Tooling**: Balances production-grade RPM package governance and security standards (SELinux/AppArmor, crypto-policies) with modern upstream releases (Kernel 6.x, GCC 14+, Clang 18+, Python 3.12+, systemd v255+).
  2. **Superior PREEMPT_RT & Low-Latency Support**: Red Hat maintains the official upstream Linux Real-Time (`kernel-rt`) tree. Low-latency kernel patches, `tuned` real-time profiles, and socket busy-polling integration are first-class citizens.
  3. **Reproducible Containerized Bootstrapping**: Fedora base images (`registry.fedoraproject.org/fedora:40`) are reproducible and can be bootstrapped deterministically using rootless/root container engines (`podman` or `docker`) or `mkosi` without requiring special host kernel privileges.
  4. **Multi-Stage ISO Tooling**: Direct support for `lorax`, `mksquashfs`, and `xorriso` for hybrid UEFI/BIOS bootable images.

---

## Decision Outcome

Chosen option: **Fedora Linux (version 40+) as the foundational upstream distribution and build substrate**.

KAIROS will use a containerized, hermetic build environment based on Fedora 40 to bootstrap the minimal rootfs, compile the low-latency real-time kernel, deploy Hyprland/Wayland desktop profiles, install the immutable `kairos-riskd` daemon, and master the bootable Live ISO.

---

## Consequences

### Positive Consequences
* First-class upstream real-time kernel support directly aligned with Red Hat's RT initiatives.
* Modern compiler toolchain out-of-the-box (GCC 14, modern Binutils, LLVM/Clang) enabling `-march=x86-64-v3` optimized builds for financial vectorization (AVX2, FMA).
* Highly reproducible build pipeline via containerization (`podman`/`docker`), preventing host distribution contamination.
* Native systemd v255+ supporting Unified Kernel Images (UKI) and TPM2 measurement.

### Negative Consequences
* RPM dependency resolution inside minimal bootstrap containers requires caching local metadata repositories to maintain build speed.
* Fedora has a 13-month release lifecycle, requiring KAIROS to anchor to stable Fedora releases and curate internal package overlays.

---

## Compliance with KAIROS Core Invariants
- [x] **Independent OS Stability**: The underlying Fedora/systemd substrate provides rock-solid service management and hardware compatibility independent of trading daemons.
- [x] **Risk Gatekeeper Unbypassability**: Standard Linux DAC and AppArmor MAC mechanisms enforce unbypassable isolation for `kairos-riskd`.
- [x] **Reproducibility**: Containerized toolchains and pinned package sets ensure bit-for-bit reproducible builds across CI/CD and developer workstations.
