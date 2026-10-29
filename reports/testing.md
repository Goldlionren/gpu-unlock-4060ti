# Validation record

Historical research record; final hardware validation and owner-selected freeze are documented in [release acceptance](release-acceptance.md).

All compilation and simulations ran in the workspace. No resulting module was loaded.

| Check | Result |
|---|---|
| Main d28c485 kernel module against 7.0.0-38 headers | Built; BTF skipped because vmlinux unavailable |
| Tag v1.1.1 491925c kernel module | Built; same BTF limitation |
| Main initial suite without assets | 30 tests, 9 skips; not sufficient for transaction validation |
| Pinned firmware input download | Both SHA-256 checks passed; sources/package cached locally |
| Firmware generation | Completed, output pins verified by upstream generators |
| Main test-full with assets | 33 tests, 3 optional decoder skips; AD102 and GA102 full mocked transactions pass |
| v1.1.1 | Has no test-full target; make test with explicit asset and NVIDIA source paths used instead; 22 tests, 3 optional decoder skips; pass |
| Local board admission/failure model | 8 tests pass, including actual incomplete profile rejection |
| CUDA numerical binary | Built with nvcc 13.0 for sm_89; six FP16/BF16 seeded cases pass |
| GPU smoke | Passed after benchmarks; SSH service/socket active |

Three optional private firmware-decoder tests require PyCryptodome and were not run. These skips do not include main's full mocked hardware transactions. Successful simulations do not verify this board, Thunderbolt FLR containment, boot ordering or real DMA shutdown.

The first benchmark attempt stopped on unsupported E5M2 with ValueError. The harness was corrected to record unsupported dispatch and continue; the complete rerun is in benchmark.json. E4M3's numerical threshold failures are retained. The v1.1.1 test-full invocation failed because the target does not exist; its separate make test run is the applicable result. Raw failed attempts are retained, not represented as successful checks.

Inspect `logs/module-build-*.log`, `logs/upstream-main-full-tests.log`, `logs/upstream-v1.1.1-with-assets-tests.log`, `logs/local-tests.log`, `logs/numerical-stock.txt`, `logs/verification.txt`, and `logs/benchmark.json`. Source commits are pinned in source-lock.json. Local raw evidence is excluded from publication.
