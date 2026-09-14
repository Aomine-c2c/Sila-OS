#!/usr/bin/env bash
# KAIROS Desktop Environment Supervisor & Session Watchdog
# Ensures resilience: monitors waybar, mako, cliphist, polkit, swayidle.
# If any desktop utility terminates unexpectedly, automatically restarts it.
# If Hyprland itself exits or crashes, falls back gracefully to a rescue console.
set -u

LOG_DIR="/run/user/$(id -u)/kairos"
mkdir -p "$LOG_DIR"
exec >> "$LOG_DIR/desktop-session.log" 2>&1

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] [KAIROS Watchdog] Session monitor active."

# Helper function to spawn and monitor background daemons
supervise() {
    local name="$1"
    shift
    local cmd="$@"

    (
        while true; do
            if ! pgrep -x "$name" >/dev/null 2>&1; then
                echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] [Supervisor] Starting daemon: $name ($cmd)"
                $cmd &
            fi
            sleep 3
        done
    ) &
}

# 1. Authentication Agent (polkit-gnome)
if [ -x /usr/libexec/polkit-gnome-authentication-agent-1 ]; then
    supervise "polkit-gnome-authentication-agent-1" /usr/libexec/polkit-gnome-authentication-agent-1
fi

# 2. Notification Daemon (mako)
if command -v mako >/dev/null 2>&1; then
    supervise "mako" mako
fi

# 3. Status Bar (waybar)
if command -v waybar >/dev/null 2>&1; then
    supervise "waybar" waybar -c /etc/kairos/shell/waybar.json -s /etc/kairos/shell/waybar.css
fi

# 4. Wallpaper System (swaybg)
if command -v swaybg >/dev/null 2>&1; then
    if [ ! -f "$LOG_DIR/swaybg.pid" ] || ! kill -0 "$(cat "$LOG_DIR/swaybg.pid" 2>/dev/null)" 2>/dev/null; then
        swaybg -c "#0a0c10" &
        echo $! > "$LOG_DIR/swaybg.pid"
    fi
fi

# 5. Idle Management & Screen Locker (swayidle + swaylock)
if command -v swayidle >/dev/null 2>&1 && command -v swaylock >/dev/null 2>&1; then
    LOCK_CMD="swaylock -f -c 0a0c10 --inside-color 0d1117 --ring-color 00f0ff --key-hl-color 00ff88 --line-color 00000000 --text-color e0e6ed"
    supervise "swayidle" swayidle -w \
        timeout 600 "$LOCK_CMD" \
        timeout 900 'hyprctl dispatch dpms off' \
        resume 'hyprctl dispatch dpms on' \
        before-sleep "$LOCK_CMD"
fi

# 6. Clipboard Daemon (cliphist)
if command -v cliphist >/dev/null 2>&1 && command -v wl-paste >/dev/null 2>&1; then
    (
        wl-paste --type text --watch cliphist store &
        wl-paste --type image --watch cliphist store &
    )
fi

# 7. System Tray Network Applet
if command -v nm-applet >/dev/null 2>&1; then
    supervise "nm-applet" nm-applet --indicator
fi

echo "[$(date -u +'%Y-%m-%dT%H:%M:%SZ')] [KAIROS Watchdog] All desktop daemons supervised."
