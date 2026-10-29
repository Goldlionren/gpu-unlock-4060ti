# Security and recovery — frozen deployment

Secure Boot remained disabled throughout. No EFI binary, firmware key, BootOrder/BootNext or VBIOS image was modified. The stock NVIDIA binaries remain intact. DKMS installed the local module; its signing does not establish trust if Secure Boot is later enabled.

The exact board and existing authorized Thunderbolt enclosure are checked before transaction activity. The full 1 MiB PROM digest and FWSEC geometry are mandatory. No global Thunderbolt authorization was added. Unknown/absent/bound devices skip before writes. A failed preflight was observed to continue to stock NVIDIA and normal boot. A failed transaction with unsafe handoff withholds GPU initialization and never enters an automatic reset loop; it cannot promise stock operation after every possible hardware fault.

Original running-kernel and initramfs copies are retained in `/var/lib/gpu-unlock-sm1/original-boot`, original configuration under `original-config`, and managed changes in the manifest/backups. `gpu-unlock disable` removes next-boot activation and rebuilds initramfs. `gpu-unlock rollback` restores managed files and removes this DKMS package. Neither command resets/unbinds the current GPU. These controls were tested in an isolated filesystem; the owner ended testing before a real disable/restore boot.

For local emergency recovery, see [exact procedure](local-recovery-prom-fix.md). It restores the saved initramfs and removes the NVIDIA install override/enabled flag. Do not assume a secondary GRUB entry or a systemd watchdog can recover a pre-network kernel hang. Physical access was the independent recovery option during testing; no remote power controller was demonstrated.

The onboard network interface is independent of the Thunderbolt tunnel, and SSH was healthy after the verified boots. That does not isolate the host from every kernel/DMA failure. No guaranteed unattended hardware recovery is claimed.

Raw diagnostics, PROM dumps, firmware payloads and signing keys are excluded from publication. The frozen source intentionally includes this deployment's non-secret paths, account, enclosure UUID and route-check destination because changing those would change the tested deployment. No private keys or authentication tokens are included.
