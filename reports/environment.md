# Environment audit — initial read-only phase, 2026-10-29

Historical discovery record. Subsequent installation and successful cold/warm tests are documented in release-acceptance.md; initial statements below do not describe final deployment state.

Read-only observations. Raw command output, stderr, timestamps and sysfs snapshots are under `logs/raw/20261028T225900Z` (sandbox) and `logs/raw/20261028T225933Z` (host access). Sandbox NVIDIA/network/D-Bus failures were resolved by running the same read-only collector outside the sandbox. They are not host failures.

| Item | Observation |
|---|---|
| Host | Silver Moon 1; local hostname omitted |
| OS/kernel | Ubuntu 24.04.4 LTS; `7.0.0-38-generic` x86_64 |
| Boot | UEFI; BootCurrent `0002`; BootOrder `0002,2001,2002,2003`; no BootNext reported |
| Ubuntu path | `\EFI\ubuntu\shimx64.efi`; original path untouched |
| Secure Boot | Disabled; only Canonical certificate shown in enrolled MOK list |
| Signing | `/var/lib/shim-signed/mok/MOK.der` exists but `mokutil --test-key` says not enrolled; private key contents were not read |
| ESP | `/dev/nvme1n1p1`, FAT, GPT ESP; audit mount read-only; EFI directory listing denied |
| GRUB | Default entry 0, hidden timeout style, timeout 10; quiet splash; no unlock options |
| Boot packages | shim-signed 1.58+15.8-0ubuntu1; signed GRUB 1.202.5+2.12-1ubuntu7.3; initramfs-tools 0.142ubuntu25.8; DKMS 3.0.11 |
| GPU | NVIDIA RTX 4060 Ti, 16380 MiB reported; AD106; PCI `10de:2803`, subsystem `1462:5174`, revision a1 |
| Current BDF | `0000:05:00.0` (audio function .1 is 10de:22bd) |
| VBIOS/board | `95.06.34.00.F3`; board ID `0x500`; part `2803-350-A1`; serial unavailable |
| Driver/CUDA | Stock proprietary 580.178.04, GSP 580.178.04; CUDA toolkit 13.0.88; PyTorch 2.13.0+cu130 in existing Comfy environment |
| BARs | BAR0 0x52000000–0x52ffffff; BAR1 0x6000000000–0x600fffffff; BAR3 0x6010000000–0x6011ffffff; I/O BAR5 0x5000–0x507f |
| PCI link | Idle observed 2.5 GT/s x4; endpoint maximum 16 GT/s x8. Idle report is not measured Thunderbolt throughput |
| Reset methods | `flr bus` exposed; neither invoked |
| Display/use | boot_vga=0; no attached display; NVIDIA bound; existing Python GPU client (~120 MiB) and another small client. Do not unbind/reset |
| IOMMU | Intel DMAR active; GPU and audio share group 20; Thunderbolt DMA protection=1 |
| Network | Onboard enp0s31f6 has default route; NetworkManager active; SSH service and socket active, port 22 listening |
| Rescue | No demonstrated BMC/IPMI, independent console or out-of-band power/recovery path; PXE entries alone prove none |

## Thunderbolt and boot timing

PCI path: `00:07.0 → 03:00.0 → 04:01.0 → 05:00.0`. Controller NHI is `00:0d.2`, Intel Gen12, generation 4. Attached Adaptertek “Tamales2 85W test” reports generation 3; UUID is recorded in the local snapshot. Domain security is `user`, IOMMU DMA protection enabled, enclosure authorized=1, boot=0. Per-direction speed attribute is 20 Gb/s; do not equate this attribute with aggregate usable bandwidth. `boltd` reports boot ACL unsupported and authorizes the known device under its IOMMU policy.

Current boot kernel monotonic timeline:

- 0.530 s: GPU enumerated with assigned BARs.
- 2.424 s: Thunderbolt enclosure discovered.
- 4.207 s: GPU enumerated again, BARs reassigned by 4.211 s.
- 4.795 s: NVIDIA module begins loading; 4.912 s: binds GPU.
- 6.982 s: NVIDIA DRM initialized.

Thus Linux PCI enumeration precedes NVIDIA initialization, but early topology changes invalidate a one-shot early address assumption. Userspace boltd authorization is also observed. Exact initramfs/rootfs authorization causality needs additional monotonic boltd/udev correlation. Neither Linux enumeration at 0.53 s nor boot=0 establishes addressability before ExitBootServices. UEFI availability remains unproven and is not needed for the preferred strategy.

Current and previous boot logs were saved; both contain 05:00.0. This is limited history, not proof of cold-boot or hotplug BDF stability. No reboot/hotplug was performed. Production identification must rediscover the BDF using exact identity and verified enclosure association, then recheck under the PCI device lock before writes.

The live initramfs includes Thunderbolt; its listing did not show the NVIDIA compute/display modules. Upstream module inclusion could therefore execute before the final Thunderbolt enumeration. Ubuntu init-top executes before load_modules, and udev may already be active: packaging order alone cannot prove exclusive pre-driver ownership.

## Unresolved evidence

No board PROM dump/hash or initial selector/WPR2 capture was taken; no BAR mapping or hardware write was performed. EFI contents and protected configuration were not bypassed. SSH is locally active; an external reconnection and independent rescue have not been tested. Cold power state of the externally powered enclosure is unknown. Preserve IOMMU and existing Thunderbolt security.
