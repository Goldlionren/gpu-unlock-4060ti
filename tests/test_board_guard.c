/* Execute the actual kernel guard with synthetic PCI/MMIO and SHA256. */
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <openssl/sha.h>
#define SILVER_MOON_HOST_TEST
#define __iomem
#define PCI_COMMAND 4
#define PCI_COMMAND_MEMORY 2
#define PCI_VENDOR_ID 0
#define PCI_DEVICE_ID 2
#define PCI_SUBSYSTEM_VENDOR_ID 44
#define PCI_SUBSYSTEM_ID 46
#define PCI_D0 0
#define PCI_UNKNOWN 5
#define PCI_PM_CTRL 4
#define PCI_PM_CTRL_STATE_MASK 3
#define GFP_KERNEL 0
#define SHA256_DIGEST_SIZE 32
typedef uint8_t u8;typedef uint16_t u16;typedef uint32_t u32;
struct pci_dev {u16 vendor,device,subsystem_vendor,subsystem_device;u8 revision;u32 class;void*driver;int current_state;int pm_cap;};
static unsigned char mmio[0x841000];static int config_fail, maps, copies, corrupt_repeat;
static u16 command=2;
static int pci_write_config_word(struct pci_dev*p,int off,u16 v){(void)p;assert(off==4);command=v;return 0;}
static size_t bar_length=sizeof(mmio);
static int pci_read_config_word(struct pci_dev*p,int off,u16*v){if(config_fail)return -1;switch(off){case 0:*v=p->vendor;break;case 2:*v=p->device;break;case 44:*v=p->subsystem_vendor;break;case 46:*v=p->subsystem_device;break;default:*v=command;}return 0;}
static size_t pci_resource_len(struct pci_dev*p,int n){(void)p;(void)n;return bar_length;}
static void*pci_iomap(struct pci_dev*p,int a,int b){(void)p;(void)a;(void)b;maps++;return mmio;}
static void pci_iounmap(struct pci_dev*p,void*b){(void)p;(void)b;}
static u32 readl(void*p){u32 x;memcpy(&x,p,4);return x;}
#define pci_info(...) ((void)0)
#define kvmalloc(n,f) malloc(n)
#define kvfree(p) free(p)
static void memcpy_fromio(void *dst,const void *src,size_t n){
 memcpy(dst,src,n);if(corrupt_repeat && ++copies==2)((u8*)dst)[0]^=1;
}
static int hex2bin(u8*out,const char*s,size_t n){for(size_t i=0;i<n;i++){unsigned a,b;char x=s[i*2],y=s[i*2+1];a=x>='0'&&x<='9'?x-'0':x>='a'&&x<='f'?x-'a'+10:99;b=y>='0'&&y<='9'?y-'0':y>='a'&&y<='f'?y-'a'+10:99;if(a>15||b>15)return -1;out[i]=(a<<4)|b;}return 0;}
static void sha256(const void*p,size_t n,u8*out){SHA256(p,n,out);}
char*board_prom_sha256;
#define pr_info(...) ((void)0)
void silver_moon_capture(const void *p,size_t n,unsigned sample){(void)p;assert(n==1048576);assert(sample<2);}
#include "board_guard.h"
static void reg(unsigned off,u32 v){memcpy(mmio+off,&v,4);}
int main(int argc,char **argv){
 struct pci_dev good={0x10de,0x2803,0x1462,0x5174,0xa1,0x030000,NULL,0,0},p;
 if(argc!=2){fprintf(stderr,"Usage: %s reviewed-1MiB-prom.bin\n",argv[0]);return 2;}
 FILE *f=fopen(argv[1],"rb");assert(f);
 assert(fread(mmio+0x300000,1,1048576,f)==1048576 && fgetc(f)==EOF);fclose(f);
 char hex[65];u8 hash[32];sha256(mmio+0x300000,1048576,hash);for(int i=0;i<32;i++)sprintf(hex+2*i,"%02x",hash[i]);board_prom_sha256=hex;
 reg(0,0x196000a1);assert(silver_moon_guard(&good)==0);
 command=0;assert(silver_moon_guard(&good)==0);assert(command==0);command=2;
 p=good;p.subsystem_device++;maps=0;assert(silver_moon_guard(&p)<0&&maps==0);
 p=good;p.driver=&p;assert(silver_moon_guard(&p)<0);
 p=good;p.current_state=3;assert(silver_moon_guard(&p)<0);
 config_fail=1;assert(silver_moon_guard(&good)<0);config_fail=0;
 bar_length=100;assert(silver_moon_guard(&good)<0);bar_length=sizeof(mmio);
 reg(0x1fa828,16);assert(silver_moon_guard(&good)<0);reg(0x1fa828,0);
 reg(0x82381c,0xffffffff);assert(silver_moon_guard(&good)<0);reg(0x82381c,0);
 reg(0x823820,9);assert(silver_moon_guard(&good)<0);reg(0x823820,0);
 mmio[0x300000]^=1;assert(silver_moon_guard(&good)==-EBADMSG);mmio[0x300000]^=1;
 /* No tail is ignored. Firmware, signature and final byte mutations fail. */
 unsigned offsets[]={0x45848,0x45b48,0x9a200,0xd6c00,0xfffff};
 for(unsigned i=0;i<sizeof(offsets)/sizeof(*offsets);i++){
  mmio[0x300000+offsets[i]]^=1;assert(silver_moon_guard(&good)==-EBADMSG);mmio[0x300000+offsets[i]]^=1;
 }
 corrupt_repeat=1;copies=0;assert(silver_moon_guard(&good)==-EBADMSG);corrupt_repeat=0;
 /* Even a matching digest cannot authorize malformed/other FWSEC geometry. */
 char valid_hash[65];memcpy(valid_hash,hex,65);
 unsigned bad[]={0,0x4581c,0x4581c+36,0x4581c+16};
 for(unsigned i=0;i<sizeof(bad)/sizeof(*bad);i++){
  mmio[0x300000+bad[i]]^=1;sha256(mmio+0x300000,1048576,hash);
  for(int j=0;j<32;j++)sprintf(hex+2*j,"%02x",hash[j]);
  assert(silver_moon_guard(&good)<0);mmio[0x300000+bad[i]]^=1;
 }
 memcpy(hex,valid_hash,65);
 board_prom_sha256=NULL;assert(silver_moon_guard(&good)<0);
 board_prom_sha256="not-a-hash";assert(silver_moon_guard(&good)<0);
 board_prom_sha256=hex;assert(silver_moon_guard(&good)==0);
 puts("actual board guard: identity, decode restoration, full-image SHA, repeat-read and FWSEC structure cases passed; mock PCI/MMIO only");return 0;
}
