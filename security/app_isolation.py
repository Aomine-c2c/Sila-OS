#!/usr/bin/env python3
"""
KAIROS Application Isolation Framework & Security Sandbox Engine
Enforces multi-layer sandbox boundaries across:
  - Filesystem access (Landlock / Mount namespaces / Read-Only binds)
  - Network access (Network namespaces / nftables filtering)
  - Device access (Device cgroups / minimal /dev devnodes)
  - Credentials & Secrets (TPM2 hardware vault / No broker keys in user-space)
  - IPC restrictions (Dedicated UNIX sockets / abstract namespace isolation)
  - System call filtering (Seccomp-BPF whitelist)
  - Process isolation (PID namespaces / cgroups v2 / NoNewPrivileges)

Classification Tiers:
  1. TRUSTED_SYSTEM    : Core daemons (kairos-sysd, kairos-riskd). Audited, hardware-locked.
  2. NORMAL_APP        : Standard user desktop tools (Kitty, Waybar, Text Editor).
  3. UNTRUSTED_APP     : 3rd-party charting tools, web browsers. Sandboxed via Flatpak/bwrap.
  4. PLUGIN            : In-process or sidecar algorithmic strategy plugins. Capability-gated.
  5. AI_TOOL           : Autonomous reasoning agents (kairos-agentd). Advisory-only sandbox.

INVARIANT:
A plugin or AI tool can NEVER automatically gain:
  - Broker API credentials / private keys
  - Root access (UID 0 / sudo / setuid)
  - Risk configuration write permissions
  - Arbitrary un-sandboxed execution
  - Protected filesystem access (/etc/kairos/vault, /etc/shadow, /var/log/audit)
"""

import os
import sys
import enum
import json
import dataclasses
from typing import Dict, List, Set, Optional, Any

class IsolationTier(enum.Enum):
    TRUSTED_SYSTEM = "TRUSTED_SYSTEM"
    NORMAL_APP = "NORMAL_APP"
    UNTRUSTED_APP = "UNTRUSTED_APP"
    PLUGIN = "PLUGIN"
    AI_TOOL = "AI_TOOL"

@dataclasses.dataclass
class SandboxProfile:
    tier: IsolationTier
    name: str
    network_access: str           # "NONE", "UNIX_ONLY", "FILTERED_LAN", "FULL"
    filesystem_access: str        # "RESTRICTED_RO", "TEMP_RW", "USER_HOME", "FULL_SYSTEM"
    allowed_syscall_filter: str   # "SECCOMP_STRICT", "SECCOMP_DEFAULT", "SECCOMP_MINIMAL"
    allow_setuid: bool
    allow_device_raw: bool
    allow_broker_credentials: bool
    allow_risk_config_write: bool
    cgroup_memory_max: str
    cgroup_cpu_quota: str

# Standard Baseline Profiles
SANDBOX_PROFILES: Dict[IsolationTier, SandboxProfile] = {
    IsolationTier.TRUSTED_SYSTEM: SandboxProfile(
        tier=IsolationTier.TRUSTED_SYSTEM,
        name="Trusted System Infrastructure",
        network_access="FILTERED_LAN",
        filesystem_access="FULL_SYSTEM",
        allowed_syscall_filter="SECCOMP_DEFAULT",
        allow_setuid=False,
        allow_device_raw=True,
        allow_broker_credentials=True,
        allow_risk_config_write=True,
        cgroup_memory_max="None",
        cgroup_cpu_quota="None"
    ),
    IsolationTier.NORMAL_APP: SandboxProfile(
        tier=IsolationTier.NORMAL_APP,
        name="Standard Operator Desktop Application",
        network_access="FULL",
        filesystem_access="USER_HOME",
        allowed_syscall_filter="SECCOMP_DEFAULT",
        allow_setuid=False,
        allow_device_raw=False,
        allow_broker_credentials=False,
        allow_risk_config_write=False,
        cgroup_memory_max="4G",
        cgroup_cpu_quota="None"
    ),
    IsolationTier.UNTRUSTED_APP: SandboxProfile(
        tier=IsolationTier.UNTRUSTED_APP,
        name="Untrusted 3rd-Party Sandboxed Application",
        network_access="FILTERED_LAN",
        filesystem_access="TEMP_RW",
        allowed_syscall_filter="SECCOMP_STRICT",
        allow_setuid=False,
        allow_device_raw=False,
        allow_broker_credentials=False,
        allow_risk_config_write=False,
        cgroup_memory_max="2G",
        cgroup_cpu_quota="200%"
    ),
    IsolationTier.PLUGIN: SandboxProfile(
        tier=IsolationTier.PLUGIN,
        name="Algorithmic Strategy / Market Data Plugin",
        network_access="NONE",
        filesystem_access="RESTRICTED_RO",
        allowed_syscall_filter="SECCOMP_STRICT",
        allow_setuid=False,
        allow_device_raw=False,
        allow_broker_credentials=False,
        allow_risk_config_write=False,
        cgroup_memory_max="1G",
        cgroup_cpu_quota="100%"
    ),
    IsolationTier.AI_TOOL: SandboxProfile(
        tier=IsolationTier.AI_TOOL,
        name="Autonomous AI Agent & Reasoning Tool",
        network_access="UNIX_ONLY",
        filesystem_access="TEMP_RW",
        allowed_syscall_filter="SECCOMP_STRICT",
        allow_setuid=False,
        allow_device_raw=False,
        allow_broker_credentials=False,
        allow_risk_config_write=False,
        cgroup_memory_max="2G",
        cgroup_cpu_quota="150%"
    )
}

# Forbidden directories for untrusted, plugins, and AI tools
PROTECTED_PATHS = [
    "/etc/kairos/vault",
    "/etc/kairos/risk",
    "/etc/shadow",
    "/var/log/audit",
    "/boot",
    "/sys/firmware/efi"
]

# Forbidden system calls under strict seccomp
BLOCKED_SYSCALLS = [
    "ptrace",
    "bpf",
    "kexec_load",
    "kexec_file_load",
    "reboot",
    "mount",
    "umount2",
    "chroot",
    "setns",
    "unshare",
    "init_module",
    "finit_module",
    "delete_module"
]

class SandboxEnforcer:
    """
    Evaluates execution requests and produces verified sandbox confinement directives.
    Guarantees that untrusted code, plugins, and AI tools cannot access forbidden targets.
    """

    @staticmethod
    def get_profile(tier: IsolationTier) -> SandboxProfile:
        return SANDBOX_PROFILES[tier]

    @staticmethod
    def validate_access(tier: IsolationTier, target_path: Optional[str] = None, request_network: bool = False, request_secret: bool = False, request_risk_config: bool = False) -> Dict[str, Any]:
        """
        Enforces access control invariants.
        Returns a dict: {"allowed": bool, "reason": str}
        """
        profile = SANDBOX_PROFILES.get(tier)
        if not profile:
            return {"allowed": False, "reason": f"Unknown tier: {tier}"}

        # Invariant 1: Check broker credentials request
        if request_secret and not profile.allow_broker_credentials:
            return {
                "allowed": False,
                "reason": f"SECURITY VIOLATION: {tier.value} is strictly denied access to broker credentials and private vault keys."
            }

        # Invariant 2: Check risk configuration modification
        if request_risk_config and not profile.allow_risk_config_write:
            return {
                "allowed": False,
                "reason": f"SECURITY VIOLATION: {tier.value} cannot modify immutable Risk Gatekeeper configuration."
            }

        # Invariant 3: Check protected filesystem paths
        if target_path:
            norm = os.path.normpath(target_path)
            for p in PROTECTED_PATHS:
                if norm == p or norm.startswith(p + "/"):
                    if tier in (IsolationTier.PLUGIN, IsolationTier.AI_TOOL, IsolationTier.UNTRUSTED_APP):
                        return {
                            "allowed": False,
                            "reason": f"SECURITY VIOLATION: Path '{target_path}' is protected system substrate; access denied for {tier.value}."
                        }

        # Invariant 4: Check network access for plugins
        if request_network and profile.network_access == "NONE":
            return {
                "allowed": False,
                "reason": f"SECURITY VIOLATION: {tier.value} operates under total network isolation (Network namespace denied)."
            }

        return {"allowed": True, "reason": "Access granted within sandbox policy"}

    @staticmethod
    def generate_bwrap_command(tier: IsolationTier, binary_path: str, args: List[str]) -> List[str]:
        """
        Generates bubblewrap / unshare CLI args to sandbox an application process.
        """
        profile = SANDBOX_PROFILES[tier]
        cmd = [
            "bwrap",
            "--ro-bind", "/usr", "/usr",
            "--ro-bind", "/lib", "/lib",
            "--ro-bind", "/lib64", "/lib64",
            "--ro-bind", "/bin", "/bin",
            "--ro-bind", "/sbin", "/sbin",
            "--proc", "/proc",
            "--dev", "/dev",
            "--tmpfs", "/tmp",
            "--tmpfs", "/run",
            "--die-with-parent",
            "--new-session"
        ]

        if not profile.allow_setuid:
            cmd.append("--nosuid")

        if profile.network_access == "NONE":
            cmd.append("--unshare-net")
        elif profile.network_access == "UNIX_ONLY":
            cmd.extend(["--unshare-net", "--bind", "/run/kairos", "/run/kairos"])

        if tier in (IsolationTier.PLUGIN, IsolationTier.AI_TOOL):
            # Mount a sandboxed scratch space
            scratch_dir = f"/tmp/kairos_sandbox_{os.getpid()}"
            os.makedirs(scratch_dir, exist_ok=True)
            cmd.extend(["--bind", scratch_dir, "/workspace"])

        cmd.append(binary_path)
        cmd.extend(args)
        return cmd

    @staticmethod
    def generate_seccomp_policy(tier: IsolationTier) -> Dict[str, Any]:
        """
        Generates Seccomp BPF whitelist / blacklist filter definition.
        """
        profile = SANDBOX_PROFILES[tier]
        if profile.allowed_syscall_filter == "SECCOMP_STRICT":
            return {
                "default_action": "SCMP_ACT_ERRNO",
                "blocked_syscalls": BLOCKED_SYSCALLS,
                "allowed_standard": ["read", "write", "close", "fstat", "mmap", "mprotect", "munmap", "brk", "rt_sigaction", "exit_group", "futex", "nanosleep", "clock_gettime", "getpid", "getuid"]
            }
        else:
            return {
                "default_action": "SCMP_ACT_ALLOW",
                "blocked_syscalls": ["kexec_load", "init_module", "delete_module"]
            }
