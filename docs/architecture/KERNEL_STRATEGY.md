# KAIROS Kernel Strategy & Configuration Specification

## 1. Executive Summary & Kernel Strategy
KAIROS OS avoids maintaining an out-of-tree, heavily modified kernel. Instead, it employs a **maintainable upstream-compatible strategy**:
- **Baseline**: Upstream LTS/Stable enterprise kernel (Linux 6.x series).
- **Configuration Mechanism**: Modular configuration fragments (`.config.fragment`) layered over standard defconfig/distribution baseline.
- **Philosophy**: "Compatibility & Reliability First, Low-Latency Through Tunable Infrastructure". Premature and overly aggressive micro-patches that break hardware compatibility or graphics acceleration are rejected.

---

## 2. Core Strategic Dimensions

### 2.1 Kernel Version Strategy
- Track upstream long-term support (LTS) / active stable kernels (currently Linux 6.14.x / 6.6.x LTS).
- Ensure security errata and hardware drivers (Intel Meteor Lake/Arrow Lake, AMD Zen 4/5, NVIDIA Blackwell/Ada Lovelace) are seamlessly absorbed.

### 2.2 Configuration Strategy (Layered Modular Fragments)
Rather than a monolithic 10,000-line config file, KAIROS structures configurations into declarative fragments located in `config/kernel/`:
1. `00-core-hardware.config`: UEFI, EFI vars, PCIe, NVMe, SATA, USB 3/4.
2. `10-storage-filesystems.config`: Btrfs, XFS, ext4, VFAT, zram, dm-crypt.
3. `20-networking.config`: Modern 10G/25G Ethernet, Intel/Realtek Wi-Fi, WireGuard, eBPF, TCP low-latency buffers.
4. `30-desktop-graphics.config`: DRM/KMS, Mesa DRI drivers (Intel i915/Xe, AMDGPU, Nouveau), Wayland sync objects.
5. `40-audio-peripherals.config`: ALSA, SoundWire, USB Audio, Bluetooth HCI.
6. `50-security.config`: AppArmor, Seccomp, hardened usercopy, eBPF JIT lockdown, stack protector strong.
7. `60-performance.config`: PREEMPT_DYNAMIC, tickless idle (`NO_HZ_IDLE`/`NO_HZ_FULL`), 1000Hz timer, CPU frequency performance governors.
8. `70-virtualization.config`: KVM, VirtIO (PCI, Net, Block, Balloon, GPU), Hyper-V, and Xen guest drivers.

### 2.3 Module Strategy
- **Built-in (`=y`)**: Everything essential to mount rootfs and boot to user space: NVMe, Btrfs, Ext4, VFAT, EFI vars, TTY/Serial console, core PCIe bus.
- **Modules (`=m`)**: Peripherals, Wi-Fi drivers, Bluetooth, GPU drivers, USB audio, and auxiliary network drivers.

### 2.4 Firmware Strategy
- Comprehensive firmware distribution via `linux-firmware` (including `intel-gpu`, `amd-gpu`, `nvidia-gpu`, `realtek`, `atheros`, and `intel-microcode`/`amd-ucode`).

---

## 3. Subsystem Requirements Matrix

| Subsystem | Requirement | Configuration Directives |
|---|---|---|
| **UEFI & Boot** | UEFI 64-bit + EFI runtime variables | `CONFIG_EFI=y`, `CONFIG_EFIVAR_FS=y`, `CONFIG_EFI_STUB=y` |
| **Storage** | NVMe PCIe Gen4/5, SATA AHCI, Btrfs subvolumes | `CONFIG_BLK_DEV_NVME=y`, `CONFIG_SATA_AHCI=y`, `CONFIG_BTRFS_FS=y`, `CONFIG_ZRAM=y` |
| **Networking** | High-speed Ethernet, Wi-Fi 6/7, WireGuard, eBPF | `CONFIG_IGB=m`, `CONFIG_E1000E=m`, `CONFIG_IWLMVM=m`, `CONFIG_WIREGUARD=y`, `CONFIG_BPF_SYSCALL=y` |
| **Graphics** | Wayland/Hyprland DRM/KMS acceleration | `CONFIG_DRM=y`, `CONFIG_DRM_AMDGPU=m`, `CONFIG_DRM_I915=m`, `CONFIG_DRM_XE=m`, `CONFIG_DRM_NOUVEAU=m` |
| **Desktop / Audio**| Low-latency audio and Bluetooth | `CONFIG_SND_HDA_INTEL=m`, `CONFIG_SND_USB_AUDIO=m`, `CONFIG_BT=m`, `CONFIG_BT_HCIBTUSB=m` |
| **Security** | Mandatory Access Control, memory bounds checking | `CONFIG_SECURITY_APPARMOR=y`, `CONFIG_SECCOMP=y`, `CONFIG_HARDENED_USERCOPY=y` |
| **Virtualization**| KVM host & VirtIO guest compatibility | `CONFIG_KVM=y`, `CONFIG_KVM_INTEL=m`, `CONFIG_KVM_AMD=m`, `CONFIG_VIRTIO_PCI=y`, `CONFIG_VIRTIO_BLK=y`, `CONFIG_VIRTIO_NET=y` |
| **Performance** | Deterministic scheduling without extreme kernel forks | `CONFIG_PREEMPT_DYNAMIC=y`, `CONFIG_HZ_1000=y`, `CONFIG_CPU_FREQ_DEFAULT_GOV_PERFORMANCE=y` |
