# Verified cold-boot unlock and matched GEMM results

Test date: 2026-10-29. Boot ID: `9794ffdf-f339-4b0f-a793-f0bce16030c1`. User confirmed cold boot after host shutdown and enclosure power cycle.

The exact MSI AD106 completed the validated transaction before NVIDIA loaded: three full PROM checks passed, FWSEC returned scratch=0, payload marker and permissions passed, selectors changed from SS0=40671143/SS1=3 to 88888888/8, FLR returned 0, post-FLR GFW and selector checks passed. NVIDIA 580.178.04 then loaded; CUDA and SSH are functional. Thunderbolt enclosure UUID matched the existing authorization policy. BDF remained 0000:05:00.0.

## Matched performance

Same GPU/UUID, driver, CUDA 13.0, PyTorch 2.13.0+cu130, benchmark source SHA, seed, precision controls and 165 W limit. Device-resident GEMM uses CUDA event timing; host/device transfers are excluded. These are real GEMM results, not synthetic Tensor Issue figures. Rates are TFLOP/s except INT8 TOP/s.

| N | Mode | Stock | Unlocked | Ratio | Stock ms | Unlocked ms |
|---:|---|---:|---:|---:|---:|---:|
| 2048 | fp32 | 11.65 | 11.72 | 1.006× | 1.475 | 1.465 |
| 2048 | fp16 | 41.12 | 72.32 | 1.759× | 0.418 | 0.238 |
| 2048 | bf16 | 41.22 | 73.91 | 1.793× | 0.417 | 0.232 |
| 2048 | fp8_e4m3 | 76.96 | 112.60 | 1.463× | 0.223 | 0.153 |
| 2048 | int8 | 133.15 | 118.15 | 0.887× | 0.129 | 0.145 |
| 4096 | fp32 | 12.89 | 12.20 | 0.946× | 10.663 | 11.268 |
| 4096 | fp16 | 43.46 | 73.87 | 1.700× | 3.162 | 1.861 |
| 4096 | bf16 | 44.19 | 75.02 | 1.698× | 3.110 | 1.832 |
| 4096 | fp8_e4m3 | 87.90 | 121.46 | 1.382× | 1.564 | 1.132 |
| 4096 | int8 | 157.35 | 154.45 | 0.982× | 0.873 | 0.890 |
| 8192 | fp32 | 11.67 | 11.81 | 1.012× | 94.200 | 93.066 |
| 8192 | fp16 | 44.99 | 74.29 | 1.651× | 24.439 | 14.800 |
| 8192 | bf16 | 44.95 | 76.84 | 1.710× | 24.461 | 14.308 |
| 8192 | fp8_e4m3 | 87.25 | 137.41 | 1.575× | 12.602 | 8.002 |
| 8192 | int8 | 171.39 | 164.11 | 0.958× | 6.415 | 6.700 |

A second run after boot reproduced the gains: 8192 FP16 74.04 TFLOP/s, BF16 76.64, FP8 E4M3 136.14. FP32 stayed near its baseline; INT8 did not improve. These runs validate a substantial gain, not an exact doubling.

## Numerical and operating limits

All measured FP32/FP16/BF16/INT8 max-error, RMSE and relative-L2 statistics match the stock run. FP16/BF16 pass existing tolerances. Independent CUDA FP16/FP32 and BF16/FP32 accumulation checks across three shapes pass all six cases with zero mismatches/max_abs=0. This covers exercised workloads, not every possible input.

FP8 E4M3 relative L2 remains about 1.03e-4 in both states; the original 1e-5 criterion fails in both and has not been relaxed. Twelve targeted cases (quantized references, CPU/GPU FP64 cross-check, scaling, dyadic inputs, subnormal exclusion, fast accumulation and split-K) reproduce exactly the stock statistics. No unlock-attributable numerical degradation was observed. Evidence supports accumulation/rounding as the pre-existing error source, without proving an internal mantissa width. E5M2×E5M2 remains unsupported by the installed PyTorch operation.

Clocks and power were not locked or modified. Point telemetry at 8192 FP16/BF16 was 2640/2640 MHz stock versus 2370/2295 MHz unlocked; power 158.59/145.44 W versus 160.01/152.91 W, temperature 67/66 C versus 59/60 C. Memory clock was 8751 MHz. Lower sampled unlocked SM clocks and the 165 W cap plausibly constrain scaling; point samples are not continuous in-kernel measurements and do not prove a causal power limit. Short GEMMs, dispatch overhead and memory movement also prevent equating doubled instruction capacity with doubled GEMM. Background ComfyUI allocation remained present. No claim of perfectly isolated or fixed-clock performance.

No matching NVRM Xid, GPU-fallen-off-bus, AER error, kernel Oops or BUG entry was found after tests. No live reset or driver reload was performed by the agent.

## Boot acceptance

- Verified: actual board transaction, FLR, preserved selectors, stock NVIDIA handoff, CUDA, measured FP16/BF16 improvements, FP8 characterization, automatic cold-boot loading and independent on-boot verification, local SSH service/socket health.
- Verified failure case: earlier PROM rejection continued to stock NVIDIA without firmware execution or repeated reset.
- Offline only: managed installation/disable/rollback restoration tests; emergency initramfs recovery is documented and backups preserved.
- Pending: two successful warm reboot tests after unlocking, actual disable-to-stock boot and re-enable boot, external SSH client reconnection, broader suspend/hotplug and kernel-upgrade qualification.

At the time of these measurements the original full acceptance matrix was not complete. The owner subsequently chose to freeze the verified configuration; see release-acceptance.md. Late hotplug after NVIDIA registration is deliberately left stock; no live reapplication is attempted.

## Evidence

Raw boot files: `logs/boots/9794ffdf-f339-4b0f-a793-f0bce16030c1`. Comparisons: `logs/cold1-comparison.json`, `logs/cold1-repeat-comparison.json`, `logs/cold1-fp8-comparison.json`. Stock data and original capture remain unmodified.

## Successful warm reboot #1

Boot `181b38f5-beff-4182-8bb7-2352a97833c5` completed the automatic transaction again with the enclosure left powered. Entry WPR2=0, SS0=60671143, SS1=3; selectors and post-FLR checks succeeded. Both PROM snapshots exactly match the cold boot. Independent verification service exited successfully; SSH service/socket and NVIDIA/CUDA work.

8192 GEMM: FP16 76.745 TFLOP/s (1.706× stock), BF16 77.009 (1.713×), FP8 E4M3 147.492 (1.691×). FP32 and INT8 are within about 1.3% of stock on this run, consistent with unchanged control paths and ordinary run variation. Every measured numerical statistic matches stock. E4M3's original strict criterion remains failed and E5M2×E5M2 unsupported. Metadata checks pass. Evidence: `logs/warm-success1-comparison.json` and the boot directory's `acceptance.json`/`kernel.txt`.

One successful warm reboot is now verified; the second and actual disable/restore boot tests remain pending.

## Owner-selected freeze

Further hardware cycles were waived on 2026-10-29. The second warm reboot and live disable/restore remain unverified, not outstanding requests to the owner. The successful cold/warm configuration is retained unchanged.
