# Frozen release acceptance — 2026-10-29

The owner explicitly ended further hardware testing after a successful cold boot and one successful warm reboot, and requested publication to Goldlionren/gpu-unlock-4060ti. The deployed unlock remains enabled. Publication does not change any boot artifact or runtime hardware state.

| Criterion | Evidence/status |
|---|---|
| Actual MSI AD106 unlock | Verified: board/PROM/firmware guards, payload completion, selectors and FLR |
| Standard NVIDIA and CUDA | Verified after both successful boots |
| FP16/BF16 performance | Verified matched real GEMM gains; 8192 approximately 1.65–1.71× stock |
| Numerical correctness | Tested FP16/BF16 cases passed; measured statistics unchanged from stock |
| FP8 | E4M3 GEMM gains observed with unchanged pre-existing error; E5M2×E5M2 unsupported in tested API |
| Automatic boot integration | Verified cold boot and one subsequent warm reboot with independent boot service |
| Preflight failure fallback | Verified earlier SHA rejection retained normal Ubuntu/NVIDIA operation |
| Remote administration | Local SSH service/socket and network healthy; no independent external SSH client test recorded |
| Disable/rollback | Scripts and isolated-filesystem restoration tested; live disable/restore deliberately not tested |
| Recovery | Original kernel/initramfs/config backups retained; physical access available during testing; emergency recovery not exercised |
| Second warm reboot | Not performed by owner decision |
| Future kernels, suspend, hotplug | Not hardware-qualified; late hotplug after NVIDIA registration left stock |

This is an owner-accepted, exact-machine frozen deployment. It is not a claim that all initially proposed validation cycles were completed, or that any software fallback guarantees recovery from a pre-network kernel hang.

The kernel source and integration files are unchanged from the successful boots. Frozen hashes are in release-manifest.json. Files under reports/evidence contain selected numerical results; private captures/raw logs remain on the workstation.
