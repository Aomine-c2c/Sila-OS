# Changelog

All notable changes to the **KAIROS OS** project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0-alpha.1] - 2026-09-14

### Added
- **Monorepo Structure**: Established complete 24-folder standard operating system layout:
  `/boot`, `/build`, `/config`, `/docs`, `/kernel`, `/iso`, `/packages`, `/system`, `/services`, `/desktop`, `/shell`, `/apps`, `/plugins`, `/trading`, `/research`, `/agents`, `/adaptive`, `/security`, `/scripts`, `/tests`, `/tools`, `/recovery`, `/installer`, `/assets`.
- **Project Manifest**: Machine-readable `kairos.toml` defining system metadata, architecture specifications, build targets, and invariant toggles.
- **Architecture Documentation**: Comprehensive `ARCHITECTURE.md` specifying system invariants, defense-in-depth security model, and low-latency pipeline topology.
- **Architecture Decision Record (ADR) System**: Initialized `docs/adr/` with template and foundational ADRs:
  - `ADR-0001`: Record Architecture Decisions
  - `ADR-0002`: Independent OS Stability Invariant
  - `ADR-0003`: Unbypassable Trading Risk Gatekeeper Pipeline
  - `ADR-0004`: Linux Base, PREEMPT_RT Kernel & Btrfs Subvolume Hierarchy
  - `ADR-0005`: Hyprland Wayland Compositor Selection
- **Operational Automation Scripts**:
  - `scripts/env_detect.sh`: Host execution environment, CPU virtualization, and WSL probe
  - `scripts/check_deps.sh`: Mandatory build tool and compiler dependency auditing
  - `scripts/build.sh`: Orchestrated OS build pipeline runner
  - `scripts/test.sh`: Architecture invariant and unit test suite harness
  - `scripts/clean.sh`: Safe workspace cleaning and build artifact purger
  - `scripts/package.sh`: Target package bundler and staging generator
  - `scripts/iso_generate.sh`: Bootable UEFI/BIOS live ISO mastering script
  - `scripts/vm_boot.sh`: Automated QEMU virtual machine test harness
  - `scripts/hardware_validate.sh`: Low-latency hardware, timer, and NIC validation engine
- **Automated Test Suite**: Unit tests in `tests/` verifying repo layout, manifest validity, script existence, risk isolation, and plugin capability constraints.
