#define _FILE_OFFSET_BITS 64
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <unistd.h>
/* Read-only, hard-selected resource supplied by validated capture_board.py. */
int main(int argc,char**argv){
 if(argc!=3)return 2;
 int fd=open(argv[1],O_RDONLY|O_CLOEXEC);if(fd<0){perror("open");return 2;}
 const volatile uint32_t*p=mmap(NULL,0x400000,PROT_READ,MAP_SHARED,fd,0);
 if(p==MAP_FAILED){perror("mmap");return 2;}
 if(p[0]!=0x196000a1){fprintf(stderr,"wrong chip\n");return 2;}
 uint32_t*b=malloc(1048576);if(!b)return 2;
 for(unsigned i=0;i<1048576/4;i++)b[i]=p[0x300000/4+i];
 FILE*f=fopen(argv[2],"wb");if(!f)return 2;
 int ok=fwrite(b,1,1048576,f)==1048576;fclose(f);munmap((void*)p,0x400000);close(fd);free(b);return !ok;
}
