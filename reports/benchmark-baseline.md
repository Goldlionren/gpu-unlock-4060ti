# Preliminary stock benchmark — 2026-10-29

No unlock was applied. Same physical MSI AD106; NVIDIA 580.178.04, PyTorch 2.13.0+cu130, CUDA 13.0. Inputs seeded 20261029. Raw measurements, source hash, precision flags and telemetry are in `logs/benchmark.json`. Existing Python GPU clients remained active: this is a preliminary baseline, not a controlled publication comparison.

CUDA events time device-resident GEMM only: three warmups, seven timed calls, median throughput = 2N³ / elapsed time. No H2D/D2H is included in GEMM time. TF32 and FP16/BF16 reduced precision reduction are disabled; FP8 fast accumulation is disabled. This does not by itself establish the actual cuBLAS kernel/instruction dispatch. Kernel profiling is still required for attribution. Power/temperature/SM and memory clocks are sampled around runs, not continuously integrated energy measurements.

| N | Mode | Median TFLOP/s | Relative L2 error | Numerical result |
|---|---|---:|---:|---|
| 2048 | fp32 | 11.65 | 3.12e-07 | pass |
| 2048 | fp16 | 41.22 | 0.000207 | pass |
| 2048 | bf16 | 41.22 | 0.00164 | pass |
| 2048 | fp8_e4m3 | 76.96 | 0.000103 | threshold failure |
| 2048 | fp8_e5m2 | 0.00 | nan | unsupported: E5M2 × E5M2 |
| 4096 | fp32 | 12.49 | 1.15e-06 | pass |
| 4096 | fp16 | 41.85 | 0.000208 | pass |
| 4096 | bf16 | 44.38 | 0.00166 | pass |
| 4096 | fp8_e4m3 | 88.30 | 0.000103 | threshold failure |
| 4096 | fp8_e5m2 | 0.00 | nan | unsupported: E5M2 × E5M2 |
| 8192 | fp32 | 11.67 | 1.62e-06 | pass |
| 8192 | fp16 | 44.99 | 0.000208 | pass |
| 8192 | bf16 | 44.95 | 0.00166 | pass |
| 8192 | fp8_e4m3 | 87.73 | 0.000103 | threshold failure |
| 8192 | fp8_e5m2 | 0.00 | nan | unsupported: E5M2 × E5M2 |

The reference uses FP64 accumulation of already quantized operands for 32 evenly spaced complete rows. Errors measure arithmetic on representable inputs, not quantization versus original full-precision inputs. Whole-output finiteness is checked; this is not exhaustive numerical certification. Initial relative-L2 limits are 1e-5 for FP32/FP8-output-FP32 and 0.005 for FP16/BF16 outputs. FP8 E4M3 is approximately 1e-4 and fails that initial criterion even in stock state. Do not loosen the threshold merely to obtain a pass; investigate kernel accumulation/subnormal behavior and compare against independent instruction tests. E5M2 × E5M2 raises an explicit unsupported-operation error in this stack. No fallback to lower precision is made.

The separately compiled upstream `validate_gemm.cu` checks all elements of three seeded shapes (256×256×256, 64×96×128, 127×65×95) in FP16 and BF16 with FP32 accumulation against CPU references. All six checks pass, zero failures and max_abs=0 for these dyadic fixtures (`logs/numerical-stock.txt`). This stronger accumulation test complements the PyTorch output-dtype checks.

The public NVIDIA RM getter worked on driver 580: FMLA32, IMLA2 and IMLA4 report 1 (half); the other six fields report 0 (full). This confirms the stock rate profile at observation time, not a performance conclusion. No BAR mapping is used by this getter.

Pinned-memory transfer tests (`logs/transfers.json`) use 16/64/256 MiB buffers, one warmup and five host-wall measurements with explicit GPU synchronization. Transfers remain separate from compute and include host API/synchronization overhead.

No after-unlock run exists. Before any claim: repeat under an agreed idle workload window with unchanged driver/PyTorch/binaries, input seed, precision settings, GPU identity, power cap and clock policy; record time-series telemetry, identify actual dispatched kernels, alternate matched runs, inspect Xid/GSP errors, and repeat numerical checks. Do not infer application FP8 gains from FP16/BF16 or rate-register changes.
