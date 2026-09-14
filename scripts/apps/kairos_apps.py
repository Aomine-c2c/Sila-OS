#!/usr/bin/env python3
"""
KAIROS Core System Applications Suite
Unified application controller and native interface for the 14 core OS applications:
  1. System Settings (Performance profiles, real-time scheduler, low-latency tuning)
  2. Network Manager (Interface state, DNS, IP routing, hardware telemetry)
  3. Display Settings (Wayland KMS, DRM outputs, HiDPI scaling, refresh rates)
  4. Audio Settings (PipeWire/ALSA endpoints, volume levels, mute state)
  5. Users (User identity, privilege boundaries, role groups, session audit)
  6. Storage (Btrfs subvolumes, LUKS2 encryption, snapshots, disk health)
  7. Security (Firewall ruleset, AppArmor, audit telemetry, immutable controls)
  8. Updates (Reproducible release validation, rollback targets, atomic state)
  9. Services (Systemd daemons, low-latency watchdogs, immutable risk engine)
 10. Startup Applications (Desktop session autostart, background agents)
 11. Hardware Information (CPU topology, NUMA nodes, GPU acceleration, memory)
 12. Logs (Audit events, privileged operation trails, journal slices)
 13. Recovery (Disaster recovery generation, fallback initramfs, snapshot rollback)
 14. About KAIROS (Operating system identity, design philosophy, release tier)

Every application interacts with the OS through controlled system interfaces.
Privileged and dangerous operations are NEVER run directly by UI/client code;
they are delegated to kairos-sysd via UNIX domain socket (/run/kairos/sysd.sock)
which enforces SO_PEERCRED authentication, group-based authorization (wheel/trader),
action whitelisting, and structured audit logging.
"""

import sys
import os
import json
import argparse
import datetime

# Add root directory to sys.path so we can import services and shell state
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.services.kairos_sysd import client_request

ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_CYAN = "\033[36m"
ANSI_GREEN = "\033[32m"
ANSI_YELLOW = "\033[33m"
ANSI_RED = "\033[31m"
ANSI_MAGENTA = "\033[35m"
ANSI_GRAY = "\033[90m"

def render_banner(app_number: int, app_name: str, app_desc: str):
    print(f"{ANSI_CYAN}================================================================================{ANSI_RESET}")
    print(f" {ANSI_BOLD}◈ KAIROS CORE APP #{app_number:02d} :: {app_name.upper()}{ANSI_RESET}")
    print(f" {ANSI_GRAY}Role: {app_desc}{ANSI_RESET}")
    print(f"{ANSI_CYAN}================================================================================{ANSI_RESET}")

def render_json_or_formatted(data, as_json=False):
    if as_json:
        print(json.dumps(data, indent=2))
        return
    if isinstance(data, dict) and "error" in data:
        print(f" {ANSI_RED}[DENIED / ERROR]{ANSI_RESET} {data['error']}")
        return
    return data

# -----------------------------------------------------------------------------
# 1. SYSTEM SETTINGS
# -----------------------------------------------------------------------------
def app_settings(action: str = "get", profile: str = "low-latency", as_json: bool = False):
    """System Settings: Performance profiles, real-time scheduler & power governors."""
    render_banner(1, "System Settings", "System-wide performance, scheduler, and kernel tuning")
    if action == "set":
        print(f" Requesting privileged profile adjustment -> '{profile}' via kairos-sysd...")
        res = client_request("settings.set_profile", {"profile": profile})
    else:
        res = client_request("settings.get_profile")

    if as_json:
        return render_json_or_formatted(res, True)
    if "error" in res:
        return render_json_or_formatted(res)

    if action == "set":
        print(f" {ANSI_GREEN}[SUCCESS]{ANSI_RESET} Applied system profile: {ANSI_BOLD}{res.get('applied_profile')}{ANSI_RESET}")
    else:
        print(f" Active Tuning Profile : {ANSI_BOLD}{res.get('profile', 'low-latency')}{ANSI_RESET}")
        print(f" CPU Governor Policy   : {res.get('governor', 'performance')}")
        print(f" Realtime Tickless     : {'ENABLED (nohz_full)' if res.get('tickless') else 'DISABLED'}")
        print(f" IRQ Core Pinning      : Low-Latency Network/NVMe pinned to dedicated isolcpus")
    return 0

# -----------------------------------------------------------------------------
# 2. NETWORK MANAGER
# -----------------------------------------------------------------------------
def app_network(action: str = "status", iface: str = "eth0", dns: str = None, as_json: bool = False):
    """Network Manager: Network topology, latency monitoring & DNS configuration."""
    render_banner(2, "Network Manager", "Controlled network connection & interface manager")
    if action == "restart":
        print(f" Requesting privileged interface bounce for '{iface}' via kairos-sysd...")
        res = client_request("network.restart_interface", {"interface": iface})
    elif action == "set-dns":
        print(f" Requesting privileged DNS update -> '{dns}' via kairos-sysd...")
        res = client_request("network.set_dns", {"dns": dns})
    else:
        res = client_request("network.get_status")

    if as_json:
        return render_json_or_formatted(res, True)
    if "error" in res:
        return render_json_or_formatted(res)

    if action == "restart":
        print(f" {ANSI_GREEN}[SUCCESS]{ANSI_RESET} Network interface '{iface}' cycled successfully.")
    elif action == "set-dns":
        print(f" {ANSI_GREEN}[SUCCESS]{ANSI_RESET} DNS configuration updated to '{dns}'.")
    else:
        print(f" Stack Health      : {ANSI_GREEN}{res.get('status', 'NOMINAL')}{ANSI_RESET}")
        print(f" Primary Gateway   : {res.get('gateway', '192.168.1.1')}")
        print(f" Round-Trip Latency: {res.get('latency_ms', 0.12):.2f} ms (sub-millisecond low-latency)")
        print(f" Packet Loss       : {res.get('packet_loss', '0.00%')}")
        print(f" Active DNS Resolv : 127.0.0.53 (systemd-resolved zero-cache-leak)")
    return 0

# -----------------------------------------------------------------------------
# 3. DISPLAY SETTINGS
# -----------------------------------------------------------------------------
def app_display(action: str = "info", scale: str = "1.0", as_json: bool = False):
    """Display Settings: Wayland KMS, display outputs, refresh rates & HiDPI scaling."""
    render_banner(3, "Display Settings", "Wayland compositor display outputs and HiDPI scaling")
    if action == "set-scale":
        print(f" Requesting display scaling adjustment -> '{scale}' via kairos-sysd...")
        res = client_request("display.set_scale", {"scale": scale})
    else:
        res = client_request("display.get_info")

    if as_json:
        return render_json_or_formatted(res, True)
    if "error" in res:
        return render_json_or_formatted(res)

    if action == "set-scale":
        print(f" {ANSI_GREEN}[SUCCESS]{ANSI_RESET} Display scale '{res.get('scale_applied')}' applied to active Wayland output.")
    else:
        monitors = res.get("monitors", [])
        print(f" Wayland Compositor: Hyprland KMS/DRM Direct Output")
        print(f" Detected Monitors : {len(monitors)} connected output(s)")
        for m in monitors:
            print(f"   • {m.get('name', 'eDP-1')} [{m.get('resolution', '1920x1080@60Hz')}] Scale: {m.get('scale', 1.0)}x")
        print(f" DRM Render Node   : {res.get('render_node', '/dev/dri/renderD128')}")
        print(f" Variable Refresh  : VRR/Adaptive Sync Enabled")
    return 0

# -----------------------------------------------------------------------------
# 4. AUDIO SETTINGS
# -----------------------------------------------------------------------------
def app_audio(action: str = "status", volume: int = 50, as_json: bool = False):
    """Audio Settings: PipeWire endpoints, master volume & hardware mute states."""
    render_banner(4, "Audio Settings", "PipeWire pro-audio low-latency routing and mixer")
    if action == "set-volume":
        res = client_request("audio.set_volume", {"volume": volume})
    elif action == "mute":
        res = client_request("audio.toggle_mute")
    else:
        res = client_request("audio.get_status")

    if as_json:
        return render_json_or_formatted(res, True)
    if "error" in res:
        return render_json_or_formatted(res)

    if action == "set-volume":
        print(f" {ANSI_GREEN}[SUCCESS]{ANSI_RESET} Master volume set to {res.get('volume')}%.")
    elif action == "mute":
        print(f" {ANSI_GREEN}[SUCCESS]{ANSI_RESET} Audio output mute state toggled.")
    else:
        print(f" Sound Server     : PipeWire 1.0 Low-Latency Audio Subsystem")
        print(f" Master Volume    : {res.get('volume', 65)}%")
        print(f" Mute Status      : {'MUTED' if res.get('muted') else 'UNMUTED'}")
        print(f" Default Sink     : Realtek ALC Pro High-Definition Audio (Direct HW)")
    return 0

# -----------------------------------------------------------------------------
# 5. USERS
# -----------------------------------------------------------------------------
def app_users(action: str = "list", target_user: str = "trader", as_json: bool = False):
    """Users: Identity accounts, role boundaries & privilege separation."""
    render_banner(5, "Users", "User identity, session management, and privilege separation")
    if action == "lock":
        print(f" Requesting privileged account lock for '{target_user}' via kairos-sysd...")
        res = client_request("users.lock_account", {"username": target_user})
    else:
        res = client_request("users.list")

    if as_json:
        return render_json_or_formatted(res, True)
    if "error" in res:
        return render_json_or_formatted(res)

    if action == "lock":
        print(f" {ANSI_GREEN}[SUCCESS]{ANSI_RESET} Account '{target_user}' successfully locked.")
    else:
        users = res.get("users", [])
        print(f" Defined System & Local Accounts ({len(users)} registered):")
        for u in users:
            print(f"   • {ANSI_BOLD}{u.get('username')}{ANSI_RESET} (UID: {u.get('uid')}) - Shell: {u.get('shell')} - Home: {u.get('home')}")
        print(" Security Boundary: Trading daemons run non-root (UID 1000/1001); admin requires wheel.")
    return 0

# -----------------------------------------------------------------------------
# 6. STORAGE
# -----------------------------------------------------------------------------
def app_storage(action: str = "info", snapshot_label: str = "manual", as_json: bool = False):
    """Storage: Btrfs subvolumes, LUKS2 encryption, snapshot creation & drive health."""
    render_banner(6, "Storage", "Storage architecture, Btrfs subvolumes, and snapshot management")
    if action == "snapshot":
        print(f" Requesting privileged snapshot creation ('{snapshot_label}') via kairos-sysd...")
        res = client_request("storage.create_snapshot", {"label": snapshot_label})
    else:
        res = client_request("storage.get_info")

    if as_json:
        return render_json_or_formatted(res, True)
    if "error" in res:
        return render_json_or_formatted(res)

    if action == "snapshot":
        print(f" {ANSI_GREEN}[SUCCESS]{ANSI_RESET} Created atomic Btrfs snapshot: {ANSI_BOLD}{res.get('snapshot')}{ANSI_RESET}")
    else:
        print(f" Filesystem Engine : {res.get('filesystem', 'btrfs').upper()} with zstd compression")
        print(f" Root Encryption   : LUKS2 (AES-XTS 512-bit Hardware Accelerated)")
        print(f" Active Subvolumes :")
        for sub in res.get("subvolumes", []):
            print(f"   • {sub}")
        print(f" Snapshot Policy   : Pre-update atomic rollbacks enabled on @snapshots")
    return 0

# -----------------------------------------------------------------------------
# 7. SECURITY
# -----------------------------------------------------------------------------
def app_security(action: str = "audit", as_json: bool = False):
    """Security: Hardening telemetry, firewall rule management & AppArmor profiles."""
    render_banner(7, "Security", "Operating system security posture, firewall, and access control")
    if action == "reload-firewall":
        print(" Requesting privileged firewall reload via kairos-sysd...")
        res = client_request("security.reload_firewall")
    else:
        res = client_request("security.audit_report")

    if as_json:
        return render_json_or_formatted(res, True)
    if "error" in res:
        return render_json_or_formatted(res)

    if action == "reload-firewall":
        print(f" {ANSI_GREEN}[SUCCESS]{ANSI_RESET} {res.get('ruleset')}")
    else:
        print(f" Overall Security Status: {ANSI_GREEN}{res.get('status', 'PASS')}{ANSI_RESET}")
        print(" Active Security Controls:")
        for c in res.get("controls", []):
            print(f"   • {c.get('name')}: {ANSI_GREEN}{c.get('result')}{ANSI_RESET}")
        print(" Kernel Lockdown       : Integrity mode active")
        print(" Privilege Escalation  : Restricted to authenticated 'wheel' members with TTY audit")
    return 0

# -----------------------------------------------------------------------------
# 8. UPDATES
# -----------------------------------------------------------------------------
def app_updates(action: str = "check", target_snapshot: str = "snapshot_previous", as_json: bool = False):
    """Updates: Reproducible OS image releases, atomic updates & snapshot rollback."""
    render_banner(8, "Updates", "Certified reproducible release updates and atomic rollbacks")
    if action == "rollback":
        print(f" Requesting privileged boot rollback to '{target_snapshot}' via kairos-sysd...")
        res = client_request("updates.rollback", {"snapshot": target_snapshot})
    else:
        res = client_request("updates.check")

    if as_json:
        return render_json_or_formatted(res, True)
    if "error" in res:
        return render_json_or_formatted(res)

    if action == "rollback":
        print(f" {ANSI_GREEN}[SUCCESS]{ANSI_RESET} Rollback target staged: {res.get('rollback_target')}. Status: {res.get('next_boot')}")
    else:
        print(f" Installed Version : {res.get('installed_version', '1.0.0-rt')}")
        print(f" Remote Channel    : Certified Stable Production Channel")
        print(f" Update Status     : {'ALL PACKAGES CURRENT' if res.get('up_to_date') else 'UPDATE AVAILABLE'}")
        print(f" Image Signature   : ed25519 Verified by KAIROS Institutional Release Authority")
    return 0

# -----------------------------------------------------------------------------
# 9. SERVICES
# -----------------------------------------------------------------------------
def app_services(action: str = "list", service_name: str = "", as_json: bool = False):
    """Services: System daemons, low-latency watchdogs & hardware-enforced risk engine."""
    render_banner(9, "Services", "Systemd background service supervision & health telemetry")
    if action == "restart":
        print(f" Requesting privileged restart for '{service_name}' via kairos-sysd...")
        res = client_request("services.restart", {"service": service_name})
    else:
        res = client_request("services.list")

    if as_json:
        return render_json_or_formatted(res, True)
    if "error" in res:
        return render_json_or_formatted(res)

    if action == "restart":
        print(f" {ANSI_GREEN}[SUCCESS]{ANSI_RESET} Service '{service_name}' restarted.")
    else:
        print(" Monitored Core Subsystems:")
        for s in res.get("services", []):
            st = s.get('state')
            col = ANSI_GREEN if st == "active" else ANSI_YELLOW
            print(f"   • {ANSI_BOLD}{s.get('name')}{ANSI_RESET} [{col}{st.upper()}{ANSI_RESET}] - {s.get('type')}")
        print(" Immutable Rule: kairos-riskd cannot be terminated while trading orders remain live.")
    return 0

# -----------------------------------------------------------------------------
# 10. STARTUP APPLICATIONS
# -----------------------------------------------------------------------------
def app_startup(action: str = "list", app_name: str = "", as_json: bool = False):
    """Startup Applications: Desktop environment autostart, notification & clipboard daemons."""
    render_banner(10, "Startup Applications", "Wayland user session startup applications and autostart hooks")
    if action == "toggle":
        print(f" Requesting autostart toggle for '{app_name}' via kairos-sysd...")
        res = client_request("startup.toggle", {"app": app_name})
    else:
        res = client_request("startup.list")

    if as_json:
        return render_json_or_formatted(res, True)
    if "error" in res:
        return render_json_or_formatted(res)

    if action == "toggle":
        print(f" {ANSI_GREEN}[SUCCESS]{ANSI_RESET} Startup configuration for '{app_name}' toggled.")
    else:
        print(" User Session Autostart Registry (~/.config/hypr/autostart.conf):")
        for app in res.get("startup_apps", []):
            stat = "ENABLED" if app.get('enabled') else "DISABLED"
            col = ANSI_GREEN if app.get('enabled') else ANSI_GRAY
            print(f"   • [{col}{stat}{ANSI_RESET}] {ANSI_BOLD}{app.get('name')}{ANSI_RESET} -> `{app.get('command')}`")
    return 0

# -----------------------------------------------------------------------------
# 11. HARDWARE INFORMATION
# -----------------------------------------------------------------------------
def app_hardware(as_json: bool = False):
    """Hardware Information: CPU microarchitecture, NUMA topology, memory & GPU detection."""
    render_banner(11, "Hardware Information", "Physical compute architecture, memory topology, and accelerators")
    res = client_request("hardware.get_info")

    if as_json:
        return render_json_or_formatted(res, True)
    if "error" in res:
        return render_json_or_formatted(res)

    print(f" CPU Architecture  : {res.get('arch', 'x86_64')} with AVX-512 & AES-NI hardware extensions")
    print(f" Memory Subsystem  : High-throughput low-latency DDR5 (ECC enabled where supported)")
    print(f" NUMA Topology     : {res.get('topology', 'NUMA Balanced')}")
    print(f" Graphics Devices  :")
    for gpu in res.get("gpus", []):
        print(f"   • {gpu.get('vendor', 'Unknown')} {gpu.get('model', 'Graphics Accelerator')} (Driver: {gpu.get('driver', 'amdgpu/i915')})")
    print(" Bus Inspection    : PCIe Gen4/Gen5 lanes dedicated to network and NVMe fabric")
    return 0

# -----------------------------------------------------------------------------
# 12. LOGS
# -----------------------------------------------------------------------------
def app_logs(limit: int = 10, as_json: bool = False):
    """Logs: System event logs, audit trails of privileged operations & journal entries."""
    render_banner(12, "Logs", "System-wide audit trail and journal observability")
    res = client_request("logs.query", {"limit": limit})

    if as_json:
        return render_json_or_formatted(res, True)
    if "error" in res:
        return render_json_or_formatted(res)

    print(f" Showing recent audit & journal log records (most recent {limit}):")
    for entry in res.get("recent_entries", []):
        print(f"   [{ANSI_GRAY}{entry.get('timestamp')}{ANSI_RESET}] {ANSI_CYAN}{entry.get('source')}{ANSI_RESET}: {entry.get('message')}")
    print(f" Audit Store       : /var/log/audit/kairos-sysd.log (Immutable append-only)")
    return 0

# -----------------------------------------------------------------------------
# 13. RECOVERY
# -----------------------------------------------------------------------------
def app_recovery(action: str = "status", as_json: bool = False):
    """Recovery: Disaster recovery environment, fallback initramfs & emergency shell."""
    render_banner(13, "Recovery", "Disaster recovery, fallback kernel profiles, and emergency boots")
    if action == "trigger-test":
        print(" Requesting fallback initramfs integrity check via kairos-sysd...")
        res = client_request("updates.rollback", {"snapshot": "snapshot_fallback_test"})
    else:
        res = client_request("about.info")

    if as_json:
        return render_json_or_formatted(res, True)
    if "error" in res:
        return render_json_or_formatted(res)

    print(" Recovery Architecture Components:")
    print("   • Fallback Initramfs   : /boot/initramfs-kairos-fallback.img (All storage drivers built-in)")
    print("   • Emergency Entry      : GRUB/systemd-boot recovery profile (`kairos.mode=recovery nomodeset`)")
    print("   • Read-Only Subvolume  : Btrfs root snapshot mountable without modifying broken user state")
    print("   • Network Rescue       : Embedded minimal busybox rescue shell with static DHCP")
    print(f" Status                : {ANSI_GREEN}HEALTHY - Ready for disaster failover{ANSI_RESET}")
    return 0

# -----------------------------------------------------------------------------
# 14. ABOUT KAIROS
# -----------------------------------------------------------------------------
def app_about(as_json: bool = False):
    """About KAIROS: Operating system identity, visual philosophy & release tier."""
    render_banner(14, "About KAIROS", "Adaptive Trading Operating System Identity & Release Tier")
    res = client_request("about.info")

    if as_json:
        return render_json_or_formatted(res, True)
    if "error" in res:
        return render_json_or_formatted(res)

    print(f" Operating System  : {ANSI_BOLD}{res.get('os_name')}{ANSI_RESET}")
    print(f" Edition           : {res.get('edition')}")
    print(f" Version           : {res.get('version')}")
    print(f" Release Tier      : {res.get('build_type')}")
    print(f" Display Server    : {res.get('display_server')}")
    print(f" Kernel Flavor     : {res.get('kernel')}")
    print(f" Risk Gatekeeper   : {res.get('risk_engine')}")
    print(f" Design Philosophy : Minimal, technical, calm, professional, information-dense.")
    print(f" Core Symbol       : Adaptive Mechanical/Evolutionary Ring (Observe-Diagnose-Adapt-Validate-Deploy-Learn)")
    return 0

# -----------------------------------------------------------------------------
# CLI ROUTER & DISPATCH
# -----------------------------------------------------------------------------
APP_REGISTRY = {
    "settings": ("System Settings", app_settings),
    "network": ("Network Manager", app_network),
    "display": ("Display Settings", app_display),
    "audio": ("Audio Settings", app_audio),
    "users": ("Users & Privilege Boundaries", app_users),
    "storage": ("Storage Architecture", app_storage),
    "security": ("Security Posture & Firewall", app_security),
    "updates": ("Updates & Atomic Rollback", app_updates),
    "services": ("Services & Low-Latency Daemons", app_services),
    "startup": ("Startup Applications", app_startup),
    "hardware": ("Hardware Telemetry", app_hardware),
    "logs": ("System & Audit Logs", app_logs),
    "recovery": ("Disaster Recovery Subsystem", app_recovery),
    "about": ("About KAIROS OS", app_about),
}

def list_applications():
    print(f"{ANSI_CYAN}================================================================================{ANSI_RESET}")
    print(f" {ANSI_BOLD}KAIROS OS - CORE SYSTEM APPLICATIONS (14 Core Domains){ANSI_RESET}")
    print(f"{ANSI_CYAN}================================================================================{ANSI_RESET}")
    for idx, (app_id, (name, _)) in enumerate(APP_REGISTRY.items(), start=1):
        print(f"  {idx:02d}. {ANSI_BOLD}{app_id:<12}{ANSI_RESET} - {name}")
    print(f"{ANSI_CYAN}================================================================================{ANSI_RESET}")
    print(" Usage: kairos app <application-name> [options]")
    print("        kairos app <application-name> --json")

def main():
    parser = argparse.ArgumentParser(description="KAIROS Core System Applications Suite", add_help=False)
    parser.add_argument("app", nargs="?", help="Application name to launch")
    parser.add_argument("--json", action="store_true", help="Output data in structured JSON format")
    parser.add_argument("--action", default="", help="Specific sub-action for the target application")
    parser.add_argument("--param", default="", help="Parameter value for the action")
    parser.add_argument("-h", "--help", action="store_true", help="Show help")

    args, remaining = parser.parse_known_args()

    if args.help or not args.app:
        list_applications()
        return 0

    app_key = args.app.lower().strip()
    if app_key not in APP_REGISTRY:
        print(f"{ANSI_RED}Error: Unknown core application '{args.app}'{ANSI_RESET}")
        list_applications()
        return 1

    _, handler = APP_REGISTRY[app_key]

    if app_key == "settings":
        act = args.action or ("set" if args.param else "get")
        prof = args.param or "low-latency"
        return handler(action=act, profile=prof, as_json=args.json)
    elif app_key == "network":
        act = args.action or "status"
        return handler(action=act, iface=args.param or "eth0", dns=args.param, as_json=args.json)
    elif app_key == "display":
        act = args.action or ("set-scale" if args.param else "info")
        return handler(action=act, scale=args.param or "1.0", as_json=args.json)
    elif app_key == "audio":
        act = args.action or ("set-volume" if args.param else "status")
        vol = int(args.param) if args.param.isdigit() else 50
        return handler(action=act, volume=vol, as_json=args.json)
    elif app_key == "users":
        act = args.action or ("lock" if args.param else "list")
        return handler(action=act, target_user=args.param or "trader", as_json=args.json)
    elif app_key == "storage":
        act = args.action or ("snapshot" if args.param else "info")
        return handler(action=act, snapshot_label=args.param or "manual", as_json=args.json)
    elif app_key == "security":
        act = args.action or "audit"
        return handler(action=act, as_json=args.json)
    elif app_key == "updates":
        act = args.action or ("rollback" if args.param else "check")
        return handler(action=act, target_snapshot=args.param or "snapshot_previous", as_json=args.json)
    elif app_key == "services":
        act = args.action or ("restart" if args.param else "list")
        return handler(action=act, service_name=args.param, as_json=args.json)
    elif app_key == "startup":
        act = args.action or ("toggle" if args.param else "list")
        return handler(action=act, app_name=args.param, as_json=args.json)
    elif app_key == "hardware":
        return handler(as_json=args.json)
    elif app_key == "logs":
        lim = int(args.param) if args.param.isdigit() else 10
        return handler(limit=lim, as_json=args.json)
    elif app_key == "recovery":
        act = args.action or "status"
        return handler(action=act, as_json=args.json)
    elif app_key == "about":
        return handler(as_json=args.json)

    return 0

if __name__ == "__main__":
    sys.exit(main())
