/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef SILVER_MOON_BOARD_GUARD_H
#define SILVER_MOON_BOARD_GUARD_H
#ifndef SILVER_MOON_HOST_TEST
#include <crypto/sha2.h>
#include <linux/io.h>
#include <linux/pci.h>
#include <linux/slab.h>
#include <linux/string.h>
#include <linux/hex.h>
#endif
#include "vbios_610.h"
extern char *board_prom_sha256;
extern void silver_moon_capture(const void *rom, size_t size, unsigned int sample);
/* Called with pci_dev_lock held, BEFORE upstream changes config or DMA. */
static int silver_moon_prom(const void *rom, size_t size)
{
 u8 expected[SHA256_DIGEST_SIZE], actual[SHA256_DIGEST_SIZE];
 struct gpu_unlock_fwsec fw;
 int ret;
 if (!board_prom_sha256 || strlen(board_prom_sha256) != 64 ||
     hex2bin(expected, board_prom_sha256, sizeof(expected)) || size != 1024*1024)
  return -EINVAL;
 sha256(rom, size, actual);
 pr_info("silver_moon PROM sha256=%*phN expected=%s bytes=%zu\n",32,actual,board_prom_sha256,size);
 if (memcmp(expected, actual, sizeof(actual))) return -EBADMSG;
 /* Validate the firmware structure BEFORE upstream changes hardware state.
  * These are offsets from this board's independently compared ROM chain. */
 ret = gpu_unlock_vbios_fwsec(rom, size, &fw);
 if (ret) return ret;
 if (fw.image_off != 0x45b48 || fw.image_size != 0x10500 ||
     fw.imem_pa != 0 || fw.imem_va != 0 || fw.imem_size != 0xf700 ||
     fw.dmem_pa != 0 || fw.data_off != 0xf700 || fw.dmem_size != 0xd80 ||
     fw.pkc_off != 0xb24 || fw.interface_off != 0x1c ||
     fw.ucode_id != 9 || fw.engine_mask != 0x400 ||
     fw.sig_count != 2 || fw.sig_versions != 3 ||
     fw.sig_off != 0x45848 || fw.sig_bytes != 768) return -EINVAL;
 return 0;
}
static inline int silver_moon_guard(struct pci_dev *p)
{
 void __iomem *bar; void *rom; int ret; u16 cmd, live, pmcsr, vendor, device, sv, sd; bool decode_changed=false;
 u32 chip, ss0, ss1, wpr; unsigned int i;
 if (p->vendor != 0x10de || p->device != 0x2803 ||
     p->subsystem_vendor != 0x1462 || p->subsystem_device != 0x5174 ||
     p->revision != 0xa1 || p->class != 0x030000 || p->driver)
  return -ENODEV;
 if (!board_prom_sha256 || strlen(board_prom_sha256) != 64) return -EINVAL;
 if (pci_read_config_word(p, PCI_VENDOR_ID, &vendor) || vendor != 0x10de ||
     pci_read_config_word(p, PCI_DEVICE_ID, &device) || device != 0x2803 ||
     pci_read_config_word(p, PCI_SUBSYSTEM_VENDOR_ID, &sv) || sv != 0x1462 ||
     pci_read_config_word(p, PCI_SUBSYSTEM_ID, &sd) || sd != 0x5174 ||
     pci_read_config_word(p, PCI_COMMAND, &cmd) || cmd == 0xffff || pci_resource_len(p,0) < 0x841000)
  return -ENODEV;
 if (p->current_state != PCI_D0 &&
     (p->current_state != PCI_UNKNOWN || !p->pm_cap ||
      pci_read_config_word(p, p->pm_cap+PCI_PM_CTRL, &pmcsr) ||
      (pmcsr & PCI_PM_CTRL_STATE_MASK) != PCI_D0)) return -EBUSY;
 /* Linux hotplug may assign BARs with MEMORY decode still off. Only
  * toggle that PCI configuration bit; never start an engine or enable BME. */
 if (!(cmd & PCI_COMMAND_MEMORY)) {
  decode_changed=true;
  ret=-EIO;
  if (pci_write_config_word(p,PCI_COMMAND,cmd|PCI_COMMAND_MEMORY) ||
      pci_read_config_word(p,PCI_COMMAND,&live) || live!=(cmd|PCI_COMMAND_MEMORY)) goto restore;
 }
 bar = pci_iomap(p, 0, 0); if (!bar) {ret=-ENOMEM;goto restore;}
 chip = readl(bar); ss0 = readl(bar+0x82381c); ss1 = readl(bar+0x823820);
 wpr = readl(bar+0x1fa828);
 pci_info(p,"silver_moon preflight chip=%08x ss0=%08x ss1=%08x wpr2=%08x\n",chip,ss0,ss1,wpr);
 ret = -EBUSY;
 if (chip != 0x196000a1 || wpr != 0 || ss1 > 8) goto out;
 /* Reject invalid selector encodings; do not import another board's state. */
 for (i=0;i<8;i++) if (((ss0>>(i*4))&15)>8) goto out;
 rom = kvmalloc(1024*1024, GFP_KERNEL); if (!rom) {ret=-ENOMEM;goto out;}
 memcpy_fromio(rom, bar+0x300000, 1024*1024);
 silver_moon_capture(rom,1024*1024,0);
 ret=silver_moon_prom(rom,1024*1024);
 memcpy_fromio(rom,bar+0x300000,1024*1024);
 silver_moon_capture(rom,1024*1024,1);
 if (silver_moon_prom(rom,1024*1024) && !ret) ret=-EBADMSG;
 kvfree(rom);
 if (!ret) pci_info(p,"silver_moon board and PROM verified before writes\n");
out:
 pci_iounmap(p,bar);
restore:
 if (decode_changed && (pci_write_config_word(p,PCI_COMMAND,cmd) ||
     pci_read_config_word(p,PCI_COMMAND,&live) || live!=cmd)) return -EUCLEAN;
 return ret;
}
#endif
