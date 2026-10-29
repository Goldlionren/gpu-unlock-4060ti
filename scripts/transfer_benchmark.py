#!/usr/bin/env python3
import json,time,pathlib,torch
rows=[]
for size in [16,64,256]:
 h=torch.empty(size*1024*1024,dtype=torch.uint8,pin_memory=True);h.fill_(1);d=torch.empty_like(h,device='cuda')
 for direction in ['H2D','D2H']:
  times=[]
  for i in range(6):
   torch.cuda.synchronize();t=time.perf_counter()
   if direction=='H2D':d.copy_(h,non_blocking=True)
   else:h.copy_(d,non_blocking=True)
   torch.cuda.synchronize()
   if i:times.append(time.perf_counter()-t)
  rows.append({'MiB':size,'direction':direction,'seconds':times,'median_GB_s':size*1024*1024/sorted(times)[2]/1e9})
pathlib.Path('logs/transfers.json').write_text(json.dumps(rows,indent=2))
