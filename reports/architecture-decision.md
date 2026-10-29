# Architecture decision — deployed Linux path

The frozen solution uses the stock NVIDIA driver, a guarded local fork of gpu-unlock-ada main, DKMS packaging and initramfs inclusion. EFI execution was not pursued.

The actual ordering point is the `install nvidia` modprobe action. Its synchronous helper runs before NVIDIA registers its PCI driver, dynamically locates the exact board behind the expected root-port path and already-authorized enclosure, and invokes the unlock module once. A lock and per-boot attempted marker prevent duplicate execution. Existing IOMMU/Thunderbolt authorization protections remain intact; no arbitrary sleep or global authorization is introduced.

The kernel rechecks identity, ownership, power, chip/WPR2/selectors and complete PROM state while holding the PCI device lock. It temporarily enables only memory decoding if hotplug left that bit clear and verifies restoration before the upstream transaction. The transaction revalidates PROM, executes the upstream firmware mechanism, verifies selectors, runs FLR and validates handoff state. A guard rejection allows stock driver loading. An unsafe transaction result withholds the GPU driver; it does not repeatedly reset or block SSH through a systemd dependency.

The initramfs hook includes the coordinator, profile, module and firmware but does not force-load the module. The tested initramfs did not contain the NVIDIA compute module; the root filesystem's driver loading passed through the coordinator. The boot verifier is an independent non-root oneshot service; it observes GPU readiness with a bound and records results/benchmarks after successful transactions. Its success does not imply a guarantee against kernel hangs.

One cold boot and one subsequent warm reboot verified this sequence. BDF was unchanged in those observations, but matching is dynamic. A device arriving after NVIDIA registration is left stock. Kernel upgrades, unusual direct driver insertion, suspend/resume and hotplug have not been qualified. No redesign or additional boot mutation was performed for publication.

The owner selected this tested configuration for release and waived additional hardware cycles. See release-acceptance.md for the exact acceptance boundary and source-lock.json for upstream revisions.
