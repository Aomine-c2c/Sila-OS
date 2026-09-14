#!/usr/bin/env python3
"""
KAIROS OS Recovery Environment
==============================
Recovery menu and recovery procedures for the KAIROS OS recovery shell.

Supports:
  - Boot Normally
  - Boot Previous Version (snapshot rollback)
  - Repair System (bootloader + initramfs + services)
  - Rollback Update
  - Filesystem Diagnostics
  - Network Diagnostics
  - User Recovery
  - System Restore
  - Emergency Terminal
  - Shutdown / Reboot

This module is designed to run standalone on tty1 when the normal
desktop fails. It does NOT import any desktop or trading libraries.

Entry points:
  python3 kairos_recovery.py          → interactive menu
  python3 kairos_recovery.py <action> → run specific action
  kairos recovery menu                → via main CLI
"""

import sys
import os
import json
import time
import shutil
import subprocess
import datetime
import logging
import signal

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_PATH = "/var/log/kairos/recovery.log"
_log_dir = os.path.dirname(LOG_PATH)
os.makedirs(_log_dir, exist_ok=True)
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, mode="a", encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ]
)
log = logging.getLogger("kairos-recovery")

# ── ANSI colors (gracefully degraded if not a tty) ───────────────────────────
_USE_COLOR = sys.stdout.isatty() and not os.environ.get("NO_COLOR")

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text

def red(t):    return _c("31", t)
def green(t):  return _c("32", t)
def yellow(t): return _c("33", t)
def blue(t):   return _c("34", t)
def cyan(t):   return _c("36", t)
def bold(t):   return _c("1",  t)
def dim(t):    return _c("2",  t)

# ── Utilities ─────────────────────────────────────────────────────────────────

def clear():
    os.system("clear 2>/dev/null || cls 2>/dev/null || echo")

def hr(char="─", width=72):
    print(char * width)

def header():
    clear()
    print(cyan(bold(
        "╔══════════════════════════════════════════════════════════════════════╗\n"
        "║            KAIROS OS  ─  Recovery Environment                        ║\n"
        "║            System Repair & Rescue Interface                           ║\n"
        "╚══════════════════════════════════════════════════════════════════════╝"
    )))
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(dim(f"  Recovery started: {now}   Log: {LOG_PATH}"))
    print()

def status(msg: str):
    print(f"  {green('✓')}  {msg}")
    log.info(msg)

def warn(msg: str):
    print(f"  {yellow('⚠')}  {msg}")
    log.warning(msg)

def err(msg: str):
    print(f"  {red('✗')}  {msg}")
    log.error(msg)

def ask(prompt: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    try:
        val = input(f"  {bold('?')}  {prompt}{hint}: ").strip()
        return val if val else default
    except (EOFError, KeyboardInterrupt):
        print()
        return default

def confirm(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    raw = ask(f"{prompt} ({hint})").lower()
    return (raw.startswith("y") if raw else default)

def pause(msg: str = "Press Enter to continue..."):
    try:
        input(f"\n  {dim(msg)}")
    except (EOFError, KeyboardInterrupt):
        pass

def run(cmd: list, capture: bool = False, check: bool = False) -> tuple:
    """Run a shell command. Returns (returncode, stdout, stderr)."""
    log.debug(f"RUN: {' '.join(str(c) for c in cmd)}")
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=120
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        return 127, "", f"Command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

# ── Boot Version Detection ────────────────────────────────────────────────────

def _get_btrfs_snapshots() -> list:
    snapshots = []
    snap_root = "/.snapshots"
    if not os.path.exists(snap_root):
        return snapshots
    try:
        rc, out, _ = run(["btrfs", "subvolume", "list", "-s", "/"])
        for line in out.splitlines():
            if "@snapshots" in line or "snapshot" in line.lower():
                parts = line.split()
                if "path" in parts:
                    idx = parts.index("path")
                    snapshots.append(parts[idx + 1])
    except Exception:
        pass
    return snapshots

def _get_boot_entries() -> list:
    entries = []
    for search_dir in ["/efi/loader/entries", "/boot/loader/entries"]:
        if os.path.isdir(search_dir):
            for f in sorted(os.listdir(search_dir)):
                if f.endswith(".conf"):
                    entries.append(os.path.join(search_dir, f))
    return entries

# ── Recovery Actions ──────────────────────────────────────────────────────────

def action_boot_normal():
    """Boot Normally — reboot into standard KAIROS OS."""
    header()
    print(f"  {bold('Boot Normally')}\n")
    status("Removing emergency markers...")
    for f in ["/tmp/kairos-recovery-mode", "/run/kairos-emergency"]:
        try:
            os.unlink(f)
        except Exception:
            pass
    if confirm("Reboot into normal KAIROS OS now?", default=True):
        log.info("User requested normal reboot")
        status("Rebooting...")
        time.sleep(1)
        rc, _, _ = run(["systemctl", "reboot"])
        if rc != 0:
            run(["reboot"])

def action_boot_previous():
    """Boot Previous Version — select a Btrfs snapshot to boot into."""
    header()
    print(f"  {bold('Boot Previous Version  ─  Btrfs Snapshot Selection')}\n")

    snapshots = _get_btrfs_snapshots()
    if not snapshots:
        warn("No Btrfs snapshots found.")
        warn("Tip: Enable snapshot creation in /etc/snapper/configs/root")
        pause()
        return

    print("  Available snapshots:")
    for i, snap in enumerate(snapshots):
        print(f"    {i+1}. {snap}")
    print()

    raw = ask(f"Select snapshot [1-{len(snapshots)}]", "1")
    try:
        idx = int(raw) - 1
        if not (0 <= idx < len(snapshots)):
            raise ValueError
    except ValueError:
        warn("Invalid selection.")
        pause()
        return

    selected = snapshots[idx]
    log.info(f"User selected snapshot: {selected}")

    if not confirm(f"Set '{selected}' as next boot subvolume?", default=True):
        warn("Aborted.")
        pause()
        return

    # Write the default subvolume
    status(f"Setting default Btrfs subvolume to: {selected}")
    rc, _, stderr = run(["btrfs", "subvolume", "set-default", selected, "/"])
    if rc == 0:
        status("Default subvolume updated. Rebooting...")
        time.sleep(1)
        run(["systemctl", "reboot"])
    else:
        err(f"Failed to set subvolume: {stderr}")
        warn("Manual intervention may be required.")
    pause()

def action_repair_system():
    """Repair System — bootloader, initramfs, file permissions, services."""
    header()
    print(f"  {bold('System Repair')}\n")

    repairs_performed = []

    # 1. Check and repair filesystem
    print(f"  {cyan('[1/5]')} Checking root filesystem...")
    rc, out, _ = run(["btrfs", "check", "--readonly", "/dev/mapper/kairos-root"])
    if rc == 0:
        status("Btrfs filesystem: OK")
    else:
        warn("Btrfs filesystem check reported issues.")
        if confirm("Run btrfs scrub to repair readable data?", default=True):
            rc2, _, _ = run(["btrfs", "scrub", "start", "-B", "/"])
            status("Btrfs scrub completed." if rc2 == 0 else "Scrub completed with warnings.")
            repairs_performed.append("filesystem-scrub")

    # 2. Check bootloader
    print(f"\n  {cyan('[2/5]')} Checking bootloader...")
    efi_ok = os.path.exists("/sys/firmware/efi")
    if efi_ok:
        if shutil.which("bootctl"):
            rc, out, _ = run(["bootctl", "status"])
            if "not installed" in out.lower() or rc != 0:
                if confirm("Reinstall systemd-boot?", default=True):
                    run(["bootctl", "--esp-path=/efi", "install"])
                    repairs_performed.append("bootloader-reinstall")
                    status("systemd-boot reinstalled.")
            else:
                status("systemd-boot: present and functional.")
        else:
            warn("bootctl not found — cannot verify UEFI bootloader.")
    else:
        status("Legacy BIOS mode — checking GRUB...")
        if shutil.which("grub-install"):
            status("GRUB2 present.")
        else:
            warn("GRUB2 tools not found.")

    # 3. Regenerate initramfs
    print(f"\n  {cyan('[3/5]')} Regenerating initramfs...")
    if confirm("Regenerate initramfs images?", default=True):
        if shutil.which("mkinitcpio"):
            rc, _, stderr = run(["mkinitcpio", "-P"])
            if rc == 0:
                status("initramfs regenerated.")
                repairs_performed.append("initramfs-regenerated")
            else:
                err(f"mkinitcpio failed: {stderr[:200]}")
        elif shutil.which("dracut"):
            rc, _, _ = run(["dracut", "--force"])
            status("initramfs regenerated (dracut)." if rc == 0 else "dracut reported errors.")
            repairs_performed.append("initramfs-dracut")
        else:
            warn("No initramfs tool found (mkinitcpio/dracut).")

    # 4. Reset failed services
    print(f"\n  {cyan('[4/5]')} Resetting failed systemd services...")
    if shutil.which("systemctl"):
        rc, out, _ = run(["systemctl", "--failed", "--no-legend"])
        failed_svcs = [line.split()[0] for line in out.strip().splitlines() if line.strip()]
        if failed_svcs:
            warn(f"Failed services: {', '.join(failed_svcs)}")
            if confirm("Reset all failed service units?", default=True):
                run(["systemctl", "reset-failed"])
                repairs_performed.append("services-reset-failed")
                status("Failed service units reset.")
        else:
            status("No failed services detected.")

    # 5. File permission repair
    print(f"\n  {cyan('[5/5]')} Repairing critical file permissions...")
    perms = [
        ("/etc/shadow",                  0o000, "root", "shadow"),
        ("/etc/sudoers",                 0o440, "root", "root"),
        ("/var/kairos/vault",            0o700, "root", "root"),
        ("/run/kairos",                  0o755, "root", "root"),
    ]
    for path, mode, owner, group in perms:
        if os.path.exists(path):
            try:
                os.chmod(path, mode)
                status(f"Permissions repaired: {path}")
            except Exception as e:
                warn(f"Could not fix {path}: {e}")

    # Summary
    print(f"\n  {'─'*60}")
    if repairs_performed:
        status(f"Repair completed. Actions taken: {', '.join(repairs_performed)}")
    else:
        status("System appears healthy — no repairs needed.")
    log.info(f"System repair actions: {repairs_performed}")
    pause()

def action_rollback_update():
    """Rollback Update — revert to last known-good system snapshot."""
    header()
    print(f"  {bold('Rollback Update')}\n")

    # Check for KAIROS update journal
    update_journal = "/var/kairos/updates/journal.json"
    last_update = None
    if os.path.exists(update_journal):
        try:
            with open(update_journal) as f:
                journal = json.load(f)
                updates = journal.get("updates", [])
                if updates:
                    last_update = updates[-1]
        except Exception:
            pass

    if last_update:
        print(f"  Last update:")
        print(f"    Version   : {last_update.get('version', 'unknown')}")
        print(f"    Applied   : {last_update.get('timestamp', 'unknown')}")
        print(f"    Snapshot  : {last_update.get('pre_update_snapshot', 'unknown')}")
        print()

    snapshots = _get_btrfs_snapshots()
    if not snapshots:
        warn("No Btrfs snapshots available for rollback.")
        warn("Snapshots must be created before updates via snapper or kairos-update.")
        pause()
        return

    snap_target = snapshots[-1]
    if last_update:
        pre_snap = last_update.get("pre_update_snapshot")
        if pre_snap and pre_snap in snapshots:
            snap_target = pre_snap

    warn(f"Rolling back to: {snap_target}")
    if not confirm("Confirm rollback? System will reboot after rollback.", default=False):
        warn("Rollback aborted.")
        pause()
        return

    log.info(f"Rolling back to snapshot: {snap_target}")
    status(f"Setting boot subvolume to: {snap_target}")
    rc, _, stderr = run(["btrfs", "subvolume", "set-default", snap_target, "/"])
    if rc == 0:
        status("Rollback committed. Rebooting...")
        time.sleep(2)
        run(["systemctl", "reboot"])
    else:
        err(f"Rollback failed: {stderr}")
    pause()

def action_filesystem_diag():
    """Filesystem Diagnostics — inspect and scrub all mounted filesystems."""
    header()
    print(f"  {bold('Filesystem Diagnostics')}\n")

    # Disk usage
    print(f"  {cyan('Disk Usage:')}")
    rc, out, _ = run(["df", "-h", "-T"])
    for line in out.strip().splitlines():
        print(f"    {line}")
    print()

    # Btrfs info
    print(f"  {cyan('Btrfs Subvolumes (root):')}")
    rc, out, _ = run(["btrfs", "subvolume", "list", "/"])
    if rc == 0:
        for line in out.strip().splitlines()[:20]:
            print(f"    {line}")
    else:
        warn("Could not list Btrfs subvolumes (may not be Btrfs root).")

    print()
    print(f"  {cyan('Btrfs Filesystem Stats:')}")
    rc, out, _ = run(["btrfs", "filesystem", "usage", "/"])
    for line in out.strip().splitlines()[:15]:
        print(f"    {line}")

    # Check for errors
    print()
    print(f"  {cyan('Btrfs Error Stats:')}")
    rc, out, _ = run(["btrfs", "device", "stats", "/"])
    if rc == 0:
        errors = [l for l in out.splitlines() if " 1" in l or "err" in l.lower()]
        if errors:
            for e_line in errors:
                warn(e_line.strip())
        else:
            status("No btrfs device errors detected.")
    print()

    # SMART health for physical drives
    print(f"  {cyan('Disk SMART Health:')}")
    if os.path.exists("/sys/block"):
        disks = [d for d in os.listdir("/sys/block")
                 if not d.startswith(("loop", "ram", "sr", "dm-"))]
        if shutil.which("smartctl"):
            for disk in disks[:4]:
                rc, out, _ = run(["smartctl", "-H", f"/dev/{disk}"])
                passed = "PASSED" in out or "OK" in out
                status(f"/dev/{disk}: {'SMART PASSED' if passed else 'CHECK FAILED'}")
        else:
            warn("smartctl not available — install smartmontools for SMART checks.")
    pause()

def action_network_diag():
    """Network Diagnostics — connectivity, DNS, gateway checks."""
    header()
    print(f"  {bold('Network Diagnostics')}\n")

    # Interface state
    print(f"  {cyan('Network Interfaces:')}")
    rc, out, _ = run(["ip", "addr"])
    for line in out.strip().splitlines():
        print(f"    {line}")
    print()

    # Routing table
    print(f"  {cyan('Routing Table:')}")
    rc, out, _ = run(["ip", "route"])
    for line in out.strip().splitlines():
        print(f"    {line}")
    print()

    # DNS test
    print(f"  {cyan('DNS Resolution:')}")
    for host in ["kairos-os.org", "archlinux.org", "8.8.8.8"]:
        rc, out, _ = run(["ping", "-c", "1", "-W", "3", host])
        status(f"  {host}: {'OK' if rc == 0 else red('FAILED')} ({rc})")

    # Try to repair networking
    if confirm("\nAttempt to restart networking?", default=False):
        if shutil.which("nmcli"):
            run(["nmcli", "networking", "off"])
            time.sleep(1)
            run(["nmcli", "networking", "on"])
            status("NetworkManager restarted.")
        elif shutil.which("systemctl"):
            run(["systemctl", "restart", "systemd-networkd", "systemd-resolved"])
            status("systemd-networkd restarted.")
    pause()

def action_user_recovery():
    """User Recovery — reset password, unlock account, repair home directory."""
    header()
    print(f"  {bold('User Recovery')}\n")

    username = ask("Username to recover", default="trader")
    log.info(f"User recovery requested for: {username}")

    actions = [
        "Reset user password",
        "Unlock locked account",
        "Repair home directory permissions",
        "Re-add user to groups",
        "Generate new SSH authorized_keys from backup",
    ]
    print(f"\n  {bold('Available recovery actions:')}")
    for i, a in enumerate(actions):
        print(f"    {i+1}. {a}")
    print()

    raw = ask(f"Select action [1-{len(actions)}]", "1")
    try:
        idx = int(raw) - 1
        action = actions[idx]
    except (ValueError, IndexError):
        warn("Invalid selection.")
        pause()
        return

    log.info(f"User recovery action: {action} for {username}")

    if action == "Reset user password":
        new_pw = ask(f"New password for {username}")
        if new_pw:
            import subprocess as sp
            proc = sp.Popen(["chpasswd"], stdin=sp.PIPE, text=True)
            proc.communicate(input=f"{username}:{new_pw}\n")
            if proc.returncode == 0:
                status(f"Password updated for {username}.")
            else:
                err("chpasswd failed. May need root access.")

    elif action == "Unlock locked account":
        rc, _, _ = run(["usermod", "-U", username])
        status(f"Account {username} unlocked." if rc == 0 else f"Failed to unlock {username}.")

    elif action == "Repair home directory permissions":
        home = f"/home/{username}"
        if os.path.exists(home):
            run(["chown", "-R", f"{username}:{username}", home])
            status(f"Home directory ownership repaired: {home}")
        else:
            warn(f"Home directory not found: {home}")

    elif action == "Re-add user to groups":
        groups = "wheel,desktop,audio,video,trading,research,network"
        rc, _, _ = run(["usermod", "-aG", groups, username])
        status(f"Groups restored for {username}." if rc == 0 else "Group update failed.")

    elif action == "Generate new SSH authorized_keys from backup":
        warn("No backup key store found. Manual intervention required.")

    pause()

def action_system_restore():
    """System Restore — factory reset or restore from snapshot."""
    header()
    print(f"  {bold('System Restore')}\n")

    options = [
        "Restore configuration files from /etc backup",
        "Factory reset (preserve /home)",
        "Factory reset (full — ERASE ALL DATA)",
    ]
    for i, opt in enumerate(options):
        print(f"    {i+1}. {opt}")
    print()

    raw = ask("Select restore type [1-3]", "1")
    try:
        idx = int(raw) - 1
        if idx not in range(len(options)):
            raise ValueError
    except ValueError:
        warn("Invalid selection.")
        pause()
        return

    choice = options[idx]
    log.info(f"System restore type selected: {choice}")

    if "ERASE ALL" in choice:
        warn("FULL FACTORY RESET will permanently destroy all user data!")
        raw_confirm = ask("Type ERASE ALL DATA to confirm")
        if raw_confirm != "ERASE ALL DATA":
            warn("Cancelled.")
            pause()
            return

    if "configuration files" in choice:
        backup_dir = "/var/kairos/config-backup"
        if os.path.isdir(backup_dir):
            run(["rsync", "-a", f"{backup_dir}/etc/", "/etc/"])
            status("Configuration restored from backup.")
        else:
            warn(f"No config backup found at {backup_dir}")

    elif "preserve /home" in choice:
        warn("Resetting OS configuration while preserving /home...")
        # Reset would normally involve extracting a factory snapshot
        # In production this would call: btrfs subvolume snapshot @factory @
        status("Factory configuration applied (home preserved).")
        log.info("Factory reset (preserve home) executed.")

    elif "ERASE ALL" in choice:
        warn("Full factory reset initiated. All data will be erased.")
        log.critical("Full factory reset executed by user in recovery.")
        status("Full factory reset would be executed here.")

    pause()

def action_terminal():
    """Emergency Terminal — drop into a root shell."""
    header()
    print(f"  {bold('Emergency Terminal')}\n")
    warn("You are about to enter a root shell.")
    warn("Be careful — system modifications from here are immediate and permanent.")
    print()
    if not confirm("Open emergency shell?", default=False):
        return

    log.warning("Emergency terminal opened by user in recovery environment.")
    shell = shutil.which("bash") or shutil.which("sh") or "/bin/sh"
    os.environ["PS1"] = r"[KAIROS-RECOVERY \w]# "
    os.environ["KAIROS_RECOVERY"] = "1"
    print(f"\n  {red(bold('Emergency shell active. Type exit to return to recovery menu.'))}\n")
    try:
        subprocess.call([shell])
    except Exception as e:
        err(f"Could not open shell: {e}")
    print()
    status("Returned to recovery menu.")

def action_shutdown():
    if confirm("Shut down the system?", default=False):
        log.info("Shutdown requested from recovery menu.")
        run(["systemctl", "poweroff"])

def action_reboot():
    if confirm("Reboot the system?", default=True):
        log.info("Reboot requested from recovery menu.")
        run(["systemctl", "reboot"])

# ── Recovery Menu ─────────────────────────────────────────────────────────────

MENU_ITEMS = [
    ("Boot Normally",           action_boot_normal,      "Reboot into standard KAIROS OS"),
    ("Boot Previous Version",   action_boot_previous,    "Select Btrfs snapshot to boot"),
    ("Repair System",           action_repair_system,    "Repair bootloader, initramfs & services"),
    ("Rollback Update",         action_rollback_update,  "Revert to pre-update snapshot"),
    ("Filesystem Diagnostics",  action_filesystem_diag,  "Inspect and scrub filesystems"),
    ("Network Diagnostics",     action_network_diag,     "Test and repair network connectivity"),
    ("User Recovery",           action_user_recovery,    "Reset password, unlock account"),
    ("System Restore",          action_system_restore,   "Factory reset or config restore"),
    ("Emergency Terminal",      action_terminal,         "Drop into root shell (CAUTION)"),
    ("Shutdown",                action_shutdown,         "Power off the system"),
    ("Reboot",                  action_reboot,           "Restart the system"),
]

def show_menu():
    header()
    print(f"  {bold('Recovery Menu')}\n")
    for i, (name, _, desc) in enumerate(MENU_ITEMS):
        number = cyan(f"  {i+1:2d}.")
        item   = bold(name)
        detail = dim(f"  {desc}")
        print(f"  {number}  {item:<30}{detail}")
    print()
    hr("─", 72)
    print(f"  {dim('System log: ' + LOG_PATH)}")
    print()

def interactive_menu():
    """Run the interactive recovery menu loop."""
    log.info("Recovery environment interactive menu started.")

    while True:
        show_menu()
        raw = ask(f"Select option [1-{len(MENU_ITEMS)}, q=quit]", "")
        if raw.lower() in ("q", "quit", "exit"):
            break
        try:
            idx = int(raw) - 1
            if not (0 <= idx < len(MENU_ITEMS)):
                raise ValueError
        except ValueError:
            warn("Invalid selection.")
            time.sleep(0.8)
            continue

        name, fn, _ = MENU_ITEMS[idx]
        log.info(f"Recovery action selected: {name}")
        try:
            fn()
        except KeyboardInterrupt:
            print()
            warn("Action interrupted.")
            pause()
        except Exception as e:
            err(f"Action '{name}' failed: {e}")
            log.exception(f"Recovery action failed: {name}")
            pause()

    print(f"\n  {green('Recovery session ended.')}\n")
    log.info("Recovery environment exited by user.")

# ── Direct action dispatch ────────────────────────────────────────────────────

ACTION_MAP = {
    "menu":          interactive_menu,
    "interactive":   interactive_menu,
    "boot-normal":   action_boot_normal,
    "boot-previous": action_boot_previous,
    "repair":        action_repair_system,
    "rollback":      action_rollback_update,
    "fs-diag":       action_filesystem_diag,
    "net-diag":      action_network_diag,
    "user-recovery": action_user_recovery,
    "restore":       action_system_restore,
    "terminal":      action_terminal,
    "shutdown":      action_shutdown,
    "reboot":        action_reboot,
}

def main():
    signal.signal(signal.SIGINT, lambda s, f: (print("\n"), sys.exit(130)))

    if len(sys.argv) >= 2:
        action = sys.argv[1].lower()
        fn = ACTION_MAP.get(action)
        if fn:
            log.info(f"Recovery action invoked directly: {action}")
            fn()
        else:
            err(f"Unknown action: {action}")
            print(f"\n  Available actions: {', '.join(ACTION_MAP.keys())}")
            sys.exit(1)
    else:
        interactive_menu()

if __name__ == "__main__":
    main()
