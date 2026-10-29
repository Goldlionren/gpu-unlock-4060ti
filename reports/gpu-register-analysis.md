# Register and firmware analysis

Historical research record; final hardware validation and owner-selected freeze are documented in [release acceptance](release-acceptance.md).

Sources are locally cloned and commit-pinned in `source-lock.json`: [primary Linux upstream](https://github.com/JustAResearcher/gpu-unlock-ada), [AD103 Linux reference](https://github.com/NeoChen1024/gpu-unlock-ad103), [Windows reference](https://github.com/ZeroHackz/gpu-unlock-windows), and [4080 SUPER reference](https://github.com/Goldlionren/gpu-unlock-4080s). Findings below are source observations or upstream evidence, not independent unlock verification on this host.

## Mechanism

`kernel/gpu_unlock/unlock_610.c` uses pinned NVIDIA 610.43.03 assets, parses board PROM/FWSEC, prepares DMA metadata, runs FWSEC and the Booter/V67 payload, verifies halted SEC2 and permission changes, restores the stock signature, writes feature selectors, and performs PCIe FLR with containment checks. This is a firmware-mediated permission change followed by selector writes, not a two-register userspace tweak.

SS0 is BAR0 offset 0x0082381c (eight 4-bit selectors), SS1 is 0x00823820 (effective low nibble). Upstream writes 0x88888888 and 0x8 and verifies readback plus effective speed fields. It does not derive a new per-board constant by copying a 4080 profile. AD106 takes the AD102-family path and four-PLM payload. Architectural family compatibility does not establish all boards/firmware/drivers as safe.

Entry requires ROM GFW completion, halted engine, accessible config/MMIO and WPR2 high value clear. Open PLM can produce EALREADY; that is not performance verification. Firmware result requires marker 0x67b00001, SEC2 halt and required WPR_CFG/WPR/FEAT permissions. FBPA mismatch is observational in this path. Before FLR, BME is cleared and DMA memory retained. After FLR: PCI identity/BAR restoration, GFW halt, SEC2 reset/release, no pending transactions, WPR2 disabled, selectors and effective readout verified. On uncertain DMA termination the module retains allocations and its reference until power off. This is containment, not guaranteed rollback to stock state.

The board PROM reader uses the BAR0 PROM window at 0x300000, up to 1 MiB, and parses firmware geometry. Upstream asset hashes protect supplied firmware; they do not replace a board-specific PROM hash. Main's admission uses vendor/device plus explicit BDF/experimental flag, without this project's required subsystem and exact firmware profile. Add those checks before executing firmware, under the same ownership protection as the transaction.

Windows/4080 implementations supply useful PROM/identity, exclusive ownership, selector readback and failure simulations. Their board-specific hashes, BAR layout, VRAM registers and boot-manager paths must not be imported. The 4080 repository records changing initial selectors and removal of a fixed initial-state allowlist after PROM checks; this project still requires locally understood initial states and must skip unknown states until reviewed.

## Evidence by precision

Main's `docs/ada-2803-report.md` reports one 16 GB 2803 card, 615.78.08 driver, matched stock/unlocked measurements: FP16/FP32 and BF16/FP32 instruction rates approximately doubled; separate seeded numerical checks passed. This is narrow upstream evidence with different driver/kernel/board context. The 2805 report explicitly lacks a same-card stock benchmark pair and GEMM numerical validation. Do not describe both reports as equally validated.

FP8 E4M3 has an explicit SM89 `mma.sync` path in upstream `mma_bench.cu`. That supplies an instruction-path test method; it does not prove a matched AD106 FP8 application improvement. E5M2 needs its own supported path and numerical tests. FP16 accumulation, strict scalar FP32, integer and FP32-accumulate tensor paths must remain separate. Local baseline E4M3 numeric errors and E5M2 dispatch limitations are recorded separately.

## Lifecycle assessment

| Event | Evidence / policy |
|---|---|
| FLR inside successful transaction | Selectors checked afterward in source and upstream AD106 logs; not tested here |
| Driver reload | No host validation; never unbind for this research phase |
| Later GPU reset | Retention unknown; mark status unknown and do not auto-retry |
| Suspend/resume | Unknown; revalidate after resume without resetting |
| Warm reboot | External enclosure may retain power/WPR2. Reject non-fresh WPR2; host reboot is not proof of cold GPU |
| Cold boot | Requires real enclosure power loss to establish fresh state; no test authorized/performed |
| Hotplug/reauthorization | BDF, topology and state may change; one-shot module does not rerun automatically; require new evidence |

The required execution window is after Linux PCI discovery and usable BAR assignment, while the GPU firmware state is fresh and before NVIDIA binds. Neither execution before bus enumeration nor EFI execution is intrinsically required by this Linux mechanism.
