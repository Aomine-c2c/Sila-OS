#!/usr/bin/env python3
"""
KAIROS Theme Switcher Engine (kairos-theme)
Manages deterministic light (default) and dark themes across:
- Waybar top status bar
- Foot terminal emulator
- Wofi command palette
- GTK & Wayland desktop styles
"""

import sys
import os
import json
import subprocess
import shutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THEME_DIR = "/etc/kairos/shell" if os.getuid() == 0 else os.path.expanduser("~/.config/kairos/theme")
THEME_STATE_FILE = os.path.join(THEME_DIR, "current_theme.json")

# Light Theme Style (Default)
WAYBAR_LIGHT_CSS = """/* KAIROS Light Theme (Default) - Information-Dense & Clean */
* {
    border: none;
    border-radius: 0;
    font-family: "JetBrains Mono", "Roboto Mono", monospace;
    font-size: 12px;
    font-weight: 600;
    min-height: 0;
}

window#waybar {
    background: #ffffff;
    color: #0f172a;
    border-bottom: 2px solid #0284c7;
}

#custom-logo {
    color: #0284c7;
    font-size: 14px;
    padding: 0 10px;
    font-weight: bold;
}

#custom-palette_btn {
    color: #0284c7;
    background: #f0f9ff;
    border: 1px solid #0284c7;
    border-radius: 2px;
    padding: 0 8px;
    margin: 3px 4px;
}

#workspaces button {
    padding: 0 8px;
    color: #64748b;
}

#workspaces button.active {
    color: #0284c7;
    border-bottom: 2px solid #0284c7;
    background: #e0f2fe;
}

#custom-risk_status {
    color: #059669;
    background: #ecfdf5;
    padding: 0 10px;
    margin: 3px 6px;
    border-radius: 2px;
    border: 1px solid #10b981;
}

#custom-market_ticker {
    color: #0f172a;
    background: #f1f5f9;
    padding: 0 12px;
    margin: 3px 0;
    border-radius: 2px;
    border: 1px solid #cbd5e1;
}

#custom-broker_status {
    color: #0284c7;
    background: #f0f9ff;
    padding: 0 8px;
    margin: 3px 4px;
    border-radius: 2px;
    border: 1px solid #bae6fd;
}

#custom-adaptive_status {
    color: #7c3aed;
    background: #f5f3ff;
    padding: 0 8px;
    margin: 3px 4px;
    border-radius: 2px;
    border: 1px solid #ddd6fe;
}

#custom-adaptive_status.evolution_complete {
    color: #059669;
    background: #ecfdf5;
    border-color: #10b981;
}

#custom-adaptive_status.rollback, #custom-adaptive_status.halted {
    color: #dc2626;
    background: #fef2f2;
    border-color: #ef4444;
}

#custom-jitter {
    color: #0284c7;
    padding: 0 6px;
}

#pulseaudio, #network, #battery, #cpu, #memory, #clock {
    padding: 0 8px;
    color: #334155;
}

#battery.warning {
    color: #d97706;
}

#battery.critical {
    color: #dc2626;
}

#clock {
    color: #0284c7;
    background: #f0f9ff;
    padding: 0 10px;
}

#tray {
    padding: 0 8px;
}
"""

# Dark Theme Style (Optional)
WAYBAR_DARK_CSS = """/* KAIROS Dark Theme (Optional) */
* {
    border: none;
    border-radius: 0;
    font-family: "JetBrains Mono", "Roboto Mono", monospace;
    font-size: 12px;
    font-weight: bold;
    min-height: 0;
}

window#waybar {
    background: rgba(10, 12, 16, 0.94);
    color: #e0e6ed;
    border-bottom: 2px solid #00f0ff;
}

#custom-logo {
    color: #00f0ff;
    font-size: 14px;
    padding: 0 10px;
}

#custom-palette_btn {
    color: #00f0ff;
    background: rgba(0, 240, 255, 0.12);
    border: 1px solid #00f0ff;
    border-radius: 3px;
    padding: 0 8px;
    margin: 3px 4px;
}

#workspaces button {
    padding: 0 8px;
    color: #7b8496;
}

#workspaces button.active {
    color: #ffffff;
    border-bottom: 2px solid #00f0ff;
    background: rgba(0, 240, 255, 0.15);
}

#custom-risk_status {
    color: #00ff88;
    background: rgba(0, 255, 136, 0.15);
    padding: 0 10px;
    margin: 3px 6px;
    border-radius: 4px;
    border: 1px solid #00ff88;
}

#custom-market_ticker {
    color: #ffd700;
    background: rgba(255, 215, 0, 0.1);
    padding: 0 12px;
    margin: 3px 0;
    border-radius: 4px;
    border: 1px solid rgba(255, 215, 0, 0.3);
}

#custom-broker_status {
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.1);
    padding: 0 8px;
    margin: 3px 4px;
    border-radius: 3px;
    border: 1px solid rgba(56, 189, 248, 0.3);
}

#custom-adaptive_status {
    color: #c084fc;
    background: rgba(192, 132, 252, 0.1);
    padding: 0 8px;
    margin: 3px 4px;
    border-radius: 3px;
    border: 1px solid rgba(192, 132, 252, 0.3);
}

#custom-adaptive_status.evolution_complete {
    color: #00ff88;
    background: rgba(0, 255, 136, 0.15);
    border-color: #00ff88;
}

#custom-adaptive_status.rollback, #custom-adaptive_status.halted {
    color: #ff3366;
    background: rgba(255, 51, 102, 0.15);
    border-color: #ff3366;
}

#custom-jitter {
    color: #00f0ff;
    padding: 0 6px;
}

#pulseaudio, #network, #battery, #cpu, #memory, #clock {
    padding: 0 8px;
    color: #cbd5e1;
}

#battery.warning {
    color: #ffaa00;
}

#battery.critical {
    color: #ff3366;
}

#clock {
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.15);
    padding: 0 10px;
}

#tray {
    padding: 0 8px;
}
"""

def get_current_theme():
    if os.path.exists(THEME_STATE_FILE):
        try:
            with open(THEME_STATE_FILE, "r") as f:
                return json.load(f).get("theme", "light")
        except Exception:
            pass
    return "light"

def apply_theme(theme_name):
    theme_name = theme_name.lower().strip()
    if theme_name not in ("light", "dark"):
        print(f"[!] Invalid theme '{theme_name}'. Choose 'light' (default) or 'dark'.")
        return 1

    os.makedirs(THEME_DIR, exist_ok=True)
    with open(THEME_STATE_FILE, "w") as f:
        json.dump({"theme": theme_name}, f)

    # Write CSS to target system path if accessible
    waybar_css_target = "/etc/kairos/shell/waybar.css"
    css_content = WAYBAR_LIGHT_CSS if theme_name == "light" else WAYBAR_DARK_CSS

    # Also update repository config path
    repo_css_path = os.path.join(ROOT_DIR, "config/shell/waybar.css")
    try:
        with open(repo_css_path, "w", encoding="utf-8") as f:
            f.write(css_content)
    except Exception:
        pass

    if os.path.exists("/etc/kairos/shell"):
        try:
            with open(waybar_css_target, "w", encoding="utf-8") as f:
                f.write(css_content)
            # Signal waybar reload if running
            subprocess.call(["pkill", "-SIGUSR2", "waybar"], stderr=subprocess.DEVNULL)
        except Exception:
            pass

    print(f"[+] KAIROS Design System Theme set to: {theme_name.upper()} (Default is LIGHT).")
    return 0

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("set", "switch"):
        theme = sys.argv[2] if len(sys.argv) > 2 else "light"
        sys.exit(apply_theme(theme))
    elif len(sys.argv) > 1 and sys.argv[1] in ("get", "status"):
        print(f"Current theme: {get_current_theme()}")
        sys.exit(0)
    else:
        print(f"KAIROS Design System Theme Manager")
        print(f"Current Theme : {get_current_theme().upper()}")
        print(f"Usage:")
        print(f"  kairos theme get           - Show active system theme")
        print(f"  kairos theme set light     - Apply default calm Light Mode")
        print(f"  kairos theme set dark      - Apply optional Dark Mode")
        sys.exit(0)
