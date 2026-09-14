# KAIROS OS Build Environment & Host System Specification

This document defines the technical prerequisites, supported host operating systems, resource budgets, and tooling dependencies required to build and verify KAIROS OS.

---

## ◈ 1. Supported Host Systems

KAIROS OS uses a containerized, hermetic build architecture based on **Fedora 40 (x86_64)**. Builds can be conducted natively on Linux or through virtualization environments that provide access to Linux namespaces and standard POSIX utilities.

### Tier 1: Fully Supported
- **Fedora Workstation / Server 40+** (Native)
- **Red Hat Enterprise Linux 9+ / Rocky Linux 9+ / AlmaLinux 9+**
- **Ubuntu LTS 22.04 / 24.04** (via Docker/Podman container or native package install)
- **Debian 12 (Bookworm)+**
- **Windows 11 with WSL2 (Fedora / Ubuntu distro)** with container engine integration

### Tier 2: Continuous Integration (CI) Environments
- **GitHub Actions Runners (`ubuntu-latest`)** with container engine
- **GitLab CI / Self-hosted Linux runners**

---

## ◈ 2. Minimum & Recommended Hardware Requirements

| Resource | Minimum Requirement | Recommended Specification | Justification |
|---|---|---|---|
| **Architecture** | `x86_64` | `x86_64` (v3 compliant: AVX2, FMA, BMI2) | Low-latency numeric compute & vectorization |
| **CPU Cores** | 2 logical cores | 8+ cores (multi-threaded) | Parallel kernel compilation and rootfs squashfs compression |
| **RAM** | 4 GB | 8 GB – 16 GB | In-memory package dependency resolution and squashfs staging |
| **Free Disk Space**| 10 GB | 30+ GB (Fast NVMe SSD preferred) | Base rootfs trees, kernel build caches, squashfs images, and Live ISOs |
| **Virtualization** | Optional | Intel VT-x / AMD-V (exposed to `/dev/kvm`) | Hardware-accelerated QEMU boot verification |

---

## ◈ 3. Required Packages & Tooling Audit

The `./scripts/check-environment` utility automatically validates all required dependencies before any build action.

### Core Build & Toolchain
- `bash` (v5.0+): Orchestration and script dispatching
- `make` (v4.0+): Target dependency resolution
- `python3` (v3.10+): Manifest parsing (`kairos.toml`), architecture validation, and automated unit testing
- `tar` & `gzip`: File archive handling

### Filesystem & ISO Mastering Tooling
- `mksquashfs` (`squashfs-tools` v4.5+): High-compression (Zstandard) rootfs generation
- `xorriso` (v1.5+): Hybrid ISO9660 mastering with UEFI El-Torito boot payload
- `sha256sum` (`coreutils`): Cryptographic attestation and checksum recording

### Optional Hypervisor & Emulation Tooling
- `qemu-system-x86_64`: Virtual machine test execution
- `qemu-img`: Virtual disk creation

---

## ◈ 4. Required Privileges

1. **Unprivileged User Execution**:
   - Running `./scripts/check-environment` requires zero elevated privileges.
   - Running `./scripts/test` and dry-run packaging requires zero elevated privileges.
2. **Container Engine Execution**:
   - When building via rootless `podman` or `docker`, standard user privileges are sufficient.
3. **Direct Host Chroot & Disk Mounting (Optional)**:
   - Creating raw loop devices or modifying physical block devices requires `sudo` or root privileges. Standard builds run in user space or within containers without needing host root.

---

## ◈ 5. Developer Workflow Quickstart

```bash
# 1. Inspect host compatibility
./scripts/check-environment

# 2. Run automated architectural test suite
./scripts/test

# 3. Build target OS components (base, kernel, desktop, trading, or all)
./scripts/build all

# 4. Master bootable hybrid Live ISO with cryptographic checksums
./scripts/build-iso

# 5. Boot the generated ISO in QEMU virtual machine
./scripts/run-vm

# 6. Clean build artifacts and temporary caches
./scripts/clean all
```
