#!/usr/bin/env python3
"""
KAIROS OS Installer  ─  Complete Production Implementation
==========================================================
Installation flow:
  BOOT → HARDWARE DETECTION → LANGUAGE → KEYBOARD → NETWORK →
  DISK → ENCRYPTION → USER → HOSTNAME → TIMEZONE →
  INSTALL PROFILE → OPTIONAL COMPONENTS → CONFIRM →
  INSTALL → BOOTLOADER → HEALTH CHECK → FIRST BOOT

Profiles: Minimal | Trader | Quant Research | Developer | Full

Safety Contract:
  - NEVER destructively modify disks without explicit typed confirmation
  - All disk operations are guarded by confirm_destructive()
  - Dry-run mode (--dry-run / -n) makes ZERO disk changes
  - Full audit log: /tmp/kairos-install.log
  - Install manifest: /tmp/kairos-install-manifest.json
"""

from __future__ import annotations

import sys
import os

# ── Ensure UTF-8 output on all platforms (incl. Windows cp1252) ───────────────
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
import re
import json
import time
import shutil
import subprocess
import datetime
import platform
import hashlib
import logging
import signal
import struct
import glob
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Any

# ── Version ──────────────────────────────────────────────────────────────────
INSTALLER_VERSION = "0.1.0"
KAIROS_VERSION    = "0.1.0-alpha.1"
KAIROS_CODENAME   = "Aethelgard"

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE = "/tmp/kairos-install.log"
try:
    _fh = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
except OSError:
    LOG_FILE = os.path.join(os.path.expanduser("~"), "kairos-install.log")
    _fh = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[_fh],
)
log = logging.getLogger("kairos-installer")

# ── ANSI colors (auto-disabled when not a tty or NO_COLOR is set) ─────────────
class C:
    RESET  = "\033[0m"
    BOLD   = "\033[1m"
    DIM    = "\033[2m"
    RED    = "\033[31m"
    GREEN  = "\033[32m"
    YELLOW = "\033[33m"
    BLUE   = "\033[34m"
    CYAN   = "\033[36m"
    WHITE  = "\033[37m"
    BGRED  = "\033[41m"

def _strip_color():
    for attr in list(vars(C).keys()):
        if not attr.startswith("_"):
            setattr(C, attr, "")

if not sys.stdout.isatty() or os.environ.get("NO_COLOR") or os.environ.get("TERM") == "dumb":
    _strip_color()

# ── Terminal helpers ──────────────────────────────────────────────────────────

def _w(n: int = 72) -> str:
    return "─" * n

def banner():
    print(f"{C.CYAN}{C.BOLD}")
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║          KAIROS OS  ─  Installation & System Configuration           ║")
    print(f"║          Version {KAIROS_VERSION:<10}  Codename: {KAIROS_CODENAME:<20}  ║")
    print("║          Adaptive Trading OS  ─  Quantitative Research Platform      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    print(C.RESET)

def section(title: str):
    print(f"\n{C.BLUE}{_w(2)} {C.BOLD}{title}{C.RESET}{C.BLUE} {_w(2)}{C.RESET}")

def info(msg: str):
    print(f"  {C.GREEN}✓{C.RESET}  {msg}")
    log.info(msg)

def warn(msg: str):
    print(f"  {C.YELLOW}⚠{C.RESET}  {msg}")
    log.warning(msg)

def error(msg: str):
    print(f"  {C.RED}✗{C.RESET}  {msg}")
    log.error(msg)

def step_progress(n: int, total: int, desc: str, done: bool = False):
    pct = int((n / total) * 100)
    if done:
        print(f"  {C.GREEN}[{pct:3d}%]{C.RESET}  {desc:<55}  {C.DIM}done{C.RESET}")
    else:
        print(f"  {C.CYAN}[{pct:3d}%]{C.RESET}  {desc:<55}", end="\r", flush=True)

def ask(prompt: str, default: str = "", secret: bool = False) -> str:
    hint = f" [{default}]" if default else ""
    try:
        if secret:
            import getpass
            val = getpass.getpass(f"  {C.BOLD}?{C.RESET}  {prompt}: ")
        else:
            val = input(f"  {C.BOLD}?{C.RESET}  {prompt}{hint}: ").strip()
        return val if val else default
    except (EOFError, KeyboardInterrupt):
        print()
        return default

def ask_choice(prompt: str, options: List[str], default_idx: int = 0) -> str:
    print(f"\n  {C.BOLD}{prompt}{C.RESET}")
    for i, opt in enumerate(options):
        marker = f"{C.GREEN}▶{C.RESET}" if i == default_idx else " "
        print(f"   {marker} {i+1:2d}.  {opt}")
    while True:
        raw = ask(f"Select [1-{len(options)}]", str(default_idx + 1))
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            pass
        warn(f"Enter a number between 1 and {len(options)}.")

def confirm(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    raw = ask(f"{prompt} ({hint})").lower()
    if not raw:
        return default
    return raw.startswith("y")

def confirm_destructive(description: str) -> bool:
    """
    Gate for any destructive disk operation.
    Requires the user to type exactly: YES, DESTROY DATA
    """
    print()
    print(f"  {C.BGRED}{C.WHITE} ▲  DESTRUCTIVE OPERATION  ▲ {C.RESET}")
    print(f"  {C.RED}{description}{C.RESET}")
    print(f"  {C.YELLOW}This CANNOT be undone. All data will be PERMANENTLY ERASED.{C.RESET}")
    print()
    print(f"  Type  {C.RED}{C.BOLD}YES, DESTROY DATA{C.RESET}  to confirm, or press Enter to abort:")
    print()
    raw = ask("Confirmation").strip()
    confirmed = (raw == "YES, DESTROY DATA")
    if confirmed:
        log.warning(f"Destructive operation confirmed by user: {description}")
    else:
        log.info(f"Destructive operation ABORTED by user: {description}")
    return confirmed

def run_cmd(
    cmd: List[str],
    check: bool = True,
    capture: bool = False,
    dry_run: bool = False,
    input_text: Optional[str] = None,
    timeout: int = 300,
) -> subprocess.CompletedProcess:
    """
    Run a command, logging it and respecting dry-run mode.
    """
    log.debug(f"CMD: {' '.join(str(c) for c in cmd)}")
    if dry_run:
        print(f"  {C.DIM}[DRY-RUN]  {' '.join(str(c) for c in cmd)}{C.RESET}")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    kwargs: Dict[str, Any] = {
        "check": check,
        "text": True,
        "timeout": timeout,
    }
    if capture:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    if input_text is not None:
        kwargs["input"] = input_text
        kwargs["stdin"] = subprocess.PIPE
    try:
        return subprocess.run(cmd, **kwargs)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Command timed out after {timeout}s: {' '.join(cmd)}")
    except FileNotFoundError:
        raise RuntimeError(f"Command not found: {cmd[0]}")

def chroot_run(
    cmd: List[str],
    check: bool = True,
    dry_run: bool = False,
    input_text: Optional[str] = None,
    target: str = "/mnt",
) -> subprocess.CompletedProcess:
    """Run a command inside the chroot target."""
    if not shutil.which("arch-chroot") and not shutil.which("chroot"):
        log.warning(f"No chroot tool found; skipping: {cmd}")
        return subprocess.CompletedProcess(cmd, 0)
    tool = "arch-chroot" if shutil.which("arch-chroot") else "chroot"
    return run_cmd([tool, target] + cmd, check=check, dry_run=dry_run,
                   input_text=input_text)


# ── Disk helpers ──────────────────────────────────────────────────────────────

def partition_name(disk: str, num: int) -> str:
    """
    Return the correct partition device name.
    NVMe: /dev/nvme0n1 → /dev/nvme0n1p1
    SATA/SCSI: /dev/sda → /dev/sda1
    VirtIO: /dev/vda → /dev/vda1
    Loop: /dev/loop0 → /dev/loop0p1
    """
    if re.search(r"(nvme|loop|mmcblk)", disk):
        return f"{disk}p{num}"
    return f"{disk}{num}"

def get_disk_uuid(device: str) -> str:
    """Return the UUID for a block device."""
    try:
        out = subprocess.check_output(
            ["blkid", "-s", "UUID", "-o", "value", device],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        return out if out else "00000000-0000-0000-0000-000000000000"
    except Exception:
        return "00000000-0000-0000-0000-000000000000"

def get_disk_partuuid(device: str) -> str:
    """Return the PARTUUID for a block device."""
    try:
        out = subprocess.check_output(
            ["blkid", "-s", "PARTUUID", "-o", "value", device],
            stderr=subprocess.DEVNULL, text=True
        ).strip()
        return out if out else ""
    except Exception:
        return ""

def read_block_devices() -> List[Tuple[str, float, str]]:
    """
    Enumerate physical block devices.
    Returns list of (device_path, size_gib, model).
    """
    devices = []
    sys_block = "/sys/block"
    if not os.path.exists(sys_block):
        return [("/dev/sda", 50.0, "Virtual Disk")]

    for name in sorted(os.listdir(sys_block)):
        if name.startswith(("loop", "ram", "sr", "dm-", "md", "zram")):
            continue
        # Only physical disks, not partitions
        dev_path = f"/dev/{name}"
        size_bytes = 0
        try:
            with open(f"{sys_block}/{name}/size") as f:
                sectors = int(f.read().strip())
                size_bytes = sectors * 512
        except Exception:
            pass
        size_gib = size_bytes / (1024 ** 3)
        if size_gib < 0.01:
            continue
        model = ""
        try:
            with open(f"{sys_block}/{name}/device/model") as f:
                model = f.read().strip()
        except Exception:
            pass
        if not model:
            try:
                result = subprocess.run(
                    ["lsblk", "-d", "-o", "MODEL", "-n", dev_path],
                    capture_output=True, text=True
                )
                model = result.stdout.strip()
            except Exception:
                pass
        devices.append((dev_path, size_gib, model))
    return devices


def detect_existing_systems(disk: str) -> List[Dict[str, str]]:
    """
    Scan a disk for existing operating systems.
    Returns list of found systems with their partition and type.
    """
    found = []

    # Read partition table with blkid
    try:
        out = subprocess.check_output(
            ["lsblk", "-J", "-o", "NAME,FSTYPE,LABEL,UUID,PARTLABEL,MOUNTPOINTS,SIZE", disk],
            stderr=subprocess.DEVNULL, text=True
        )
        data = json.loads(out)
        block_devices = data.get("blockdevices", [])
    except Exception:
        block_devices = []

    def _check_partition(dev_data: dict, parent_disk: str):
        name    = dev_data.get("name", "")
        fstype  = dev_data.get("fstype") or ""
        label   = dev_data.get("label") or ""
        partlbl = dev_data.get("partlabel") or ""
        dev     = f"/dev/{name}"

        # Mount temporarily to check for OS signatures
        tmpdir = None
        mounted = False
        try:
            if fstype in ("ext4", "ext3", "btrfs", "xfs", "vfat", "ntfs", "f2fs"):
                tmpdir = subprocess.check_output(["mktemp", "-d"], text=True).strip()
                result = subprocess.run(
                    ["mount", "-o", "ro", dev, tmpdir],
                    capture_output=True, timeout=10
                )
                if result.returncode == 0:
                    mounted = True

                    # Linux detection
                    if os.path.exists(os.path.join(tmpdir, "etc/os-release")):
                        osrel = {}
                        with open(os.path.join(tmpdir, "etc/os-release")) as f:
                            for line in f:
                                if "=" in line:
                                    k, v = line.strip().split("=", 1)
                                    osrel[k] = v.strip('"\'')
                        found.append({
                            "device": dev,
                            "type": "Linux",
                            "name": osrel.get("PRETTY_NAME", osrel.get("NAME", "Linux")),
                            "version": osrel.get("VERSION_ID", ""),
                        })

                    # Windows detection via NTFS markers
                    for wpath in ["Windows/System32", "WINDOWS/System32", "windows/system32"]:
                        if os.path.isdir(os.path.join(tmpdir, wpath)):
                            found.append({"device": dev, "type": "Windows",
                                          "name": "Microsoft Windows", "version": ""})
                            break

                    # EFI partition detection
                    efi_markers = ["EFI/Microsoft", "EFI/ubuntu", "EFI/arch",
                                   "EFI/debian", "EFI/fedora", "EFI/grub"]
                    for marker in efi_markers:
                        if os.path.isdir(os.path.join(tmpdir, marker)):
                            vendor = marker.split("/")[1]
                            found.append({"device": dev, "type": "EFI",
                                          "name": f"EFI partition ({vendor})", "version": ""})
                            break
        except Exception:
            pass
        finally:
            if mounted and tmpdir:
                subprocess.run(["umount", tmpdir], capture_output=True)
            if tmpdir and os.path.isdir(tmpdir):
                subprocess.run(["rmdir", tmpdir], capture_output=True)

        for child in dev_data.get("children", []):
            _check_partition(child, parent_disk)

    for bd in block_devices:
        for child in bd.get("children", []):
            _check_partition(child, disk)

    # Also check via sgdisk for partition type GUIDs
    try:
        out = subprocess.check_output(
            ["sgdisk", "--print", disk], stderr=subprocess.DEVNULL, text=True
        )
        if "Microsoft basic data" in out:
            if not any(s["type"] == "Windows" for s in found):
                found.append({"device": disk, "type": "Windows",
                               "name": "Microsoft Windows (detected via GPT)", "version": ""})
    except Exception:
        pass

    return found


# ── Install State ─────────────────────────────────────────────────────────────

@dataclass
class InstallState:
    dry_run      : bool  = False
    language     : str   = "en_US.UTF-8"
    kb_layout    : str   = "us"
    kb_variant   : str   = ""
    timezone     : str   = "UTC"
    hostname     : str   = "kairos"
    username     : str   = "trader"
    password     : str   = field(default="", repr=False)
    root_locked  : bool  = True
    root_password: str   = field(default="", repr=False)
    disk         : str   = ""
    efi_detected : bool  = False
    encrypt      : bool  = True
    luks_pass    : str   = field(default="", repr=False)
    tpm2_enroll  : bool  = False
    profile      : str   = "Trader"
    optional     : List[str] = field(default_factory=list)
    network_cfg  : Dict  = field(default_factory=dict)
    hw           : Dict  = field(default_factory=dict)
    existing_sys : List  = field(default_factory=list)
    install_target: str  = "/mnt"

    # Derived (computed during install)
    part_efi   : str = ""
    part_boot  : str = ""
    part_root  : str = ""
    uuid_efi   : str = ""
    uuid_boot  : str = ""
    uuid_root  : str = ""

    def safe_dict(self) -> dict:
        """Return state dict with secrets redacted."""
        d = {}
        for k, v in self.__dict__.items():
            if k in ("password", "root_password", "luks_pass"):
                d[k] = "<REDACTED>"
            else:
                d[k] = v
        return d

    def save_manifest(self, path: str = "/tmp/kairos-install-manifest.json"):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.safe_dict(), f, indent=2, default=str)
            log.info(f"Manifest saved: {path}")
        except Exception as e:
            log.warning(f"Could not save manifest: {e}")


# ── Profile definitions ────────────────────────────────────────────────────────

PROFILES: Dict[str, Dict] = {
    "Minimal": {
        "description": "Core OS only. Console + SSH. No desktop, no trading stack.",
        "disk_gb_min": 4,
        "packages": [
            "linux-kairos-rt", "linux-firmware", "systemd", "base",
            "openssh", "btrfs-progs", "cryptsetup", "dosfstools",
            "e2fsprogs", "util-linux", "iproute2", "iputils",
            "dhcpcd", "curl", "wget", "git", "vim", "sudo",
        ],
        "services": ["sshd", "systemd-networkd", "systemd-resolved", "systemd-timesyncd"],
        "groups_extra": [],
    },
    "Trader": {
        "description": "Full desktop + complete trading stack. Recommended for live trading.",
        "disk_gb_min": 10,
        "packages": [
            "linux-kairos-rt", "linux-firmware", "systemd", "base",
            "hyprland", "xdg-desktop-portal-hyprland", "waybar",
            "kitty", "wofi", "mako", "polkit",
            "pipewire", "wireplumber", "pipewire-pulse", "pavucontrol",
            "networkmanager", "network-manager-applet",
            "kairos-shell", "kairos-riskd", "kairos-feedd",
            "kairos-executiond", "kairos-watchdog",
            "kairos-command-center", "kairos-desktop",
            "btrfs-progs", "cryptsetup", "openssh",
            "python3", "python-pip",
            "snapper", "snap-pac",
        ],
        "services": [
            "NetworkManager", "kairos-riskd", "kairos-feedd",
            "kairos-watchdog", "sshd", "snapper-timeline.timer",
            "snapper-cleanup.timer", "systemd-timesyncd",
        ],
        "groups_extra": ["trading"],
    },
    "Quant Research": {
        "description": "Full desktop + quantitative research environment (Python/Jupyter/data stack).",
        "disk_gb_min": 20,
        "packages": [
            "linux-kairos-rt", "linux-firmware", "systemd", "base",
            "hyprland", "xdg-desktop-portal-hyprland", "waybar",
            "kitty", "wofi", "mako", "polkit",
            "pipewire", "wireplumber",
            "networkmanager",
            "python3", "python-pip", "python-numpy", "python-pandas",
            "python-scipy", "python-matplotlib", "python-scikit-learn",
            "jupyter-notebook", "jupyterlab",
            "kairos-researchd", "duckdb",
            "btrfs-progs", "cryptsetup", "openssh",
            "snapper", "snap-pac",
        ],
        "services": [
            "NetworkManager", "kairos-researchd", "sshd",
            "snapper-timeline.timer", "systemd-timesyncd",
        ],
        "groups_extra": ["research"],
    },
    "Developer": {
        "description": "Minimal base + dev tools. Modular — use 'kairos dev enable' to add toolchains.",
        "disk_gb_min": 10,
        "packages": [
            "linux-kairos-rt", "linux-firmware", "systemd", "base",
            "hyprland", "kitty", "networkmanager",
            "git", "make", "gcc", "clang", "llvm",
            "python3", "python-pip", "nodejs", "npm",
            "btrfs-progs", "cryptsetup", "openssh",
            "gdb", "valgrind", "strace", "perf",
            "docker", "docker-compose",
        ],
        "services": [
            "NetworkManager", "sshd", "docker",
            "systemd-timesyncd",
        ],
        "groups_extra": ["docker"],
    },
    "Full": {
        "description": "All components: desktop, trading, research, dev, AI agents. Largest install.",
        "disk_gb_min": 30,
        "packages": [
            "linux-kairos-rt", "linux-firmware", "systemd", "base",
            "hyprland", "xdg-desktop-portal-hyprland", "waybar",
            "kitty", "wofi", "mako", "polkit",
            "pipewire", "wireplumber", "pipewire-pulse",
            "networkmanager", "network-manager-applet",
            "kairos-shell", "kairos-riskd", "kairos-feedd",
            "kairos-executiond", "kairos-watchdog", "kairos-command-center",
            "kairos-desktop", "kairos-researchd", "kairos-agentd",
            "kairos-adaptive",
            "python3", "python-pip", "python-numpy", "python-pandas",
            "python-scipy", "python-matplotlib", "python-scikit-learn",
            "jupyter-notebook", "jupyterlab",
            "git", "make", "gcc", "clang", "rust",
            "docker", "docker-compose",
            "openssh", "btrfs-progs", "cryptsetup",
            "snapper", "snap-pac",
        ],
        "services": [
            "NetworkManager", "kairos-riskd", "kairos-feedd",
            "kairos-watchdog", "kairos-researchd", "kairos-agentd",
            "kairos-adaptive", "sshd", "docker",
            "snapper-timeline.timer", "snapper-cleanup.timer",
            "systemd-timesyncd",
        ],
        "groups_extra": ["trading", "research", "docker"],
    },
}

OPTIONAL_COMPONENTS: List[Tuple[str, str, List[str]]] = [
    ("wireguard",       "WireGuard VPN client",                   ["wireguard-tools"]),
    ("yubikey",         "YubiKey / FIDO2 hardware authentication", ["yubikey-manager", "pam-u2f"]),
    ("tpm2",            "TPM2 disk unlock (auto on trusted boot)", ["tpm2-tools", "tpm2-tss"]),
    ("docker",          "Docker container runtime",               ["docker", "docker-compose"]),
    ("virtualization",  "QEMU/KVM virtual machines",             ["qemu-full", "virt-manager", "libvirt"]),
    ("developer-tools", "Full dev toolchain (Rust/Go/LLVM/GDB)", ["rust", "go", "llvm", "gdb", "valgrind"]),
    ("quant-libs",      "Full Python quant library stack",        ["python-statsmodels", "python-sympy",
                                                                    "python-numba", "python-polars"]),
    ("ai-agents",       "KAIROS autonomous AI agent platform",    ["kairos-agentd"]),
    ("adaptive-intel",  "Adaptive Evolution Intelligence (AEI)",  ["kairos-adaptive"]),
    ("zsh-env",         "Z-Shell + KAIROS theme + trading aliases",["zsh", "zsh-completions"]),
    ("obs",             "OBS Studio for screen recording",        ["obs-studio"]),
    ("snapper",         "Snapper automatic Btrfs snapshots",      ["snapper", "snap-pac"]),
]

LANGUAGES = [
    ("en_US.UTF-8", "English (United States)"),
    ("en_GB.UTF-8", "English (United Kingdom)"),
    ("de_DE.UTF-8", "German"),
    ("fr_FR.UTF-8", "French"),
    ("es_ES.UTF-8", "Spanish"),
    ("it_IT.UTF-8", "Italian"),
    ("pt_BR.UTF-8", "Portuguese (Brazil)"),
    ("ja_JP.UTF-8", "Japanese"),
    ("zh_CN.UTF-8", "Chinese Simplified"),
    ("ko_KR.UTF-8", "Korean"),
    ("ru_RU.UTF-8", "Russian"),
    ("ar_SA.UTF-8", "Arabic"),
    ("pl_PL.UTF-8", "Polish"),
    ("nl_NL.UTF-8", "Dutch"),
    ("sv_SE.UTF-8", "Swedish"),
]

KB_LAYOUTS = [
    ("us",      "US English (QWERTY)"),
    ("uk",      "United Kingdom"),
    ("de",      "German (QWERTZ)"),
    ("fr",      "French (AZERTY)"),
    ("es",      "Spanish"),
    ("it",      "Italian"),
    ("ru",      "Russian"),
    ("jp106",   "Japanese"),
    ("dvorak",  "Dvorak"),
    ("colemak", "Colemak"),
    ("workman", "Workman"),
    ("bepo",    "Bépo (French ergonomic)"),
]

TIMEZONES = [
    "UTC",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Sao_Paulo",
    "America/Toronto",
    "Europe/London",
    "Europe/Paris",
    "Europe/Berlin",
    "Europe/Frankfurt",
    "Europe/Zurich",
    "Europe/Amsterdam",
    "Europe/Stockholm",
    "Europe/Warsaw",
    "Europe/Moscow",
    "Asia/Kolkata",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Asia/Hong_Kong",
    "Asia/Singapore",
    "Asia/Seoul",
    "Asia/Dubai",
    "Australia/Sydney",
    "Australia/Melbourne",
    "Pacific/Auckland",
]


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 0: Boot-time Hardware Detection
# ═══════════════════════════════════════════════════════════════════════════════

def phase_hardware(state: InstallState) -> List[Tuple[str, float, str]]:
    section("PHASE 0  ─  Hardware Detection & Boot Environment")

    # ── Firmware mode ─────────────────────────────────────────
    state.efi_detected = os.path.exists("/sys/firmware/efi")
    efivars_ok = False
    if state.efi_detected:
        efivars_path = "/sys/firmware/efi/efivars"
        efivars_ok = os.path.isdir(efivars_path) and bool(os.listdir(efivars_path))

    if state.efi_detected:
        info(f"Firmware : UEFI {'(EFI vars accessible)' if efivars_ok else '(vars unavailable)'}")
    else:
        info("Firmware : Legacy BIOS")

    # ── CPU ───────────────────────────────────────────────────
    cpu_model = platform.processor() or "x86_64"
    cpu_cores = os.cpu_count() or 1
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "model name" in line:
                    cpu_model = line.split(":", 1)[1].strip()
                    break
    except Exception:
        pass
    info(f"CPU      : {cpu_model[:60]} ({cpu_cores} cores)")

    # ── Memory ────────────────────────────────────────────────
    mem_total_mb = 0
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    mem_total_mb = int(line.split()[1]) // 1024
                    break
    except Exception:
        pass
    info(f"Memory   : {mem_total_mb} MiB ({mem_total_mb // 1024} GiB)")
    if mem_total_mb < 2048:
        warn("Less than 2 GiB RAM — Minimal profile strongly recommended.")

    # ── Block devices ─────────────────────────────────────────
    block_devs = read_block_devices()
    if not block_devs:
        warn("No block devices found. Dry-run or virtual environment.")
        block_devs = [("/dev/sda", 50.0, "Virtual Disk")]

    for dev, size_gib, model in block_devs:
        model_str = f"  [{model}]" if model else ""
        info(f"Disk     : {dev}  ({size_gib:.1f} GiB){model_str}")

    # ── GPU ───────────────────────────────────────────────────
    gpus = []
    if shutil.which("lspci"):
        try:
            out = subprocess.check_output(["lspci"], stderr=subprocess.DEVNULL, text=True)
            for line in out.splitlines():
                if any(x in line for x in ("VGA", "Display", "3D controller")):
                    gpus.append(line.split(":")[-1].strip()[:60])
        except Exception:
            pass
    for g in gpus[:3]:
        info(f"GPU      : {g}")
    if not gpus:
        info("GPU      : Not detected (framebuffer/virtual fallback)")

    # ── Storage state ─────────────────────────────────────────
    rt_kernel = False
    try:
        with open("/proc/version") as f:
            content = f.read()
            rt_kernel = "PREEMPT_RT" in content or "-rt" in content
    except Exception:
        pass
    if rt_kernel:
        info("Kernel   : PREEMPT_RT detected — realtime scheduling active")

    state.hw = {
        "cpu": cpu_model,
        "cores": cpu_cores,
        "memory_mb": mem_total_mb,
        "disks": [(d, g, m) for d, g, m in block_devs],
        "efi": state.efi_detected,
        "efivars_ok": efivars_ok,
        "gpus": gpus,
        "rt_kernel": rt_kernel,
    }
    log.info(f"Hardware detection complete: {state.hw}")
    return block_devs


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 1: Language
# ═══════════════════════════════════════════════════════════════════════════════

def phase_language(state: InstallState):
    section("PHASE 1  ─  System Language & Locale")
    options = [f"{locale}  ({name})" for locale, name in LANGUAGES]
    choice = ask_choice("Select system language", options, default_idx=0)
    state.language = choice.split()[0]
    info(f"Language: {state.language}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 2: Keyboard
# ═══════════════════════════════════════════════════════════════════════════════

def phase_keyboard(state: InstallState):
    section("PHASE 2  ─  Keyboard Layout")
    options = [f"{code:<10}  {desc}" for code, desc in KB_LAYOUTS]
    choice = ask_choice("Select keyboard layout", options, default_idx=0)
    state.kb_layout = choice.split()[0]
    info(f"Keyboard layout: {state.kb_layout}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 3: Network
# ═══════════════════════════════════════════════════════════════════════════════

def phase_network(state: InstallState):
    section("PHASE 3  ─  Network Configuration")

    # Discover interfaces
    ifaces = []
    try:
        with open("/proc/net/dev") as f:
            for line in f.readlines()[2:]:
                if ":" in line:
                    iface = line.split(":")[0].strip()
                    if iface not in ("lo", ""):
                        ifaces.append(iface)
    except Exception:
        pass
    if not ifaces:
        warn("No network interfaces found. Skipping network configuration.")
        state.network_cfg = {"method": "skip"}
        return

    info(f"Available interfaces: {', '.join(ifaces)}")

    # Interface selection if multiple
    if len(ifaces) > 1:
        iface_choice = ask_choice("Select primary interface", ifaces, default_idx=0)
    else:
        iface_choice = ifaces[0]
        info(f"Using interface: {iface_choice}")

    # Method selection
    method = ask_choice(
        "Network configuration method",
        ["DHCP — automatic (recommended)", "Static IP", "Skip (configure manually later)"],
        default_idx=0
    )

    if method.startswith("DHCP"):
        state.network_cfg = {"method": "dhcp", "interface": iface_choice}
        info(f"Network: DHCP on {iface_choice}")
        # Try to test connectivity
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "3", "8.8.8.8"],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                info("Network connectivity: verified (ping 8.8.8.8 OK)")
            else:
                warn("Network connectivity: ping failed. DHCP may not be active yet.")
        except Exception:
            pass

    elif method.startswith("Static"):
        ip      = ask("IP address with prefix (e.g. 192.168.1.100/24)", "192.168.1.100/24")
        gateway = ask("Default gateway", "192.168.1.1")
        dns1    = ask("Primary DNS", "1.1.1.1")
        dns2    = ask("Secondary DNS", "8.8.8.8")
        state.network_cfg = {
            "method": "static",
            "interface": iface_choice,
            "address": ip,
            "gateway": gateway,
            "dns": [dns1, dns2],
        }
        info(f"Static: {ip} via {gateway}, DNS: {dns1}, {dns2}")
    else:
        state.network_cfg = {"method": "skip"}
        warn("Network configuration skipped. Manual setup required post-install.")


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 4: Disk Selection, Existing System Detection & Layout
# ═══════════════════════════════════════════════════════════════════════════════

def phase_disk(state: InstallState, block_devs: List[Tuple[str, float, str]]):
    section("PHASE 4  ─  Disk Selection & Partition Layout")

    warn("Disk partitioning will not begin until you provide explicit typed confirmation.")
    print()

    # Build selection list
    dev_options = []
    for dev, size_gib, model in block_devs:
        model_str = f"  [{model}]" if model else ""
        dev_options.append(f"{dev}  ({size_gib:.1f} GiB){model_str}")
    dev_options.append("Skip (manual partitioning — installer will not touch disks)")

    choice = ask_choice("Select installation disk", dev_options, default_idx=0)
    if "Skip" in choice or "manual" in choice.lower():
        state.disk = ""
        warn("Manual partitioning selected. No disk changes will be made by the installer.")
        return

    state.disk = choice.split()[0]
    info(f"Selected disk: {state.disk}")

    # Minimum size check
    disk_gib = next((g for d, g, _ in block_devs if d == state.disk), 0.0)
    min_gib = PROFILES[state.profile]["disk_gb_min"] if state.profile else 8
    if disk_gib < min_gib and not state.dry_run:
        warn(f"Disk is {disk_gib:.1f} GiB. Profile '{state.profile}' requires {min_gib} GiB minimum.")
        if not confirm("Continue anyway?", default=False):
            state.disk = ""
            return

    # ── Detect existing operating systems ─────────────────────────────────────
    section("Scanning for Existing Operating Systems")
    print("  Scanning disk for existing OS installations...", end="\r", flush=True)
    try:
        state.existing_sys = detect_existing_systems(state.disk)
    except Exception as e:
        log.warning(f"Existing system detection error: {e}")
        state.existing_sys = []

    if state.existing_sys:
        print()
        warn(f"Found {len(state.existing_sys)} existing operating system(s) on {state.disk}:")
        for sys_info in state.existing_sys:
            warn(f"  {sys_info['type']:8s}  {sys_info['name']}  ({sys_info['device']})")
        print()
        warn("INSTALLING KAIROS WILL DESTROY ALL EXISTING DATA AND OPERATING SYSTEMS.")
        print()
    else:
        print(f"  {C.GREEN}✓{C.RESET}  No existing operating systems detected.       ")
        log.info(f"No existing systems found on {state.disk}")

    # ── Show proposed partition layout ────────────────────────────────────────
    p1 = partition_name(state.disk, 1)
    p2 = partition_name(state.disk, 2)
    p3 = partition_name(state.disk, 3)

    bios_only = not state.efi_detected
    if bios_only:
        print(f"""
  Proposed Layout for {state.disk}  ({disk_gib:.1f} GiB)  [Legacy BIOS]
  ┌──────────────┬──────────┬─────────────┬────────────────────────┐
  │  Partition   │  Size    │  Type       │  Purpose               │
  ├──────────────┼──────────┼─────────────┼────────────────────────┤
  │  {p1:<12}  │  2 MiB   │  BIOS Boot  │  GRUB2 embedding       │
  │  {p2:<12}  │  2 GiB   │  ext4       │  /boot                 │
  │  {p3:<12}  │  Rest    │  LUKS2+Btrfs│  Encrypted Root        │
  └──────────────┴──────────┴─────────────┴────────────────────────┘""")
    else:
        print(f"""
  Proposed Layout for {state.disk}  ({disk_gib:.1f} GiB)  [UEFI]
  ┌──────────────┬──────────┬─────────────┬────────────────────────┐
  │  Partition   │  Size    │  Type       │  Purpose               │
  ├──────────────┼──────────┼─────────────┼────────────────────────┤
  │  {p1:<12}  │  1 GiB   │  EFI (FAT32)│  EFI System Partition  │
  │  {p2:<12}  │  2 GiB   │  ext4       │  /boot                 │
  │  {p3:<12}  │  Rest    │  LUKS2+Btrfs│  Encrypted Root        │
  └──────────────┴──────────┴─────────────┴────────────────────────┘""")

    print(f"""
  Btrfs Subvolumes inside {p3}:
    @             →  /                  Root OS tree (snapshot-capable)
    @home         →  /home              User workspaces & research data
    @snapshots    →  /.snapshots        Atomic rollback targets
    @var_log      →  /var/log           System & audit logs
    @vault        →  /var/kairos/vault  TPM2/encrypted credentials
    @data         →  /data              High-throughput tick data cache

  Mount options: rw,noatime,compress=zstd:1,space_cache=v2,autodefrag
""")

    if not confirm("Accept this partition layout?", default=True):
        warn("Partition layout declined. No changes made.")
        state.disk = ""
        return

    # Store computed partition names
    state.part_efi  = p1
    state.part_boot = p2
    state.part_root = p3


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 5: Disk Encryption
# ═══════════════════════════════════════════════════════════════════════════════

def phase_encryption(state: InstallState):
    section("PHASE 5  ─  Full-Disk Encryption (LUKS2)")

    if not state.disk:
        info("No disk selected — encryption phase skipped.")
        return

    state.encrypt = confirm(
        "Enable full-disk encryption? (LUKS2, AES-256-XTS, Argon2id KDF)",
        default=True
    )

    if not state.encrypt:
        warn("Encryption DISABLED. Anyone with physical access can read your data.")
        return

    info("Encryption algorithm : AES-256-XTS (aes-xts-plain64)")
    info("Key derivation       : Argon2id (memory-hard, GPU-resistant)")

    while True:
        pw1 = ask("Encryption passphrase", secret=True)
        if not pw1:
            warn("Passphrase cannot be empty.")
            continue
        pw2 = ask("Confirm passphrase", secret=True)
        if pw1 != pw2:
            warn("Passphrases do not match. Try again.")
            continue
        if len(pw1) < 8:
            warn("Passphrase is very short (< 8 chars). This is insecure.")
            if not confirm("Use this passphrase anyway?", default=False):
                continue
        elif len(pw1) < 16:
            warn("Passphrase is short. Recommended: 16+ characters or a passphrase.")
        state.luks_pass = pw1
        break

    info("LUKS2 passphrase accepted.")

    # TPM2 option
    tpm2_available = os.path.exists("/dev/tpm0") or bool(glob.glob("/dev/tpmrm*"))
    if tpm2_available:
        state.tpm2_enroll = confirm(
            "TPM2 chip detected. Enroll for automatic unlock on trusted hardware?",
            default=False
        )
        if state.tpm2_enroll:
            info("TPM2 enrollment will be performed on first boot.")
    else:
        info("TPM2: not detected. Manual passphrase entry required at boot.")


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 6: User Account
# ═══════════════════════════════════════════════════════════════════════════════

def phase_user(state: InstallState):
    section("PHASE 6  ─  User Account Configuration")

    # Username
    while True:
        state.username = ask("Primary username", default="trader")
        if re.match(r"^[a-z_][a-z0-9_-]{0,31}$", state.username):
            break
        warn("Invalid username. Use lowercase letters, digits, underscore, hyphen (max 32 chars).")

    # User password
    while True:
        pw1 = ask(f"Password for {state.username}", secret=True)
        if not pw1:
            warn("Password cannot be empty.")
            continue
        pw2 = ask("Confirm password", secret=True)
        if pw1 != pw2:
            warn("Passwords do not match.")
            continue
        if len(pw1) < 6:
            warn("Password is very short.")
            if not confirm("Use this password anyway?", default=False):
                continue
        state.password = pw1
        break

    # Root account
    lock_root = confirm(
        "Lock the root account? (sudo via wheel group — recommended for security)",
        default=True
    )
    state.root_locked = lock_root
    if not lock_root:
        rp1 = ask("Root password", secret=True)
        rp2 = ask("Confirm root password", secret=True)
        if rp1 == rp2 and rp1:
            state.root_password = rp1
            info("Root password set.")
        else:
            warn("Root passwords did not match. Root account will be locked.")
            state.root_locked = True

    # SSH key
    ssh_key = ask("SSH public key to install (optional, paste or press Enter to skip)", default="")
    if ssh_key and ssh_key.startswith("ssh-"):
        state.hw["ssh_pubkey"] = ssh_key
        info("SSH public key will be installed.")
    elif ssh_key:
        warn("SSH key doesn't look valid (should start with 'ssh-'). Skipped.")

    base_groups = "wheel,desktop,audio,video,network,trading,research"
    extra_groups = ",".join(PROFILES.get(state.profile, {}).get("groups_extra", []))
    all_groups = f"{base_groups},{extra_groups}" if extra_groups else base_groups
    state.hw["user_groups"] = all_groups
    info(f"User '{state.username}' → groups: {all_groups}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 7: Hostname & Timezone
# ═══════════════════════════════════════════════════════════════════════════════

def phase_hostname_tz(state: InstallState):
    section("PHASE 7  ─  Hostname & Timezone")

    while True:
        state.hostname = ask("System hostname", default="kairos-workstation")
        if re.match(r"^[a-zA-Z0-9][a-zA-Z0-9\-]{0,62}$", state.hostname):
            break
        warn("Invalid hostname. Use letters, digits, hyphens. Max 63 chars. Cannot start with hyphen.")

    info(f"Hostname: {state.hostname}")

    tz_choice = ask_choice("Select timezone", TIMEZONES, default_idx=0)
    state.timezone = tz_choice
    info(f"Timezone: {state.timezone}")


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 8: Install Profile
# ═══════════════════════════════════════════════════════════════════════════════

def phase_profile(state: InstallState):
    section("PHASE 8  ─  Installation Profile")

    profile_list = []
    for name, pdata in PROFILES.items():
        pkg_count = len(pdata["packages"])
        min_gb    = pdata["disk_gb_min"]
        profile_list.append(
            f"{name:<20}  {pdata['description'][:50]}  [{pkg_count} pkgs, ≥{min_gb}GB]"
        )

    default_idx = list(PROFILES.keys()).index("Trader")
    choice = ask_choice("Select installation profile", profile_list, default_idx=default_idx)
    state.profile = choice.split()[0]

    pdata = PROFILES[state.profile]
    info(f"Profile  : {state.profile}")
    info(f"Packages : {len(pdata['packages'])} (base profile)")
    info(f"Services : {', '.join(pdata['services'][:4])}{'...' if len(pdata['services']) > 4 else ''}")
    info(f"Min disk : {pdata['disk_gb_min']} GiB")


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 9: Optional Components
# ═══════════════════════════════════════════════════════════════════════════════

def phase_optional(state: InstallState):
    section("PHASE 9  ─  Optional Components")
    print(f"  {C.DIM}Profile: {state.profile}. Select optional extras to add:{C.RESET}\n")

    selected = []
    for key, desc, pkgs in OPTIONAL_COMPONENTS:
        # Skip if already in profile
        already = key in PROFILES.get(state.profile, {}).get("packages", [])
        if already:
            info(f"  {key:<20} (already included in profile)")
            continue
        if confirm(f"  Add {key:<20}  ({desc})?", default=False):
            selected.append(key)
            info(f"  Added: {key}  ({', '.join(pkgs[:3])})")

    state.optional = selected
    if selected:
        info(f"Optional components: {len(selected)} selected")
    else:
        info("No optional components selected.")


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 10: Summary & Confirmation Gate
# ═══════════════════════════════════════════════════════════════════════════════

def phase_confirm(state: InstallState) -> bool:
    section("PHASE 10  ─  Installation Summary")

    # Count total packages
    base_pkgs = PROFILES[state.profile]["packages"]
    opt_pkgs  = []
    for key in state.optional:
        for name, _, pkgs in OPTIONAL_COMPONENTS:
            if name == key:
                opt_pkgs.extend(pkgs)
    total_pkgs = len(set(base_pkgs + opt_pkgs))

    existing_warning = ""
    if state.existing_sys:
        existing_warning = f"\n  {C.RED}⚠  EXISTING SYSTEMS WILL BE DESTROYED:{C.RESET}"
        for s in state.existing_sys:
            existing_warning += f"\n      - {s['name']} on {s['device']}"

    print(f"""
  {C.BOLD}Installation Configuration{C.RESET}
  ══════════════════════════════════════════════════════
  Language    : {state.language}
  Keyboard    : {state.kb_layout}
  Hostname    : {state.hostname}
  Timezone    : {state.timezone}
  ──────────────────────────────────────────────────────
  Username    : {state.username}
  Root        : {'LOCKED (wheel/sudo only)' if state.root_locked else 'Password set'}
  ──────────────────────────────────────────────────────
  Target Disk : {state.disk or '(none — manual partitioning)'}
  Firmware    : {'UEFI' if state.efi_detected else 'Legacy BIOS'}
  Encryption  : {'✓  LUKS2 AES-256-XTS' if state.encrypt else '✗  DISABLED (plaintext disk!)'}
  TPM2        : {'✓  Will enroll on first boot' if state.tpm2_enroll else '─  Not enrolled'}
  ──────────────────────────────────────────────────────
  Profile     : {state.profile}
  Optional    : {', '.join(state.optional) or 'none'}
  Total pkgs  : ~{total_pkgs} packages
  Network     : {state.network_cfg.get('method', 'unconfigured')}
  ──────────────────────────────────────────────────────
  Dry Run     : {'YES — zero disk changes' if state.dry_run else 'NO — live installation'}
  ══════════════════════════════════════════════════════{existing_warning}
""")

    if not state.disk:
        return confirm("Proceed? (No disk operations will be performed)", default=True)

    if state.dry_run:
        return confirm("Proceed with dry-run installation?", default=True)

    # Actual destructive confirmation
    return confirm_destructive(
        f"Format {state.disk} and install KAIROS OS "
        f"({'LUKS2 encrypted' if state.encrypt else 'unencrypted'})"
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 11: Installation
# ═══════════════════════════════════════════════════════════════════════════════

def phase_install(state: InstallState):
    section("PHASE 11  ─  System Installation")

    steps = [
        ("Partitioning disk",             _step_partition),
        ("Formatting EFI/boot",           _step_format),
        ("Configuring LUKS2 encryption",  _step_luks),
        ("Creating Btrfs & subvolumes",   _step_btrfs),
        ("Mounting filesystems",          _step_mount),
        ("Installing packages",           _step_packages),
        ("Writing /etc/fstab",            _step_fstab),
        ("Configuring hostname",          _step_hostname),
        ("Configuring locale & keyboard", _step_locale),
        ("Configuring timezone",          _step_timezone),
        ("Configuring network",           _step_network_files),
        ("Creating user accounts",        _step_users),
        ("Configuring sudo",              _step_sudo),
        ("Configuring KAIROS groups",     _step_groups),
        ("Writing KAIROS identity",       _step_identity),
        ("Generating initramfs",          _step_initramfs),
        ("Enabling system services",      _step_services),
        ("Writing first-boot config",     _step_firstboot_config),
        ("Unmounting filesystems",        _step_unmount),
    ]

    total = len(steps)
    for i, (desc, fn) in enumerate(steps):
        step_progress(i, total, desc, done=False)
        log.info(f"Step {i+1}/{total}: {desc}")
        try:
            fn(state)
            step_progress(i + 1, total, desc, done=True)
        except Exception as ex:
            print()
            error(f"Step '{desc}' FAILED: {ex}")
            log.error(f"Step failed: {desc}: {ex}", exc_info=True)
            if not confirm(f"Continue anyway?", default=False):
                raise SystemExit(1)

    print(f"\n  {C.GREEN}{C.BOLD}[100%]  Installation complete.{C.RESET}")


# ── Installation steps ──────────────────────────────────────────────────────

def _step_partition(state: InstallState):
    if not state.disk:
        return
    dr = state.dry_run
    if state.efi_detected:
        cmds = [
            ["sgdisk", "--zap-all", state.disk],
            ["sgdisk", "--clear", state.disk],
            ["sgdisk", f"--new=1:0:+1G",   "--typecode=1:ef00",
             "--change-name=1:EFI-SYSTEM",  state.disk],
            ["sgdisk", f"--new=2:0:+2G",   "--typecode=2:8300",
             "--change-name=2:kairos-boot", state.disk],
            ["sgdisk", f"--new=3:0:0",     "--typecode=3:8309",
             "--change-name=3:kairos-root", state.disk],
        ]
    else:
        # BIOS: 2 MiB BIOS boot, 2 GiB /boot, rest for root
        cmds = [
            ["sgdisk", "--zap-all", state.disk],
            ["sgdisk", "--clear", state.disk],
            ["sgdisk", f"--new=1:0:+2M",   "--typecode=1:ef02",
             "--change-name=1:BIOS-BOOT",   state.disk],
            ["sgdisk", f"--new=2:0:+2G",   "--typecode=2:8300",
             "--change-name=2:kairos-boot", state.disk],
            ["sgdisk", f"--new=3:0:0",     "--typecode=3:8309",
             "--change-name=3:kairos-root", state.disk],
        ]
    for cmd in cmds:
        run_cmd(cmd, dry_run=dr)
    if not dr:
        # Inform kernel of new partition table
        run_cmd(["partprobe", state.disk], check=False, dry_run=dr)
        time.sleep(1)  # Allow udev to settle


def _step_format(state: InstallState):
    if not state.disk:
        return
    dr = state.dry_run
    p1 = state.part_efi
    p2 = state.part_boot
    if state.efi_detected:
        run_cmd(["mkfs.fat", "-F32", "-n", "EFI", p1], dry_run=dr)
    run_cmd(["mkfs.ext4", "-F", "-L", "kairos-boot", p2], dry_run=dr)

    if not dr:
        state.uuid_efi  = get_disk_uuid(p1) if state.efi_detected else ""
        state.uuid_boot = get_disk_uuid(p2)


def _step_luks(state: InstallState):
    if not state.disk:
        return
    dr = state.dry_run
    p3 = state.part_root

    if state.encrypt:
        # Format LUKS2 container
        luks_cmd = [
            "cryptsetup", "luksFormat",
            "--type", "luks2",
            "--cipher", "aes-xts-plain64",
            "--key-size", "512",
            "--hash", "sha512",
            "--pbkdf", "argon2id",
            "--pbkdf-memory", "131072",    # 128 MiB
            "--pbkdf-parallel", "4",
            "--batch-mode",
            p3,
        ]
        run_cmd(luks_cmd, dry_run=dr, input_text=state.luks_pass + "\n")
        # Open the container
        run_cmd(
            ["cryptsetup", "open", p3, "kairos-root"],
            dry_run=dr, input_text=state.luks_pass + "\n"
        )
        if not dr:
            state.uuid_root = get_disk_uuid(p3)
    else:
        if not dr:
            state.uuid_root = get_disk_uuid(p3)


def _step_btrfs(state: InstallState):
    if not state.disk:
        return
    dr = state.dry_run
    btrfs_dev = "/dev/mapper/kairos-root" if state.encrypt else state.part_root

    run_cmd(["mkfs.btrfs", "-L", "kairos-root", "-f", btrfs_dev], dry_run=dr)

    # Create subvolumes
    tgt = state.install_target
    run_cmd(["mount", btrfs_dev, tgt], dry_run=dr)
    for sv in ["@", "@home", "@snapshots", "@var_log", "@vault", "@data"]:
        run_cmd(["btrfs", "subvolume", "create", f"{tgt}/{sv}"], dry_run=dr)
    run_cmd(["umount", tgt], dry_run=dr)


def _step_mount(state: InstallState):
    if not state.disk:
        return
    dr = state.dry_run
    tgt = state.install_target
    btrfs_dev = "/dev/mapper/kairos-root" if state.encrypt else state.part_root
    opts = "rw,noatime,compress=zstd:1,space_cache=v2,autodefrag"

    # Root
    run_cmd(["mount", "-o", f"{opts},subvol=@", btrfs_dev, tgt], dry_run=dr)

    # Subvolumes
    submounts = [
        (f"{tgt}/home",              "@home"),
        (f"{tgt}/.snapshots",        "@snapshots"),
        (f"{tgt}/var/log",           "@var_log"),
        (f"{tgt}/var/kairos/vault",  "@vault"),
    ]
    for mp, sv in submounts:
        if not dr:
            os.makedirs(mp, exist_ok=True)
        run_cmd(["mount", "-o", f"{opts},subvol={sv}", btrfs_dev, mp], dry_run=dr)

    # EFI and boot
    if state.efi_detected:
        efi_mp = f"{tgt}/efi"
        if not dr:
            os.makedirs(efi_mp, exist_ok=True)
        run_cmd(["mount", state.part_efi, efi_mp], dry_run=dr)

    boot_mp = f"{tgt}/boot"
    if not dr:
        os.makedirs(boot_mp, exist_ok=True)
    run_cmd(["mount", state.part_boot, boot_mp], dry_run=dr)


def _step_packages(state: InstallState):
    tgt = state.install_target
    profile_pkgs = PROFILES[state.profile]["packages"]

    # Add optional component packages
    opt_pkgs = []
    for key in state.optional:
        for name, _, pkgs in OPTIONAL_COMPONENTS:
            if name == key:
                opt_pkgs.extend(pkgs)

    all_pkgs = list(dict.fromkeys(profile_pkgs + opt_pkgs))  # deduplicate
    info(f"Installing {len(all_pkgs)} packages for profile '{state.profile}'...")
    log.info(f"Package list: {all_pkgs}")

    if not state.dry_run and shutil.which("pacstrap"):
        run_cmd(["pacstrap", "-K", tgt] + all_pkgs, timeout=600)
    elif not state.dry_run and shutil.which("debootstrap"):
        # Debian-family fallback
        run_cmd(["debootstrap", "--arch=amd64", "stable", tgt], timeout=600)
    else:
        log.info(f"DRY-RUN or no package manager: would install {all_pkgs}")


def _step_fstab(state: InstallState):
    tgt = state.install_target
    dr  = state.dry_run

    if not dr and shutil.which("genfstab"):
        result = run_cmd(["genfstab", "-U", tgt], capture=True, dry_run=dr)
        fstab_content = result.stdout
    else:
        # Generate fstab manually
        btrfs_dev = "/dev/mapper/kairos-root" if state.encrypt else state.part_root
        root_uuid = state.uuid_root or "UUID-PLACEHOLDER"
        boot_uuid = state.uuid_boot or "UUID-BOOT-PLACEHOLDER"
        efi_uuid  = state.uuid_efi  or "UUID-EFI-PLACEHOLDER"
        opts = "rw,noatime,compress=zstd:1,space_cache=v2,autodefrag"

        lines = [
            "# /etc/fstab — generated by KAIROS installer",
            f"# Generated: {datetime.datetime.utcnow().isoformat()}Z",
            "",
        ]
        if state.encrypt:
            lines += [
                f"# Root (LUKS2 encrypted Btrfs)",
                f"/dev/mapper/kairos-root  /            btrfs  {opts},subvol=@            0 0",
                f"/dev/mapper/kairos-root  /home        btrfs  {opts},subvol=@home        0 0",
                f"/dev/mapper/kairos-root  /.snapshots  btrfs  {opts},subvol=@snapshots   0 0",
                f"/dev/mapper/kairos-root  /var/log     btrfs  {opts},subvol=@var_log     0 0",
                f"/dev/mapper/kairos-root  /var/kairos/vault  btrfs  {opts},subvol=@vault  0 0",
                "",
            ]
        else:
            lines += [
                f"UUID={root_uuid}  /            btrfs  {opts},subvol=@            0 0",
                f"UUID={root_uuid}  /home        btrfs  {opts},subvol=@home        0 0",
                f"UUID={root_uuid}  /.snapshots  btrfs  {opts},subvol=@snapshots   0 0",
                f"UUID={root_uuid}  /var/log     btrfs  {opts},subvol=@var_log     0 0",
                "",
            ]
        lines += [
            f"UUID={boot_uuid}  /boot   ext4   rw,relatime   1 2",
        ]
        if state.efi_detected:
            lines += [
                f"UUID={efi_uuid}   /efi    vfat   rw,relatime,fmask=0022,dmask=0022,codepage=437,iocharset=iso8859-1,shortname=mixed,utf8,errors=remount-ro  0 2",
            ]
        lines += ["", "# tmpfs", "tmpfs  /tmp  tmpfs  defaults,noatime,mode=1777  0 0", ""]
        fstab_content = "\n".join(lines)

    fstab_path = os.path.join(tgt, "etc", "fstab")
    if not dr:
        os.makedirs(os.path.dirname(fstab_path), exist_ok=True)
        with open(fstab_path, "w") as f:
            f.write(fstab_content)
    else:
        log.info(f"DRY-RUN: would write fstab:\n{fstab_content}")


def _step_hostname(state: InstallState):
    tgt = state.install_target
    dr  = state.dry_run
    if dr:
        return

    hostname_path = os.path.join(tgt, "etc", "hostname")
    hosts_path    = os.path.join(tgt, "etc", "hosts")
    os.makedirs(os.path.dirname(hostname_path), exist_ok=True)

    with open(hostname_path, "w") as f:
        f.write(state.hostname + "\n")

    with open(hosts_path, "w") as f:
        f.write(
            f"# /etc/hosts — KAIROS OS\n"
            f"127.0.0.1  localhost\n"
            f"::1        localhost\n"
            f"127.0.1.1  {state.hostname}.localdomain  {state.hostname}\n"
        )


def _step_locale(state: InstallState):
    tgt = state.install_target
    dr  = state.dry_run
    if dr:
        return

    # /etc/locale.gen
    locale_gen = os.path.join(tgt, "etc", "locale.gen")
    os.makedirs(os.path.dirname(locale_gen), exist_ok=True)
    with open(locale_gen, "w") as f:
        f.write(f"{state.language} UTF-8\n")
        if not state.language.startswith("en_US"):
            f.write("en_US.UTF-8 UTF-8\n")

    # /etc/locale.conf
    locale_conf = os.path.join(tgt, "etc", "locale.conf")
    with open(locale_conf, "w") as f:
        f.write(f"LANG={state.language}\n")
        f.write(f"LC_COLLATE=C\n")

    # /etc/vconsole.conf  (keyboard in console)
    vconsole = os.path.join(tgt, "etc", "vconsole.conf")
    with open(vconsole, "w") as f:
        f.write(f"KEYMAP={state.kb_layout}\n")
        f.write(f"FONT=ter-132n\n")

    # Run locale-gen inside chroot
    chroot_run(["locale-gen"], check=False, dry_run=dr, target=tgt)


def _step_timezone(state: InstallState):
    tgt = state.install_target
    dr  = state.dry_run
    if dr:
        return

    zoneinfo_src = f"/usr/share/zoneinfo/{state.timezone}"
    localtime    = os.path.join(tgt, "etc", "localtime")

    # Try to create symlink via chroot
    chroot_run(
        ["ln", "-sf", f"/usr/share/zoneinfo/{state.timezone}", "/etc/localtime"],
        check=False, dry_run=dr, target=tgt
    )
    # Fallback: write /etc/timezone
    tz_path = os.path.join(tgt, "etc", "timezone")
    try:
        with open(tz_path, "w") as f:
            f.write(state.timezone + "\n")
    except Exception:
        pass


def _step_network_files(state: InstallState):
    tgt    = state.install_target
    dr     = state.dry_run
    method = state.network_cfg.get("method", "skip")
    iface  = state.network_cfg.get("interface", "eth0")

    if method == "skip" or dr:
        return

    # systemd-networkd configuration
    net_dir = os.path.join(tgt, "etc", "systemd", "network")
    os.makedirs(net_dir, exist_ok=True)

    net_file = os.path.join(net_dir, f"10-{iface}.network")

    if method == "dhcp":
        content = (
            f"[Match]\nName={iface}\n\n"
            f"[Network]\nDHCP=yes\nIPv6AcceptRA=yes\n\n"
            f"[DHCPv4]\nRouteMetric=100\n"
        )
    else:
        dns_list = state.network_cfg.get("dns", ["1.1.1.1", "8.8.8.8"])
        dns_entries = "\n".join(f"DNS={d}" for d in dns_list)
        content = (
            f"[Match]\nName={iface}\n\n"
            f"[Network]\n"
            f"Address={state.network_cfg['address']}\n"
            f"Gateway={state.network_cfg['gateway']}\n"
            f"{dns_entries}\n"
        )

    with open(net_file, "w") as f:
        f.write(content)

    # NetworkManager fallback for desktop profiles
    if state.profile in ("Trader", "Quant Research", "Developer", "Full"):
        nm_dir = os.path.join(tgt, "etc", "NetworkManager", "system-connections")
        os.makedirs(nm_dir, exist_ok=True)


def _step_users(state: InstallState):
    tgt = state.install_target
    dr  = state.dry_run

    # All groups must exist first
    groups = [
        "wheel", "desktop", "audio", "video", "network",
        "trading", "research", "plugins", "docker",
        "kairos-risk", "kairos-feed", "kairos-agent", "kairos-plugin",
    ]
    for grp in groups:
        chroot_run(["groupadd", "-f", grp], check=False, dry_run=dr, target=tgt)

    # Create primary user
    user_groups = state.hw.get("user_groups", "wheel,desktop,audio,video,network")
    chroot_run(
        ["useradd", "-m", "-G", user_groups, "-s", "/bin/bash", state.username],
        check=False, dry_run=dr, target=tgt
    )

    # Set password
    if state.password and not dr:
        chroot_run(
            ["chpasswd"],
            check=False, dry_run=dr, target=tgt,
            input_text=f"{state.username}:{state.password}\n"
        )

    # Root account
    if state.root_locked:
        chroot_run(["passwd", "-l", "root"], check=False, dry_run=dr, target=tgt)
    elif state.root_password:
        chroot_run(
            ["chpasswd"],
            check=False, dry_run=dr, target=tgt,
            input_text=f"root:{state.root_password}\n"
        )

    # SSH authorized_keys
    ssh_key = state.hw.get("ssh_pubkey", "")
    if ssh_key and not dr:
        ssh_dir  = os.path.join(tgt, "home", state.username, ".ssh")
        os.makedirs(ssh_dir, mode=0o700, exist_ok=True)
        auth_keys = os.path.join(ssh_dir, "authorized_keys")
        with open(auth_keys, "w") as f:
            f.write(ssh_key + "\n")
        os.chmod(auth_keys, 0o600)

    # Create KAIROS service accounts
    service_accounts = [
        ("kairos-risk",   990, 1003, "KAIROS Risk Gatekeeper"),
        ("kairos-feed",   991, 1020, "KAIROS Market Feed Handler"),
        ("kairos-agent",  992, 1021, "KAIROS AI Agent Runner"),
        ("kairos-plugin", 993, 1022, "KAIROS Plugin Sandbox"),
    ]
    for svc_name, uid, gid, desc in service_accounts:
        chroot_run(
            ["useradd", "-r", "-u", str(uid), "-g", str(gid),
             "-s", "/sbin/nologin", "-d", "/dev/null",
             "-c", desc, svc_name],
            check=False, dry_run=dr, target=tgt
        )


def _step_sudo(state: InstallState):
    tgt = state.install_target
    dr  = state.dry_run
    if dr:
        return

    sudoers_d = os.path.join(tgt, "etc", "sudoers.d")
    os.makedirs(sudoers_d, mode=0o750, exist_ok=True)

    wheel_rule = os.path.join(sudoers_d, "10-wheel")
    with open(wheel_rule, "w") as f:
        f.write(
            "# KAIROS OS: wheel group members can sudo with password\n"
            "%wheel ALL=(ALL:ALL) ALL\n"
        )
    os.chmod(wheel_rule, 0o440)

    kairos_rule = os.path.join(sudoers_d, "20-kairos-services")
    with open(kairos_rule, "w") as f:
        f.write(
            "# KAIROS service accounts — restricted privilege escalation\n"
            "kairos-risk   ALL=(ALL) NOPASSWD: /usr/libexec/kairos/risk-escalate\n"
        )
    os.chmod(kairos_rule, 0o440)


def _step_groups(state: InstallState):
    """Write /etc/security/limits.d rules for KAIROS groups."""
    tgt = state.install_target
    dr  = state.dry_run
    if dr:
        return

    limits_d = os.path.join(tgt, "etc", "security", "limits.d")
    os.makedirs(limits_d, exist_ok=True)

    kairos_limits = os.path.join(limits_d, "10-kairos.conf")
    with open(kairos_limits, "w") as f:
        f.write(
            "# KAIROS OS resource limits\n\n"
            "# Real-time trading — low latency\n"
            "@trading    soft  rtprio      99\n"
            "@trading    hard  rtprio      99\n"
            "@trading    soft  memlock     unlimited\n"
            "@trading    hard  memlock     unlimited\n"
            "@trading    soft  nofile      1048576\n"
            "@trading    hard  nofile      1048576\n\n"
            "# Research — large datasets\n"
            "@research   soft  memlock     unlimited\n"
            "@research   hard  memlock     unlimited\n"
            "@research   soft  nofile      524288\n"
            "@research   hard  nofile      524288\n\n"
            "# Plugin sandbox — throttled\n"
            "@plugins    soft  rtprio      0\n"
            "@plugins    hard  rtprio      0\n"
            "@plugins    soft  nproc       1024\n"
            "@plugins    hard  nproc       1024\n"
            "@plugins    soft  nofile      8192\n"
            "@plugins    hard  nofile      8192\n"
        )


def _step_identity(state: InstallState):
    """Write /etc/os-release, /etc/kairos/system.toml, and machine-id."""
    tgt = state.install_target
    dr  = state.dry_run
    if dr:
        return

    build_date = datetime.datetime.utcnow().strftime("%Y%m%d")

    # /etc/os-release
    osrel_path = os.path.join(tgt, "etc", "os-release")
    os.makedirs(os.path.dirname(osrel_path), exist_ok=True)
    with open(osrel_path, "w") as f:
        f.write(
            f'NAME="KAIROS OS"\n'
            f'PRETTY_NAME="KAIROS OS {KAIROS_VERSION} ({KAIROS_CODENAME})"\n'
            f'ID=kairos\n'
            f'ID_LIKE=arch\n'
            f'VERSION_ID={KAIROS_VERSION}\n'
            f'VERSION="{KAIROS_VERSION} ({KAIROS_CODENAME})"\n'
            f'VERSION_CODENAME={KAIROS_CODENAME.lower()}\n'
            f'BUILD_ID={build_date}\n'
            f'ANSI_COLOR="1;36"\n'
            f'HOME_URL="https://kairos-os.org"\n'
            f'SUPPORT_URL="https://kairos-os.org/support"\n'
            f'BUG_REPORT_URL="https://github.com/kairos-os/kairos/issues"\n'
            f'LOGO="kairos"\n'
        )

    # /etc/kairos/system.toml — KAIROS system identity
    kairos_etc = os.path.join(tgt, "etc", "kairos")
    os.makedirs(kairos_etc, exist_ok=True)
    system_toml = os.path.join(kairos_etc, "system.toml")
    with open(system_toml, "w") as f:
        f.write(
            f"# KAIROS OS System Configuration\n"
            f"# Generated by installer {INSTALLER_VERSION}\n\n"
            f"[system]\n"
            f'hostname = "{state.hostname}"\n'
            f'timezone = "{state.timezone}"\n'
            f'locale   = "{state.language}"\n'
            f'keyboard = "{state.kb_layout}"\n'
            f'profile  = "{state.profile}"\n'
            f"encrypted = {'true' if state.encrypt else 'false'}\n"
            f'installed_at = "{datetime.datetime.utcnow().isoformat()}Z"\n\n'
            f"[invariants]\n"
            f"hard_risk_gatekeeper   = true\n"
            f"audit_isolation        = true\n"
            f"independent_os_stability = true\n\n"
            f"[components]\n"
            f'profile  = "{state.profile}"\n'
            f'optional = {json.dumps(state.optional)}\n'
        )

    # /etc/machine-id  (systemd will accept an empty one and fill it in)
    mid_path = os.path.join(tgt, "etc", "machine-id")
    if not os.path.exists(mid_path):
        try:
            with open(mid_path, "w") as f:
                f.write("")  # systemd-firstboot will populate this
        except Exception:
            pass


def _step_initramfs(state: InstallState):
    tgt = state.install_target
    dr  = state.dry_run

    if state.encrypt:
        # Ensure the correct mkinitcpio hooks are present
        mkinit_conf = os.path.join(tgt, "etc", "mkinitcpio.conf")
        if not dr and os.path.exists(mkinit_conf):
            try:
                with open(mkinit_conf) as f:
                    content = f.read()
                # Ensure encrypt hook is present
                if "encrypt" not in content:
                    content = content.replace(
                        "HOOKS=(base udev autodetect modconf kms keyboard keymap consolefont block filesystems fsck)",
                        "HOOKS=(base udev autodetect modconf kms keyboard keymap consolefont block encrypt btrfs filesystems fsck)"
                    )
                    with open(mkinit_conf, "w") as f:
                        f.write(content)
            except Exception as e:
                log.warning(f"Could not update mkinitcpio.conf: {e}")

    chroot_run(["mkinitcpio", "-P"], check=False, dry_run=dr, target=tgt)


def _step_services(state: InstallState):
    tgt       = state.install_target
    dr        = state.dry_run
    svcs      = PROFILES[state.profile]["services"]
    base_svcs = ["systemd-timesyncd", "systemd-resolved"]
    all_svcs  = list(dict.fromkeys(svcs + base_svcs))

    for svc in all_svcs:
        chroot_run(
            ["systemctl", "enable", svc],
            check=False, dry_run=dr, target=tgt
        )

    # Enable first-boot service
    chroot_run(
        ["systemctl", "enable", "kairos-firstboot.service"],
        check=False, dry_run=dr, target=tgt
    )
    log.info(f"Enabled services: {all_svcs}")


def _step_firstboot_config(state: InstallState):
    """Write the first-boot JSON config that kairos-firstboot.service reads."""
    tgt = state.install_target
    dr  = state.dry_run

    fb_path = os.path.join(tgt, "etc", "kairos", "first-boot.json")
    fb_data = {
        "username":           state.username,
        "hostname":           state.hostname,
        "timezone":           state.timezone,
        "language":           state.language,
        "keyboard":           state.kb_layout,
        "profile":            state.profile,
        "optional_components": state.optional,
        "network_method":     state.network_cfg.get("method", "dhcp"),
        "encrypt":            state.encrypt,
        "tpm2_enroll":        state.tpm2_enroll,
        "root_locked":        state.root_locked,
        "first_boot_complete": False,
        "installer_version":  INSTALLER_VERSION,
        "kairos_version":     KAIROS_VERSION,
        "installed_at":       datetime.datetime.utcnow().isoformat() + "Z",
    }

    if not dr:
        os.makedirs(os.path.dirname(fb_path), exist_ok=True)
        with open(fb_path, "w") as f:
            json.dump(fb_data, f, indent=2)

    log.info(f"First-boot config: {fb_data}")


def _step_unmount(state: InstallState):
    """Safely unmount all filesystems in reverse order."""
    tgt = state.install_target
    dr  = state.dry_run
    if not state.disk or dr:
        return

    submounts = [
        f"{tgt}/efi",
        f"{tgt}/boot",
        f"{tgt}/var/kairos/vault",
        f"{tgt}/var/log",
        f"{tgt}/.snapshots",
        f"{tgt}/home",
    ]
    for mp in submounts:
        if os.path.ismount(mp):
            run_cmd(["umount", mp], check=False, dry_run=dr)

    if os.path.ismount(tgt):
        run_cmd(["umount", "-R", tgt], check=False, dry_run=dr)

    if state.encrypt:
        run_cmd(["cryptsetup", "close", "kairos-root"], check=False, dry_run=dr)


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 12: Bootloader Installation
# ═══════════════════════════════════════════════════════════════════════════════

def phase_bootloader(state: InstallState):
    section("PHASE 12  ─  Bootloader Installation")

    tgt = state.install_target
    dr  = state.dry_run

    # Re-mount if unmounted during installation (for bootloader writing)
    if state.disk and not dr:
        btrfs_dev = "/dev/mapper/kairos-root" if state.encrypt else state.part_root
        opts = "rw,noatime,compress=zstd:1,space_cache=v2"
        if not os.path.ismount(tgt):
            run_cmd(["mount", "-o", f"{opts},subvol=@", btrfs_dev, tgt],
                    check=False, dry_run=dr)
            if state.efi_detected:
                run_cmd(["mount", state.part_efi, f"{tgt}/efi"], check=False, dry_run=dr)
            run_cmd(["mount", state.part_boot, f"{tgt}/boot"], check=False, dry_run=dr)

    # Get root UUID for kernel cmdline
    root_uuid = state.uuid_root or (get_disk_uuid(state.part_root) if state.disk else "UNKNOWN-UUID")

    if state.efi_detected:
        _install_systemd_boot(state, tgt, root_uuid, dr)
    else:
        _install_grub2_bios(state, tgt, root_uuid, dr)

    # Re-unmount after bootloader
    if state.disk and not dr and os.path.ismount(tgt):
        run_cmd(["umount", "-R", tgt], check=False, dry_run=dr)
        if state.encrypt:
            run_cmd(["cryptsetup", "close", "kairos-root"], check=False, dry_run=dr)


def _install_systemd_boot(state: InstallState, tgt: str, root_uuid: str, dr: bool):
    """Install systemd-boot as the UEFI bootloader."""
    info("Bootloader: systemd-boot (UEFI)")

    chroot_run(["bootctl", "--esp-path=/efi", "install"],
               check=False, dry_run=dr, target=tgt)

    # Loader configuration
    loader_dir = os.path.join(tgt, "efi", "loader")
    entries_dir = os.path.join(loader_dir, "entries")
    if not dr:
        os.makedirs(entries_dir, exist_ok=True)

        # loader.conf
        with open(os.path.join(loader_dir, "loader.conf"), "w") as f:
            f.write(
                "default  kairos.conf\n"
                "timeout  10\n"
                "console-mode max\n"
                "editor   no\n"
            )

    # Build kernel options
    if state.encrypt:
        root_opts = (
            f"rd.luks.name={root_uuid}=kairos-root "
            f"root=/dev/mapper/kairos-root rootflags=subvol=@"
        )
    else:
        root_opts = f"root=UUID={root_uuid} rootflags=subvol=@"

    common_opts = f"rw quiet splash kairos.mode=normal"
    recovery_opts = f"rw single nomodeset kairos.mode=recovery"

    # Normal boot entry
    normal_entry = (
        f"title   KAIROS OS {KAIROS_VERSION}\n"
        f"linux   /vmlinuz-kairos\n"
        f"initrd  /intel-ucode.img\n"
        f"initrd  /amd-ucode.img\n"
        f"initrd  /initramfs-kairos.img\n"
        f"options {root_opts} {common_opts}\n"
    )

    # Fallback boot entry
    fallback_entry = (
        f"title   KAIROS OS {KAIROS_VERSION} (Safe Boot)\n"
        f"linux   /vmlinuz-kairos\n"
        f"initrd  /initramfs-kairos-fallback.img\n"
        f"options {root_opts} rw nomodeset kairos.mode=normal\n"
    )

    # Recovery entry
    recovery_entry = (
        f"title   KAIROS OS Recovery Environment\n"
        f"linux   /vmlinuz-kairos\n"
        f"initrd  /initramfs-kairos-fallback.img\n"
        f"options {root_opts} {recovery_opts}\n"
    )

    if not dr:
        for fname, content in [
            ("kairos.conf",          normal_entry),
            ("kairos-safe.conf",     fallback_entry),
            ("kairos-recovery.conf", recovery_entry),
        ]:
            try:
                with open(os.path.join(entries_dir, fname), "w") as f:
                    f.write(content)
            except Exception as e:
                log.warning(f"Could not write {fname}: {e}")
    else:
        log.info(f"DRY-RUN: would write boot entries:\n{normal_entry}")

    info("systemd-boot: Normal + Safe + Recovery entries written.")


def _install_grub2_bios(state: InstallState, tgt: str, root_uuid: str, dr: bool):
    """Install GRUB2 for Legacy BIOS systems."""
    info("Bootloader: GRUB2 (Legacy BIOS)")

    chroot_run(
        ["grub-install", "--target=i386-pc", "--recheck", state.disk],
        check=False, dry_run=dr, target=tgt
    )

    # Write custom GRUB defaults
    grub_default = os.path.join(tgt, "etc", "default", "grub")
    if not dr:
        os.makedirs(os.path.dirname(grub_default), exist_ok=True)
        if state.encrypt:
            cryptdevice = f"cryptdevice=UUID={root_uuid}:kairos-root"
            root_opts   = f"root=/dev/mapper/kairos-root rootflags=subvol=@"
        else:
            cryptdevice = ""
            root_opts   = f"root=UUID={root_uuid} rootflags=subvol=@"

        with open(grub_default, "w") as f:
            f.write(
                f'GRUB_DEFAULT=0\n'
                f'GRUB_TIMEOUT=10\n'
                f'GRUB_DISTRIBUTOR="KAIROS OS"\n'
                f'GRUB_CMDLINE_LINUX_DEFAULT="quiet splash {cryptdevice}"\n'
                f'GRUB_CMDLINE_LINUX="{root_opts} rw"\n'
                f'GRUB_ENABLE_CRYPTODISK={"y" if state.encrypt else "n"}\n'
            )

    chroot_run(
        ["grub-mkconfig", "-o", "/boot/grub/grub.cfg"],
        check=False, dry_run=dr, target=tgt
    )
    info("GRUB2: configuration generated.")


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 13: Post-Install Health Check
# ═══════════════════════════════════════════════════════════════════════════════

def phase_health_check(state: InstallState) -> int:
    section("PHASE 13  ─  Installation Health Check")

    tgt      = state.install_target
    dr       = state.dry_run
    failures = 0
    warnings = 0

    def check(name: str, condition, critical: bool = True) -> bool:
        nonlocal failures, warnings
        try:
            result = condition() if callable(condition) else bool(condition)
        except Exception as e:
            result = False
            log.warning(f"Health check exception: {name}: {e}")

        if result:
            info(f"  {name}")
        elif critical:
            error(f"  {name}")
            failures += 1
        else:
            warn(f"  {name}")
            warnings += 1
        return result

    # ── Configuration checks ─────────────────────────────────
    check("Language configured",  lambda: bool(state.language))
    check("Keyboard configured",  lambda: bool(state.kb_layout))
    check("Hostname configured",  lambda: bool(state.hostname))
    check("Timezone configured",  lambda: bool(state.timezone))
    check("Username configured",  lambda: bool(state.username))
    check("Profile selected",     lambda: state.profile in PROFILES)
    check("Network configured",   lambda: bool(state.network_cfg.get("method")))
    check("Install log present",  lambda: os.path.exists(LOG_FILE))

    # ── Disk & filesystem checks (only if disk was selected) ─
    if state.disk and not dr:
        check("EFI partition exists",
              lambda: os.path.exists(state.part_efi) if state.efi_detected else True)
        check("Boot partition exists",
              lambda: os.path.exists(state.part_boot))
        check("Root partition exists",
              lambda: os.path.exists(state.part_root))
        check("/etc/fstab generated",
              lambda: os.path.exists(os.path.join(tgt, "etc", "fstab")) and
                      os.path.getsize(os.path.join(tgt, "etc", "fstab")) > 20)
        check("/etc/hostname written",
              lambda: os.path.exists(os.path.join(tgt, "etc", "hostname")))
        check("/etc/os-release written",
              lambda: os.path.exists(os.path.join(tgt, "etc", "os-release")))
        check("/etc/kairos/system.toml written",
              lambda: os.path.exists(os.path.join(tgt, "etc", "kairos", "system.toml")))
        check("/etc/kairos/first-boot.json written",
              lambda: os.path.exists(os.path.join(tgt, "etc", "kairos", "first-boot.json")))
        check("/etc/locale.conf written",
              lambda: os.path.exists(os.path.join(tgt, "etc", "locale.conf")))
        check("/etc/vconsole.conf written",
              lambda: os.path.exists(os.path.join(tgt, "etc", "vconsole.conf")))
        check("sudoers.d/10-wheel written",
              lambda: os.path.exists(os.path.join(tgt, "etc", "sudoers.d", "10-wheel")))
        check("limits.d/10-kairos.conf written",
              lambda: os.path.exists(os.path.join(tgt, "etc", "security", "limits.d", "10-kairos.conf")))

        # Bootloader check
        if state.efi_detected:
            bootentry = os.path.join(tgt, "efi", "loader", "entries", "kairos.conf")
            check("systemd-boot entry written",
                  lambda: os.path.exists(bootentry), critical=False)
        else:
            grub_cfg = os.path.join(tgt, "boot", "grub", "grub.cfg")
            check("GRUB2 config generated",
                  lambda: os.path.exists(grub_cfg), critical=False)

    # ── LUKS check ────────────────────────────────────────────
    if state.encrypt and state.disk and not dr:
        check("LUKS2 container open (/dev/mapper/kairos-root)",
              lambda: os.path.exists("/dev/mapper/kairos-root"), critical=False)

    # ── Encryption disabled warning ───────────────────────────
    if not state.encrypt:
        warn("Disk encryption is DISABLED. Physical access = full data access.")

    # ── Summary ───────────────────────────────────────────────
    print()
    if failures == 0 and warnings == 0:
        info(f"Health check: ALL PASSED")
    elif failures == 0:
        warn(f"Health check: PASSED with {warnings} advisory warning(s).")
    else:
        error(f"Health check: {failures} CRITICAL failure(s), {warnings} warning(s).")
        warn("The installation may not boot correctly.")

    state.save_manifest()
    info(f"Install manifest : /tmp/kairos-install-manifest.json")
    info(f"Install log      : {LOG_FILE}")
    return failures


# ═══════════════════════════════════════════════════════════════════════════════
#  PHASE 14: First Boot Preparation
# ═══════════════════════════════════════════════════════════════════════════════

def phase_first_boot(state: InstallState, health_failures: int):
    section("PHASE 14  ─  First Boot Preparation")

    tgt = state.install_target
    dr  = state.dry_run

    # Write first-boot systemd service to target
    service_content = (
        "[Unit]\n"
        "Description=KAIROS OS First Boot Setup\n"
        "After=network.target systemd-resolved.service\n"
        "ConditionPathExists=/etc/kairos/first-boot.json\n"
        "ConditionPathExists=!/etc/kairos/.first-boot-done\n\n"
        "[Service]\n"
        "Type=oneshot\n"
        "RemainAfterExit=yes\n"
        "ExecStart=/usr/libexec/kairos/kairos-firstboot\n"
        "ExecStartPost=/bin/touch /etc/kairos/.first-boot-done\n"
        "ExecStartPost=/bin/systemctl disable kairos-firstboot.service\n"
        "StandardOutput=journal+console\n"
        "StandardError=journal+console\n\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
    )

    service_path = os.path.join(tgt, "etc", "systemd", "system", "kairos-firstboot.service")
    if not dr:
        os.makedirs(os.path.dirname(service_path), exist_ok=True)
        try:
            with open(service_path, "w") as f:
                f.write(service_content)
        except Exception as e:
            log.warning(f"Could not write first-boot service: {e}")

    # Write the first-boot helper script
    firstboot_script = os.path.join(tgt, "usr", "libexec", "kairos", "kairos-firstboot")
    firstboot_content = f"""#!/usr/bin/env python3
\"\"\"
KAIROS OS First Boot Setup Script
Run once on first boot to complete system initialization.
\"\"\"
import json, os, subprocess, sys

CFG = "/etc/kairos/first-boot.json"

def run(cmd, check=False):
    return subprocess.run(cmd, capture_output=True, text=True, check=check)

def main():
    try:
        with open(CFG) as f:
            cfg = json.load(f)
    except Exception as e:
        print(f"First boot: could not read config: {{e}}")
        return 1

    print("KAIROS OS — First Boot Initialization")

    # 1. Set machine-id
    run(["systemd-machine-id-setup"])

    # 2. Set timezone symlink
    tz = cfg.get("timezone", "UTC")
    run(["ln", "-sf", f"/usr/share/zoneinfo/{{tz}}", "/etc/localtime"])

    # 3. Generate locale
    run(["locale-gen"])

    # 4. Sync hardware clock
    run(["hwclock", "--systohc"])

    # 5. Regenerate SSH host keys
    for key_type in ["rsa", "ecdsa", "ed25519"]:
        key_path = f"/etc/ssh/ssh_host_{{key_type}}_key"
        if not os.path.exists(key_path):
            run(["ssh-keygen", "-t", key_type, "-f", key_path, "-N", ""])

    # 6. TPM2 enrollment (if requested)
    if cfg.get("tpm2_enroll") and os.path.exists("/dev/tpm0"):
        run(["systemd-cryptenroll", "--tpm2-device=auto", "--tpm2-pcrs=0+7",
             "/dev/disk/by-partlabel/kairos-root"])

    # 7. Mark first boot complete
    with open("/etc/kairos/first-boot.json", "w") as f:
        cfg["first_boot_complete"] = True
        json.dump(cfg, f, indent=2)

    print("KAIROS OS first boot complete.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""

    if not dr:
        os.makedirs(os.path.dirname(firstboot_script), exist_ok=True)
        try:
            with open(firstboot_script, "w") as f:
                f.write(firstboot_content)
            os.chmod(firstboot_script, 0o755)
        except Exception as e:
            log.warning(f"Could not write first-boot script: {e}")

    # Print completion banner
    status_line = (f"  {C.GREEN}{C.BOLD}Installation Successful{C.RESET}"
                   if health_failures == 0
                   else f"  {C.YELLOW}{C.BOLD}Installation Complete (with warnings){C.RESET}")

    print(f"""
  {C.CYAN}╔══════════════════════════════════════════════════════════════╗
  ║          KAIROS OS  ─  Installation Complete                 ║
  ╚══════════════════════════════════════════════════════════════╝{C.RESET}

  {status_line}

  {C.BOLD}First boot sequence:{C.RESET}
   1. Remove installation media
   2. Reboot the system
   3. Select 'KAIROS OS {KAIROS_VERSION}' in the boot menu
   {f'4. Enter LUKS2 passphrase when prompted' if state.encrypt else ''}
   5. First-boot setup runs automatically (~30 seconds)
   6. Log in as '{state.username}'

  {C.BOLD}Recovery access:{C.RESET}
   • Boot menu → 'KAIROS OS Recovery Environment'
   • Emergency : append 'single' to kernel command line
   • CLI       : kairos recovery menu

  {C.BOLD}Artifacts:{C.RESET}
   • Install log      : {LOG_FILE}
   • Install manifest : /tmp/kairos-install-manifest.json
   • First-boot cfg   : {tgt}/etc/kairos/first-boot.json

  {C.DIM}Installer session log has been saved. Remove install media and reboot.{C.RESET}
""")


# ═══════════════════════════════════════════════════════════════════════════════
#  Main Installer Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

def _sigint_handler(sig, frame):
    print(f"\n\n  {C.YELLOW}Installation interrupted by user (Ctrl+C).{C.RESET}")
    print(f"  No destructive disk changes were made without explicit confirmation.")
    print(f"  Partial log: {LOG_FILE}")
    sys.exit(130)

def main() -> int:
    signal.signal(signal.SIGINT, _sigint_handler)

    # ── CLI arguments ────────────────────────────────────────
    args = sys.argv[1:]
    dry_run = "--dry-run" in args or "-n" in args
    auto    = "--auto"    in args   # headless testing mode

    if "--help" in args or "-h" in args:
        print(f"""
KAIROS OS Installer v{INSTALLER_VERSION}

Usage:
  kairos-install             Interactive installation
  kairos-install --dry-run   Dry run — no disk changes
  kairos-install --auto      Headless with defaults (testing)

Profiles: {', '.join(PROFILES.keys())}

Log: {LOG_FILE}
""")
        return 0

    banner()

    if dry_run:
        print(f"  {C.YELLOW}{C.BOLD}DRY-RUN MODE{C.RESET}{C.YELLOW} — No disk changes will be made.{C.RESET}\n")

    print(f"  {C.DIM}Installation log: {LOG_FILE}{C.RESET}\n")
    log.info(f"KAIROS Installer {INSTALLER_VERSION} starting. dry_run={dry_run} auto={auto}")

    state = InstallState()
    state.dry_run = dry_run

    # ── Auto mode defaults (for testing) ─────────────────────
    if auto:
        state.language    = "en_US.UTF-8"
        state.kb_layout   = "us"
        state.hostname    = "kairos-test"
        state.timezone    = "UTC"
        state.username    = "trader"
        state.password    = "kairos123"
        state.root_locked = True
        state.profile     = "Minimal"
        state.encrypt     = False
        state.network_cfg = {"method": "dhcp", "interface": "eth0"}
        state.dry_run     = True
        log.info("Auto mode: using test defaults with dry_run=True")

    health_failures = 0

    try:
        if not auto:
            block_devs = phase_hardware(state)
            phase_language(state)
            phase_keyboard(state)
            phase_network(state)
            phase_disk(state, block_devs)
            phase_encryption(state)
            phase_user(state)
            phase_hostname_tz(state)
            phase_profile(state)
            phase_optional(state)

            if not phase_confirm(state):
                print(f"\n  {C.YELLOW}Installation aborted by user.{C.RESET}\n")
                log.info("Aborted at confirmation step.")
                return 0
        else:
            # Auto: still detect hardware
            block_devs = phase_hardware(state)
            info("Auto mode: skipping interactive phases.")

        # ── Execute ─────────────────────────────────────────
        phase_install(state)
        phase_bootloader(state)
        health_failures = phase_health_check(state)
        phase_first_boot(state, health_failures)

    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 1
        log.info(f"Installer SystemExit: {code}")
        return code
    except KeyboardInterrupt:
        print(f"\n  {C.YELLOW}Interrupted.{C.RESET}")
        return 130
    except Exception as e:
        error(f"Fatal installer error: {e}")
        log.critical(f"Fatal: {e}", exc_info=True)
        print(f"\n  {C.RED}Installation failed. Full log: {LOG_FILE}{C.RESET}\n")
        return 1

    log.info("KAIROS installation completed successfully.")
    return 0 if health_failures == 0 else 2

if __name__ == "__main__":
    sys.exit(main())
