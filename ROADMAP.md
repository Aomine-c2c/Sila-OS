# KAIROS OS Engineering Roadmap

This roadmap details the progressive stages of KAIROS OS development, tracing from foundational architecture to production releases.

---

## ◈ Milestones Overview

```
[Phase 0: Foundation] ──► [Phase 1: Core Substrate] ──► [Phase 2: Desktop & Workstation] ──► [Phase 3: Trading & Quant] ──► [Phase 4: Release & Live ISO]
      (CURRENT)
```

---

## ◈ Milestone 0: Engineering Foundation & Monorepo Scaffold (v0.1.0-alpha.1) - [IN PROGRESS / COMPLETE]
- [x] Establish standardized repository layout (`/boot`, `/build`, `/config`, `/docs`, `/kernel`, `/iso`, `/system`, `/services`, etc.)
- [x] Create project manifest (`kairos.toml`) and versioning schema
- [x] Establish Architecture Decision Records (`docs/adr/`)
- [x] Author core documentation (`README.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CONTRIBUTING.md`, `SECURITY.md`, `LICENSE`, `CHANGELOG.md`)
- [x] Provide operational tooling scripts:
  - `scripts/env_detect.sh`
  - `scripts/check_deps.sh`
  - `scripts/build.sh`
  - `scripts/test.sh`
  - `scripts/clean.sh`
  - `scripts/package.sh`
  - `scripts/iso_generate.sh`
  - `scripts/vm_boot.sh`
  - `scripts/hardware_validate.sh`
- [x] Automated architecture and invariant validation tests in `tests/`

---

## ◈ Milestone 1: Linux Substrate & Real-Time Kernel (v0.2.0-alpha)
- [ ] Build hermetic build container using podman/docker
- [ ] Bootstrap reproducible minimal rootfs via debootstrap / dnf / pacman bootstrap
- [ ] Compile Linux 6.6+ kernel with `PREEMPT_RT` patchset enabled
- [ ] Generate Unified Kernel Images (UKI) with embedded initramfs
- [ ] Implement systemd-boot & GRUB2 secure boot signing infrastructure
- [ ] Validate transactional Btrfs subvolume layout with snapshot automounts

---

## ◈ Milestone 2: Hardened Display & Operator Desktop (v0.3.0-alpha)
- [ ] Deploy wlroots & Hyprland compositor with deterministic window placement rules
- [ ] Integrate KAIROS Shell (Waybar) with real-time financial ticker and latency ribbon
- [ ] Configure zero-latency GPU-accelerated terminal (Kitty) with hardware cursor bypass
- [ ] Implement Mako notification daemon with high-priority risk violation overrides
- [ ] Package `kairos-control` TUI/CLI for system tuning and performance profiles

---

## ◈ Milestone 3: Trading Infrastructure & Research Workspace (v0.4.0-alpha)
- [ ] Harden `kairos-riskd` daemon with AppArmor containment and UNIX socket IPC
- [ ] Enforce the unbypassable pipeline: `Signal -> Decision -> Risk -> Execution -> Broker`
- [ ] Deploy DuckDB / Polars tick data cache with Zstandard compression
- [ ] Provision capability-sandboxed plugin architecture (WASM runtime integration)
- [ ] Implement local AI reasoning agent harness with read-only market state access

---

## ◈ Milestone 4: Adaptive Intelligence & Self-Healing (v0.5.0-beta)
- [ ] Implement Adaptive Evolution Intelligence (AEI) telemetry collectors
- [ ] Validate dynamic socket buffer tuning (`net.core.busy_poll`) under heavy burst loads
- [ ] Guarantee safety invariants: AEI cannot weaken security or modify risk rules
- [ ] Finalize `kairos-update` transactional A/B update system with boot rollback guards

---

## ◈ Milestone 5: System Installer & Production Release (v1.0.0-GA)
- [ ] Calamares and CLI automated installer (`kairos-install`) with NVMe optimization
- [ ] Master reproducible hybrid UEFI/BIOS bootable Live ISO
- [ ] Automated end-to-end VM boot and execution tests via QEMU
- [ ] Cryptographic release signing, SHA256 checksums, and Software Bill of Materials (SBOM)
