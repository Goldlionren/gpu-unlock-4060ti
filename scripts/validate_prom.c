#include <stdio.h>
#include <stdlib.h>
#include "vbios_610.h"
int main(int argc,char **argv){
 if(argc!=2)return 2;
 FILE*f=fopen(argv[1],"rb");if(!f)return 2;
 unsigned char*r=malloc(1048576);if(!r)return 2;
 size_t n=fread(r,1,1048576,f);int extra=fgetc(f);fclose(f);
 struct gpu_unlock_fwsec fw={0};
 int rc=n==1048576&&extra==EOF?gpu_unlock_vbios_fwsec(r,n,&fw):-1;
 printf("{\"parse_result\":%d",rc);
#define FIELD(n) printf(",\"" #n "\":%u",fw.n)
 FIELD(image_off);FIELD(image_size);FIELD(imem_pa);FIELD(imem_size);FIELD(imem_va);
 FIELD(dmem_pa);FIELD(data_off);FIELD(dmem_size);FIELD(pkc_off);FIELD(interface_off);
 FIELD(ucode_id);FIELD(engine_mask);FIELD(sig_count);FIELD(sig_versions);FIELD(sig_off);FIELD(sig_bytes);
 puts("}");
 free(r);return rc||fw.engine_mask!=0x400;
}
