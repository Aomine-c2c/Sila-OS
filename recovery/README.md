# KAIROS OS Recovery Environment

The KAIROS recovery environment is a standalone rescue system that remains
operational even when the normal desktop, compositor, or trading stack fails.

---

## Access

### At boot (bootloader menu)

Select **"KAIROS OS Recovery"** from the systemd-boot or GRUB2 menu.

This boots with:
```
kairos.mode=recovery single nomodeset
```

### From running system

```bash
kairos recovery menu       # Interactive recovery menu
kairos recovery status     # Recovery subsystem status
```

### Emergency kernel cmdline

Append `single` or `emergency` to the kernel command line at boot.

---

## Recovery Menu

| Option | Description |
|--------|-------------|
| **Boot Normally** | Reboot into standard KAIROS OS |
| **Boot Previous Version** | Select a Btrfs snapshot to boot into |
| **Repair System** | Bootloader + initramfs + service repair |
| **Rollback Update** | Revert to pre-update snapshot |
| **Filesystem Diagnostics** | Inspect and scrub filesystems |
| **Network Diagnostics** | Test and repair network connectivity |
| **User Recovery** | Reset password, unlock account, fix groups |
| **System Restore** | Factory reset or configuration restore |
| **Emergency Terminal** | Root shell (use with extreme caution) |
| **Shutdown** | Power off |
| **Reboot** | Restart |

---

## Recovery Procedures

### Boot Repair

**Symptoms:** System fails to boot, GRUB/systemd-boot missing, kernel panic.

```
Recovery Menu → Repair System
```

Manual steps if menu unavailable:
```bash
# Mount root
cryptsetup open /dev/sda3 kairos-root
mount -o subvol=@ /dev/mapper/kairos-root /mnt
mount /dev/sda2 /mnt/boot
mount /dev/sda1 /mnt/efi

# Chroot
arch-chroot /mnt

# Reinstall bootloader
bootctl --esp-path=/efi install

# Regenerate initramfs
mkinitcpio -P

exit
reboot
```

---

### Update Rollback

**Symptoms:** System broken after update, services failing after upgrade.

```
Recovery Menu → Rollback Update
```

Manual steps:
```bash
# List available snapshots
btrfs subvolume list /

# Set previous snapshot as default
btrfs subvolume set-default <snapshot-path> /

# Reboot
systemctl reboot
```

---

### Filesystem Diagnostics

**Symptoms:** Filesystem errors, data corruption, read-only mounts.

```
Recovery Menu → Filesystem Diagnostics
```

Manual steps:
```bash
# Check Btrfs (read-only)
btrfs check --readonly /dev/mapper/kairos-root

# Scrub to repair readable data
btrfs scrub start -B /

# View device errors
btrfs device stats /

# Check SMART health
smartctl -H /dev/sda
```

---

### Configuration Rollback

**Symptoms:** Bad configuration change broke service or system.

```bash
# View config backup
ls /var/kairos/config-backup/

# Restore single file
cp /var/kairos/config-backup/etc/some.conf /etc/some.conf

# Or full restore (Recovery Menu → System Restore → Config restore)
```

---

### User Recovery

**Symptoms:** Cannot log in, locked account, forgotten password.

```
Recovery Menu → User Recovery
```

Manual steps:
```bash
# Reset password
chpasswd <<< "trader:newpassword"

# Unlock account
usermod -U trader

# Restore groups
usermod -aG wheel,desktop,audio,video,trading,research trader

# Fix home permissions
chown -R trader:trader /home/trader
```

---

### Service Repair

**Symptoms:** Services stuck in failed state, KAIROS services won't start.

```bash
# List failed services
systemctl --failed

# Reset failed units
systemctl reset-failed

# Restart specific service
systemctl restart kairos-riskd

# View service logs
journalctl -u kairos-riskd -n 100
```

---

### Network Diagnostics

**Symptoms:** No internet, broker disconnect, VPN failure.

```
Recovery Menu → Network Diagnostics
```

Manual steps:
```bash
# Check interfaces
ip addr
ip route

# Test connectivity
ping -c3 8.8.8.8
ping -c3 archlinux.org

# Restart networking
systemctl restart NetworkManager
# or
systemctl restart systemd-networkd systemd-resolved

# Check DNS
resolvectl status
```

---

### System Restore

> [!CAUTION]
> Factory reset destroys all user data that is not explicitly preserved.

**Options:**

| Option | Data Loss | Use Case |
|--------|-----------|----------|
| Config restore from backup | None | Bad config change |
| Factory reset (preserve /home) | OS config only | Major OS corruption |
| Full factory reset | All data | Complete reinstall without disk reformat |

---

## Recovery Boot Entry (systemd-boot)

`/efi/loader/entries/kairos-recovery.conf`:
```ini
title   KAIROS OS Recovery
linux   /vmlinuz-kairos
initrd  /initramfs-kairos-fallback.img
options rd.luks.name=<UUID>=kairos-root root=/dev/mapper/kairos-root \
        rootflags=subvol=@ rw single kairos.mode=recovery
```

---

## Recovery Boot Entry (GRUB2)

`/boot/grub/grub.cfg` includes:
```
menuentry "KAIROS OS — Recovery Environment" {
    linux  /boot/vmlinuz-kairos kairos.mode=recovery single nomodeset
    initrd /boot/initramfs-kairos-fallback.img
}
```

---

## Logs

| Log | Location |
|-----|----------|
| Recovery session | `/var/log/kairos/recovery.log` |
| Boot log | `journalctl -b` |
| System service log | `journalctl -u kairos-*.service` |
| Kernel log | `dmesg` |

---

## Invariants

- The recovery environment does **not** import trading, AI, or desktop libraries
- Recovery runs on **tty1** regardless of desktop state
- All recovery actions are logged to `/var/log/kairos/recovery.log`
- Destructive operations (factory reset) require typed confirmation
- Recovery is available on every KAIROS ISO, live system, and installed system
