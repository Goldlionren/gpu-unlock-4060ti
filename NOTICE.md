# Attribution and modification notice

This project uses the Linux firmware transaction from **JustAResearcher/gpu-unlock-ada**, pinned to `d28c485418c3d9d034cd4bac19200bc33dd3453b`. The v1.1.1 reference tag `491925c1079435e260137b9f3526066e764de830` was audited separately; it is not the AD106-capable source used for this deployment. The local DKMS package retained version 1.1.1-sm1 during development; use source hashes, not that version string alone, to identify this frozen build.

Upstream-derived kernel files retain their SPDX notices and GPL-2.0-only licensing. The GPL version 2 text is provided in LICENSE and src/kernel/LICENSE. Original project-specific code in this publication is provided under GPL-2.0-only. NVIDIA firmware, VBIOS images and upstream build inputs are not redistributed; their own licenses continue to apply when obtained separately.

Modifications for Silver Moon 1 made on 2026-10-29:

- main.c: exact-board admission before upstream transaction, diagnostic snapshots, transaction result and handoff status.
- unlock_610.c: full board PROM verification before firmware use and transaction diagnostics.
- vbios_610.c, prep_610.c, layout_610.c and related local compatibility headers: inspect the frozen source and upstream comparison for diagnostic/kernel integration differences; they are not asserted to be unmodified upstream files.
- board_guard.h and diagnostic.h: local strict hardware/firmware validation and logging.
- Kernel Makefile/Kbuild/DKMS packaging and project scripts: local build, managed installation, synchronous NVIDIA loading, boot verification and measurements.

Other references: [NeoChen1024/gpu-unlock-ad103](https://github.com/NeoChen1024/gpu-unlock-ad103), [Goldlionren/gpu-unlock-4080s](https://github.com/Goldlionren/gpu-unlock-4080s), [ZeroHackz/gpu-unlock-windows](https://github.com/ZeroHackz/gpu-unlock-windows). Their audit revisions are listed in reports/source-lock.json. This project does not claim authorship of the upstream unlock mechanism.
