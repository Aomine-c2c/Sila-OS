@echo -off
cls
echo "Starting KAIROS Adaptive Trading Operating System..."
vmlinuz-kairos initrd=initramfs-kairos.img root=LABEL=KAIROS_ROOT rootflags=subvol=@ ro quiet loglevel=3 kairos.mode=normal efi=runtime
