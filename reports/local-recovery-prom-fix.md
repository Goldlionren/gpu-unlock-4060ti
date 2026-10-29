# Local recovery for this test

Normal cold test: save work, run `sudo systemctl poweroff`, wait until laptop has fully shut down. Switch off/disconnect AC input to the eGPU enclosure until it is fully unpowered. Keep the Thunderbolt cable connected. Restore enclosure power, then press the laptop power button. Do not unplug power while Ubuntu is running. This tests host reboot with fresh external-GPU power; it does not remove the laptop's internal battery.

Allow up to two minutes for Ubuntu/network/verification. If the laptop remains operational but GPU initialization fails, keep it running: use SSH or the local terminal to preserve logs and disable the next-boot attempt:

```sh
sudo /usr/bin/python3 /home/james/projects/gpu-unlock-4060ti-linux/scripts/admin.py disable
```

If Ubuntu cannot reach a terminal, use local GRUB Advanced options/recovery or a known-good installed kernel. In the root recovery shell, restore the saved pre-project initramfs:

```sh
mount -o remount,rw /
# If /boot is a separate filesystem and is not mounted, mount /boot first.
rm -f /etc/modprobe.d/gpu-unlock-sm1.conf /etc/gpu-unlock-sm1/enabled
cp /var/lib/gpu-unlock-sm1/original-boot/initrd.img-7.0.0-38-generic /boot/initrd.img-7.0.0-38-generic
sync
```

Do not regenerate this restored initramfs before diagnosis. Firmware/EFI and stock NVIDIA binaries have not been replaced. These recovery commands are a local emergency procedure and can cause manifest drift; the next maintenance session should reconcile it before reinstalling. No software procedure here guarantees recovery from a pre-network kernel hang. Physical access remains the recovery mechanism for this test.
