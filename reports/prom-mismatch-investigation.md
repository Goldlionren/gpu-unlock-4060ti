# PROM mismatch: diagnosis and corrected admission profile

## Hardware evidence — 2026-10-29

Diagnostic boot `5de2cb11-35c6-4a28-9046-e6185d9eca6b` preserved two pre-driver 1,048,576-byte snapshots. Both SHA-256 digests are `c74f5e73f6d9d71f8b9a6942c7f8559a1c2f9a10e9bbacfb49e6ac93911579f2`. The configured expected digest was `2abeed7805fd3003b614c83e78815e921cfb135b253355469ba67e456013a942`, from the original post-driver capture. Neither image is truncated; every byte of the two early reads agrees.

Device: `10de:2803 / 1462:5174`, revision a1, BDF `0000:05:00.0`, chip `196000a1`. Early SS0=`40271143`, SS1=3, WPR2 high=0, NVIDIA unbound. Original capture had NVIDIA bound and WPR2 high=67087872. Both read the full BAR0 `[0x300000,0x400000)` NV_PROM_DATA aperture. Original: read-only resource0 mmap/Python slicing. Early: pci_iomap/memcpy_fromio. Neither used sysfs rom, pci_map_rom, nvflash or a downloaded VBIOS file. Diagnostic sysfs files expose saved RAM, not live MMIO.

`main.c:unlock_one` calls `silver_moon_guard` before the upstream transaction. `silver_moon_prom` hashes the full buffer and returns -EBADMSG (-74) on mismatch. That propagates to transaction_result while handoff_safe stays Y. No payload, selector write or FLR ran. The first failed boot `eed9b8ad-e53f-4170-a2ee-f6954592cc2c` did not retain its observed bytes/hash; its exact observed digest remains unknown. This diagnostic boot reproduces the rejection with complete evidence.

Ubuntu, SSH service/socket, NVIDIA 580.178.04 and CUDA remain operational. Automatic FP16/BF16 smoke tests pass with zero error. RM reports stock half rate. This verifies rejection/fallback, not unlocking.

## Exact differences and independent firmware validation

- First difference: `0xD6C00` (879,616); 124,805 differing bytes, all after the complete ROM chain. No differences before that offset.
- Independent Python header walker and upstream C parser agree on four images: `[0,0xFC00)`, `[0xFC00,0x24C00)`, `[0x24C00,0x2AC00)`, `[0x2AC00,0x9A200)`. Header image lengths and last-image flag determine the end; it was not chosen to exclude a mismatch.
- All 631,296 firmware-chain bytes match the original trusted capture. Chain SHA-256: `387bc9ae39eb78f7d61e89299eeb2c57624389bd1b89973ada5692e03ad8d126`.
- Early `[0x9A200,0x100000)` is entirely FF (417,280 bytes). Original `[0x9A200,0xD6C00)` is also FF, but later contains additional data. Original zero/FF totals: 162,243/308,080; early: 119,825/432,885. Full spans and differing blocks: `logs/prom-diagnostic-comparison.json`.
- Original tail has NVGI headers at `0xD6C00` and `0xD8C00`. First IFR v3 header total-data size is `0x1FD8`; flash-status value `0x4000` locates RFRD at `0xDBC00`. Its PCI ROM offset `0x9400` and ROM length `0x9A200` independently corroborate chain length. Original bytes at `0xE0000` repeat the VBIOS beginning for `0x16C00` bytes. Early tail contains none of this data.
- VBIOS `95.06.34.00.F3` and MSI label `MSINV517MH.221` are unchanged within the firmware chain.
- Both C parses give descriptor `0x4581C`, signatures at `0x45848` (768 bytes), image at `0x45B48` (size `0x10500`), IMEM `0xF700`, DMEM `0xD80`, PKC offset `0xB24`, interface `0x1C`, engine `0x400`, ucode 9, two signatures/version mask 3. The lookup table near `0x99FB6` is included. Parser bounds checks pass.

The software defect is using the post-driver whole-aperture hash as the pre-driver admission baseline. Captures prove different tails outside identical firmware. They do **not** establish whether shadow selection, address wrapping or access width causes that difference; these remain hypotheses. Neither full aperture dump is claimed to be an independently read physical SPI image. No live BAR access, ROM decoding, driver unload or reset was performed during this investigation.

Linux documents NVGI/IFR and transparent hardware ROM-offset application in [VBIOS layout](https://raw.githubusercontent.com/torvalds/linux/master/Documentation/gpu/nova/core/vbios.rst). Nouveau explicitly controls shadow selection and reads dwords in [shadowrom.c](https://raw.githubusercontent.com/torvalds/linux/master/drivers/gpu/drm/nouveau/nvkm/subdev/bios/shadowrom.c). These support possible view differences, not proof of the transition on this board. Standard [pci_map_rom](https://raw.githubusercontent.com/torvalds/linux/master/drivers/pci/rom.c) can enable decoding and delimit a PCI ROM view; it was not used here.

## Actual fix

`src/pre-driver-prom.json` pins the complete reviewed early 1 MiB image. Provenance is checked against every byte of the original header-delimited firmware, matching repeated early reads, independent header geometry and C FWSEC parsing. This does not accept a digest merely because the GPU returned it. Original capture remains unmodified.

`scripts/prom_profile.py` verifies this evidence offline. `scripts/admin.py` now installs that reviewed early hash instead of copying the post-driver capture hash. It verifies all three full evidence hashes, ROM bounds, firmware equivalence and FWSEC geometry before installation. It never learns a new hash automatically.

`src/kernel/board_guard.h` retains full SHA comparison for both 1 MiB reads and again before FWSEC use. There is no ignored region, shortened hash, dual-hash allowlist or wildcard. It now also parses ROM/FWSEC and checks this board's exact geometry **before** entering the upstream transaction. Thunderbolt/NVIDIA ordering and upstream firmware/reset logic are unchanged.

## Tests and next hardware step

Current-kernel build passes. Actual C guard tests cover identities, bound/power rejection, decode restoration, firmware/signature/tail corruption, unstable repeated reads and malformed/unexpected FWSEC even with matching recalculated SHA. 25 Python tests pass. Staged install/enable/disable/rollback passes.

Upstream generic C VBIOS tests pass against the local parser. An initial optional board-fixture invocation failed because it asserts three signatures/mask 7; this board has two/mask 3 in both captures. No assertion was weakened: the generic suite ran without that foreign-board fixture; dedicated C guard tests and full geometry checks cover this board. Failed invocation remains in `logs/prom-fix-vbios-tests.log`.

Corrected build awaits local administrator install+enable, then installed/initramfs inspection before controlled cold boot. Cold-state compatibility and actual unlock/FLR/performance remain **unverified**. A different cold-state hash must reject; no automatic repinning.

Original kernel/initramfs remain under `/var/lib/gpu-unlock-sm1/original-boot`. `admin.py disable` removes next-boot unlocking and rebuilds initramfs without unloading the live GPU. `admin.py rollback` restores managed configuration. If Ubuntu cannot boot, use local recovery, mount root writable, remove `/etc/modprobe.d/gpu-unlock-sm1.conf` and `/etc/gpu-unlock-sm1/enabled`, then restore saved `initrd.img-7.0.0-38-generic` to `/boot/`. Physical recovery is required in that case; this is not guaranteed remote recovery.

## Cold hardware validation completed

Cold boot 9794ffdf-f339-4b0f-a793-f0bce16030c1 returned the exact reviewed c74f... image in both captures and inside the transaction. All structural guards passed, firmware/selector/FLR transaction succeeded, NVIDIA and CUDA remained functional. This validates the corrected early profile on both warm diagnostic and cold execution states. See benchmark-unlocked.md for measured improvements. Underlying post-driver tail mapping cause remains unproven; no guard was removed.
