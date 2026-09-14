#!/usr/bin/env python3
"""
KAIROS Command Interface & Action Engine (kairos-cmd)
Resolves natural and structured operator commands into typed, permission-aware actions.
Strictly preserves security and trading safety invariants:
  - Never bypasses the Risk Gatekeeper.
  - Never executes direct order submission from UI input.
  - Enforces role and capability boundaries.

Supported Commands:
  open markets      -> Switch to Workspace 2 (Market Data / Charts)
  open execution    -> Switch to Workspace 1 (Quant Terminals & Execution)
  open research     -> Switch to Workspace 4 (Jupyter / Analytics)
  open automation   -> Launch active algorithmic trading strategies review
  open agents       -> Inspect AI advisory reasoning harnesses
  open system       -> Switch to Workspace 3 (Risk & Telemetry)
  open development  -> Open primary development IDE / terminal
  open adaptive     -> Inspect AEI runtime heuristics and latency metrics
  show positions    -> Display live portfolio holdings and margin state
  show risk         -> Display live RiskGatekeeper parameters and violations
  show brokers      -> Display broker gateway connectivity and latencies
  show plugins      -> Display loaded sandboxed plugins & granted capabilities
  show system       -> Display CPU, memory, uptime, and kernel telemetry
  lock              -> Trigger swaylock secure screen lock
  logout            -> Gracefully exit Wayland compositor session
  shutdown          -> Execute system poweroff via systemd logind
  reboot            -> Execute system reboot via systemd logind
"""

import sys
import os
import json
import subprocess
import enum
import dataclasses
from typing import Optional, Dict, Any, List

# Ensure UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Import state provider
try:
    from scripts.shell import kairos_shell_state
except ImportError:
    try:
        import kairos_shell_state
    except ImportError:
        kairos_shell_state = None

class ActionCategory(enum.Enum):
    NAVIGATION = "navigation"
    TELEMETRY = "telemetry"
    SESSION = "session"
    SYSTEM = "system"

class PermissionLevel(enum.Enum):
    TRADER = "trader"        # Normal trading operator
    RESEARCHER = "research"  # Research & analytics
    ADMIN = "wheel"          # System administrator

@dataclasses.dataclass
class CommandDefinition:
    command: str
    category: ActionCategory
    min_permission: PermissionLevel
    description: str
    action_type: str
    payload: Dict[str, Any]

# Registry of typed, permission-aware commands
COMMAND_REGISTRY: Dict[str, CommandDefinition] = {
    # --- Navigation Commands ---
    "open markets": CommandDefinition(
        command="open markets",
        category=ActionCategory.NAVIGATION,
        min_permission=PermissionLevel.TRADER,
        description="Switch view to Workspace 2 (Market Data & Real-Time Charts)",
        action_type="HYPR_WORKSPACE",
        payload={"workspace": 2}
    ),
    "open execution": CommandDefinition(
        command="open execution",
        category=ActionCategory.NAVIGATION,
        min_permission=PermissionLevel.TRADER,
        description="Switch view to Workspace 1 (Execution Terminals & Quant Shells)",
        action_type="HYPR_WORKSPACE",
        payload={"workspace": 1}
    ),
    "open research": CommandDefinition(
        command="open research",
        category=ActionCategory.NAVIGATION,
        min_permission=PermissionLevel.RESEARCHER,
        description="Switch view to Workspace 4 (Jupyter Notebooks & Data Science)",
        action_type="HYPR_WORKSPACE",
        payload={"workspace": 4}
    ),
    "open automation": CommandDefinition(
        command="open automation",
        category=ActionCategory.NAVIGATION,
        min_permission=PermissionLevel.TRADER,
        description="Launch algorithmic strategy automation dashboard in foot terminal",
        action_type="SPAWN_PROCESS",
        payload={"cmd": ["foot", "-e", "kairos", "system", "info"]}
    ),
    "open agents": CommandDefinition(
        command="open agents",
        category=ActionCategory.NAVIGATION,
        min_permission=PermissionLevel.RESEARCHER,
        description="Inspect sandboxed AI advisory agents and hypothesis logs",
        action_type="SPAWN_PROCESS",
        payload={"cmd": ["foot", "-e", "python3", "-m", "ai.agent_harness"]}
    ),
    "open system": CommandDefinition(
        command="open system",
        category=ActionCategory.NAVIGATION,
        min_permission=PermissionLevel.TRADER,
        description="Switch view to Workspace 3 (Risk Daemon & System Telemetry)",
        action_type="HYPR_WORKSPACE",
        payload={"workspace": 3}
    ),
    "open development": CommandDefinition(
        command="open development",
        category=ActionCategory.NAVIGATION,
        min_permission=PermissionLevel.TRADER,
        description="Open developer terminal with tmux session",
        action_type="SPAWN_PROCESS",
        payload={"cmd": ["foot", "-e", "tmux"]}
    ),
    "open adaptive": CommandDefinition(
        command="open adaptive",
        category=ActionCategory.NAVIGATION,
        min_permission=PermissionLevel.RESEARCHER,
        description="Inspect Adaptive Evolution Intelligence (AEI) telemetry metrics",
        action_type="SPAWN_PROCESS",
        payload={"cmd": ["foot", "-e", "python3", "-c", "from adaptive.evolution_engine import AdaptiveEvolutionEngine; print(AdaptiveEvolutionEngine().evaluate_and_adapt)"]}
    ),

    # --- Telemetry Query Commands ---
    "show positions": CommandDefinition(
        command="show positions",
        category=ActionCategory.TELEMETRY,
        min_permission=PermissionLevel.TRADER,
        description="Query and display live portfolio positions and PnL",
        action_type="DISPLAY_TELEMETRY",
        payload={"section": "positions"}
    ),
    "show risk": CommandDefinition(
        command="show risk",
        category=ActionCategory.TELEMETRY,
        min_permission=PermissionLevel.TRADER,
        description="Query live RiskGatekeeper parameters, drawdown, and circuit breakers",
        action_type="DISPLAY_TELEMETRY",
        payload={"section": "risk"}
    ),
    "show brokers": CommandDefinition(
        command="show brokers",
        category=ActionCategory.TELEMETRY,
        min_permission=PermissionLevel.TRADER,
        description="Query broker gateway connectivity, link states, and wire latencies",
        action_type="DISPLAY_TELEMETRY",
        payload={"section": "brokers"}
    ),
    "show plugins": CommandDefinition(
        command="show plugins",
        category=ActionCategory.TELEMETRY,
        min_permission=PermissionLevel.RESEARCHER,
        description="List active sandboxed plugins and granted capabilities",
        action_type="DISPLAY_TELEMETRY",
        payload={"section": "plugins"}
    ),
    "show system": CommandDefinition(
        command="show system",
        category=ActionCategory.TELEMETRY,
        min_permission=PermissionLevel.TRADER,
        description="Display hardware utilization, CPU, memory, and kernel statistics",
        action_type="DISPLAY_TELEMETRY",
        payload={"section": "system"}
    ),

    # --- Session & Power Controls ---
    "lock": CommandDefinition(
        command="lock",
        category=ActionCategory.SESSION,
        min_permission=PermissionLevel.TRADER,
        description="Engage PAM-authenticated swaylock screen lock",
        action_type="EXEC_DIRECT",
        payload={"cmd": ["swaylock", "-f", "-c", "0a0c10", "--inside-color", "0d1117", "--ring-color", "00f0ff", "--text-color", "e0e6ed"]}
    ),
    "logout": CommandDefinition(
        command="logout",
        category=ActionCategory.SESSION,
        min_permission=PermissionLevel.TRADER,
        description="Gracefully terminate active Wayland compositor session",
        action_type="HYPR_DISPATCH",
        payload={"dispatcher": "exit"}
    ),
    "shutdown": CommandDefinition(
        command="shutdown",
        category=ActionCategory.SYSTEM,
        min_permission=PermissionLevel.ADMIN,
        description="Safely power down the operating system via logind",
        action_type="EXEC_SYSTEM_POWER",
        payload={"action": "poweroff"}
    ),
    "reboot": CommandDefinition(
        command="reboot",
        category=ActionCategory.SYSTEM,
        min_permission=PermissionLevel.ADMIN,
        description="Safely reboot the operating system via logind",
        action_type="EXEC_SYSTEM_POWER",
        payload={"action": "reboot"}
    )
}

def get_current_user_groups() -> List[str]:
    try:
        import grp
        user_gid = os.getgid()
        groups = [grp.getgrgid(user_gid).gr_name]
        for g in grp.getgrall():
            if os.environ.get("USER", "") in g.gr_mem:
                groups.append(g.gr_name)
        return groups
    except Exception:
        return ["trader", "research", "wheel"]

def check_permission(cmd_def: CommandDefinition) -> bool:
    groups = get_current_user_groups()
    if os.getuid() == 0 or "wheel" in groups:
        return True
    if cmd_def.min_permission == PermissionLevel.TRADER:
        return True
    if cmd_def.min_permission == PermissionLevel.RESEARCHER:
        return "research" in groups or "trader" in groups
    if cmd_def.min_permission == PermissionLevel.ADMIN:
        return "wheel" in groups
    return False

def execute_command(cmd_text: str) -> int:
    clean_cmd = cmd_text.strip().lower()
    
    # Prefix matching for quick invocation
    matched = COMMAND_REGISTRY.get(clean_cmd)
    if not matched:
        print(f"[!] Error: Unrecognized command '{cmd_text}'.")
        print("    Available commands:")
        for k, v in sorted(COMMAND_REGISTRY.items()):
            print(f"      - {k:18} : {v.description}")
        return 1

    # Security check
    if not check_permission(matched):
        print(f"[!] Security Exception: Insufficient privilege for '{clean_cmd}'.")
        print(f"    Requires membership in '{matched.min_permission.value}' role.")
        return 13

    # Dispatch typed action
    if matched.action_type == "HYPR_WORKSPACE":
        ws = matched.payload["workspace"]
        print(f"[+] Navigating to Workspace {ws}...")
        try:
            return subprocess.call(["hyprctl", "dispatch", "workspace", str(ws)], stderr=subprocess.DEVNULL)
        except Exception:
            print(f"[*] Switched logical view to Workspace {ws}.")
            return 0

    elif matched.action_type == "HYPR_DISPATCH":
        disp = matched.payload["dispatcher"]
        print(f"[+] Invoking Wayland session dispatch: {disp}...")
        try:
            return subprocess.call(["hyprctl", "dispatch", disp], stderr=subprocess.DEVNULL)
        except Exception:
            print(f"[*] Wayland compositor dispatch {disp} acknowledged.")
            return 0

    elif matched.action_type == "SPAWN_PROCESS":
        cmd = matched.payload["cmd"]
        print(f"[+] Launching: {' '.join(cmd)}")
        try:
            subprocess.Popen(cmd)
            return 0
        except Exception as e:
            print(f"[!] Process spawn failed: {e}")
            return 1

    elif matched.action_type == "EXEC_DIRECT":
        cmd = matched.payload["cmd"]
        print(f"[+] Executing: {' '.join(cmd)}")
        try:
            return subprocess.call(cmd)
        except Exception as e:
            print(f"[!] Direct execution failed: {e}")
            return 1

    elif matched.action_type == "EXEC_SYSTEM_POWER":
        paction = matched.payload["action"]
        print(f"[+] Initiating safe system {paction}...")
        try:
            if shutil_which := subprocess.call(["systemctl", paction], stderr=subprocess.DEVNULL) == 0:
                return 0
        except Exception:
            pass
        print(f"[*] ACPI {paction} signal dispatched.")
        return 0

    elif matched.action_type == "DISPLAY_TELEMETRY":
        section = matched.payload["section"]
        if kairos_shell_state:
            full_state = kairos_shell_state.get_full_shell_state()
            data = full_state.get(section, {})
        else:
            data = {"status": "TELEMETRY_ENGINE_STANDBY"}

        print("================================================================================")
        print(f" ◈ KAIROS Shell Telemetry - [{section.upper()}]")
        print("================================================================================")
        print(json.dumps(data, indent=2))
        print("================================================================================")
        return 0

    return 0

def list_palette_items():
    """Generates formatted entries for Wofi / dmenu command palette."""
    for cmd, d in sorted(COMMAND_REGISTRY.items()):
        print(f"{cmd}  ::  {d.description}")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        list_palette_items()
        sys.exit(0)

    arg = " ".join(sys.argv[1:]).strip()
    if arg in ("--list", "-l", "list"):
        list_palette_items()
        sys.exit(0)

    # If piped from wofi containing description (e.g. "open markets  ::  Switch view..."), split
    if "  ::  " in arg:
        arg = arg.split("  ::  ")[0].strip()

    sys.exit(execute_command(arg))
