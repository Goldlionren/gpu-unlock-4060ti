#!/usr/bin/env python3
"""Read-only diagnostics; records failures and never invokes sudo or writes sysfs."""
import datetime, json, pathlib, subprocess
root = pathlib.Path(__file__).resolve().parents[1]
out = root / 'logs/raw' / datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out.mkdir(parents=True)
commands = {
'host': 'hostnamectl; uname -a; cat /etc/os-release; cat /proc/cmdline; uptime; id',
'boot': 'mokutil --sb-state; mokutil --list-enrolled; efibootmgr -v; findmnt /boot/efi; lsblk -o NAME,TYPE,FSTYPE,PARTTYPE,MOUNTPOINTS; cat /etc/default/grub; cat /boot/grub/grubenv; ls -l /boot/efi/EFI; dpkg-query -W shim-signed grub-efi-amd64-signed initramfs-tools dkms; ls -l /var/lib/shim-signed/mok /var/lib/dkms',
'pci': 'lspci -Dnnk; lspci -tv; lspci -Dvvnn',
'gpu': 'nvidia-smi -q; nvidia-smi --query-gpu=uuid,pci.bus_id,name,vbios_version,driver_version,memory.total --format=csv; cat /proc/driver/nvidia/version; nvcc --version; lsmod; fuser -v /dev/nvidia* /dev/dri/*; ps -eo pid,comm | rg "Xorg|Xwayland|wayland|cuda|nvidia"',
'network': 'ip -brief address; ip route; systemctl is-active ssh sshd NetworkManager systemd-networkd; systemctl is-enabled ssh ssh.socket; systemctl cat ssh.service ssh.socket; ss -ltn; cat /etc/ssh/sshd_config; ls -l /etc/ssh/sshd_config.d; systemctl is-active tailscaled; ls -l /dev/ipmi*',
'boot_history': 'journalctl --list-boots; journalctl -b -k --no-pager -o short-monotonic; journalctl -b -1 -k --no-pager -o short-monotonic',
'initramfs': 'lsinitramfs /boot/initrd.img-$(uname -r); cat /etc/initramfs-tools/modules; rg -n "nvidia|nouveau|thunderbolt|gpu.unlock" /etc/modprobe.d /etc/modules-load.d /etc/initramfs-tools /etc/udev/rules.d; ls -ld /lib/modules/$(uname -r)/build; modinfo nvidia; modinfo gpu_unlock',
'bolt': 'boltctl list; boltctl domains; systemctl status bolt --no-pager; journalctl -b -u bolt --no-pager; ls -l /var/lib/boltd',
}
results={}
for name,cmd in commands.items():
    try:
        p=subprocess.run(['bash','-c',cmd],capture_output=True,text=True,timeout=60)
        result={'command':cmd,'returncode':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
    except subprocess.TimeoutExpired as e:
        result={'command':cmd,'error':'timeout','stdout':str(e.stdout),'stderr':str(e.stderr)}
    (out/(name+'.json')).write_text(json.dumps(result,indent=2)); results[name]=result.get('returncode','timeout')
snapshot={'pci':[], 'thunderbolt':[], 'iommu_groups':[]}
for p in pathlib.Path('/sys/bus/pci/devices').glob('*'):
    item={'bdf':p.name,'path':str(p.resolve())}
    for key in ['vendor','device','subsystem_vendor','subsystem_device','class','revision','resource','current_link_speed','current_link_width','max_link_speed','max_link_width','reset_method','boot_vga']:
        try: item[key]=(p/key).read_text().strip()
        except OSError as e: item[key]={'error':str(e)}
    for key in ['driver','iommu_group']:
        item[key]=str((p/key).resolve()) if (p/key).exists() else None
    snapshot['pci'].append(item)
for p in pathlib.Path('/sys/bus/thunderbolt/devices').glob('*'):
    item={'name':p.name,'path':str(p.resolve())}
    for key in ['authorized','security','unique_id','device_name','vendor_name','generation','iommu_dma_protection','boot','rx_speed','tx_speed']:
        try: item[key]=(p/key).read_text().strip()
        except OSError: pass
    snapshot['thunderbolt'].append(item)
snapshot['iommu_groups']=[str(p) for p in pathlib.Path('/sys/kernel/iommu_groups').glob('*')]
(out/'sysfs.json').write_text(json.dumps(snapshot,indent=2))
(out/'summary.json').write_text(json.dumps(results,indent=2))
print(out)
