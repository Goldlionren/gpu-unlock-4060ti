# RTX 4060 Ti Linux automatic Tensor Core unlock

Frozen on **2026-10-29** for **Silver Moon 1**, an MSI RTX 4060 Ti 16 GB (AD106) connected to Ubuntu through Thunderbolt. A cold boot and one subsequent warm reboot automatically completed the guarded firmware transaction, FLR and stock NVIDIA driver handoff. No manual unlock command was needed after either boot.

This is the exact-machine implementation and validation record, not a general RTX 4060 Ti installer. It preserves the upstream transaction from [JustAResearcher/gpu-unlock-ada](https://github.com/JustAResearcher/gpu-unlock-ada/tree/d28c485418c3d9d034cd4bac19200bc33dd3453b) and adds local board/PROM guards, driver-load coordination, managed deployment and boot verification. See [NOTICE](NOTICE.md) for attribution.

## Verified results

Same GPU, NVIDIA 580.178.04, PyTorch 2.13.0+cu130, CUDA 13.0, benchmark source/seed/precision settings and 165 W limit. Device-resident 8192 × 8192 GEMM; GPU compute timing excludes Thunderbolt transfers:

| Mode | Stock | Cold boot unlocked | Warm reboot unlocked |
|---|---:|---:|---:|
| FP32 | 11.67 | 11.81 | 11.82 TFLOP/s |
| FP16 | 44.99 | 74.29 | 76.75 TFLOP/s |
| BF16 | 44.95 | 76.84 | 77.01 TFLOP/s |
| FP8 E4M3 | 87.25 | 137.41 | 147.49 TFLOP/s |
| INT8 control | 171.39 | 164.11 | 172.46 TOP/s |

All measured numerical error statistics matched stock. Six independent FP16/BF16 CUDA validation cases passed with zero mismatches. FP8 E4M3 retains the same approximately 1e-4 relative error seen before unlocking: the original 1e-5 criterion still fails and was not relaxed. Twelve targeted FP8 experiments matched stock statistics exactly. E5M2 × E5M2 is unsupported by the tested PyTorch operation.

Clocks were not locked; power/temperature and background-workload limitations are documented. These are GEMM measurements, not synthetic Tensor Issue claims. See [full results](reports/benchmark-unlocked.md), [numerical analysis](reports/fp8-investigation.md) and [sanitized evidence](reports/evidence/README.md).

## Frozen scope

- GPU identity: `10de:2803`, subsystem `1462:5174`, revision a1; VBIOS `95.06.34.00.F3`.
- Ubuntu 24.04.4 LTS, kernel `7.0.0-38-generic`, Secure Boot **disabled**.
- Exact known Thunderbolt enclosure, existing authorization and IOMMU protection retained. BDF discovered dynamically.
- DKMS module and initramfs integration installed; synchronous `modprobe nvidia` wrapper runs before NVIDIA registers/binds.
- Exact 1 MiB pre-driver PROM SHA-256 and FWSEC structure required. No VBIOS flashing, EFI changes or replacement of NVIDIA binaries.
- One attempt per boot/device admission; ordinary preflight rejection continues to stock. An unsafe post-transaction handoff withholds the GPU driver rather than repeatedly resetting it.
- Independent systemd verification saves per-boot JSON, smoke tests and successful-transaction benchmarks without relying on this development session.

The owner chose to freeze after the successful cold boot and first warm reboot. A second warm cycle and live disable/restore cycles were **not performed**. Disable/rollback were tested in an isolated filesystem only. New kernels, suspend/resume and hotplug are not qualified. Late hotplug after NVIDIA registration remains stock. No guarantee of remote recovery from a kernel hang is made. [Release acceptance](reports/release-acceptance.md) records these limits.

## Commands on the deployed workstation

```sh
gpu-unlock status
gpu-unlock verify
gpu-unlock benchmark
gpu-unlock logs
sudo gpu-unlock enable
sudo gpu-unlock disable
sudo gpu-unlock rollback
```

Status reports observed module result, NVIDIA state and available rate information; a loaded module alone is not proof of success. Enable/disable/rollback affect subsequent boots and do not unload or reset the live GPU. The configuration remains enabled on the validated workstation.

## Source and offline checks

```sh
python3 -m unittest discover -s tests -v
make -C src/kernel KDIR=/lib/modules/$(uname -r)/build
cc -O2 -Wall -Wextra -Isrc/kernel scripts/validate_prom.c src/kernel/vbios_610.c -o build/validate_prom
```

Create `build/` first for the C command. Tests requiring private board evidence skip when those files are absent. The actual C guard harness accepts a reviewed 1 MiB capture; the capture is deliberately not distributed:

```sh
cc -O2 -Wall -Wextra -Isrc/kernel tests/test_board_guard.c src/kernel/vbios_610.c -lcrypto -o build/test_board_guard
build/test_board_guard /path/to/reviewed-prom.bin
```

Upstream firmware preparation is reproducible from its pinned source, but binaries and board PROM dumps are not included:

```sh
git clone https://github.com/JustAResearcher/gpu-unlock-ada references/gpu-unlock-ada
git -C references/gpu-unlock-ada checkout d28c485418c3d9d034cd4bac19200bc33dd3453b
python3 references/gpu-unlock-ada/firmware/fetch_artifacts.py build/cache/inputs
make -C references/gpu-unlock-ada firmware CACHE="$PWD/build/cache"
```

The deployment scripts intentionally retain the tested workstation paths, account, enclosure UUID and network preflight destination. A public clone is **not sufficient to reinstall**: the installer requires the private original and repeated pre-driver capture files referenced in `src/pre-driver-prom.json`, generated firmware assets and the existing CUDA Python environment. Missing evidence fails closed. Do not substitute another board's capture, relax the profile or run upstream `make install` to bypass this process.

On the original workstation only, the reviewed maintenance procedure is `sudo python3 scripts/admin.py install` followed by `sudo python3 scripts/admin.py enable`. Existing backups and managed-file drift checks must remain intact. See [recovery](reports/security-and-recovery.md) and [PROM mismatch diagnosis](reports/prom-mismatch-investigation.md).

`src/policy.py` and `src/board-profile.json` are the initial CPU-only policy model, not the deployed hardware backend. The deployed guard is `src/kernel/board_guard.h`; the reviewed capture profile is `src/pre-driver-prom.json`.

## Publication contents

Source, attribution, test code, hashes and selected numerical evidence are included. Firmware payloads, PROM images, compiled modules, raw host logs, credentials and development-session notes are excluded. No boot configuration was changed to prepare this publication. Earlier research reports are dated historical records; the release acceptance document defines the final verified scope.
