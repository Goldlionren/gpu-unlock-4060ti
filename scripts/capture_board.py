#!/usr/bin/env python3
"""Privileged READ-ONLY BAR0 snapshot. No config writes, resets or unbinding."""
import hashlib,json,mmap,os,pathlib,struct,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
expected={'vendor':'0x10de','device':'0x2803','subsystem_vendor':'0x1462','subsystem_device':'0x5174','revision':'0xa1'}
found=[p for p in pathlib.Path('/sys/bus/pci/devices').glob('*') if all((p/k).read_text().strip()==v for k,v in expected.items())]
if len(found)!=1:raise SystemExit('Expected exactly one exact MSI board')
p=found[0]
if (p/'power/runtime_status').read_text().strip()!='active':raise SystemExit('GPU is not active; no power transition attempted')
fd=os.open(p/'resource0',os.O_RDONLY|os.O_CLOEXEC)
try:
 with mmap.mmap(fd,0x841000,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ) as bar:
  regs={k:struct.unpack_from('<I',bar,v)[0] for k,v in {'chip':0,'ss0':0x82381c,'ss1':0x823820,'wpr2_hi':0x1fa828,'gfw_cpuctl':0x110100}.items()}
  if regs['chip']!=0x196000a1:raise SystemExit('Unexpected chip; stop')
  rom=bytes(bar[0x300000:0x400000]);again=bytes(bar[0x300000:0x400000])
  if rom!=again or rom[:2]!=b'\x55\xaa':raise SystemExit('PROM unstable or invalid signature')
finally:os.close(fd)
out=ROOT/'logs/board-capture';out.mkdir(exist_ok=True)
(out/'prom.bin').write_bytes(rom)
result={'timestamp':time.time(),'bdf':p.name,'identity':expected,'registers':regs,'prom_sha256':hashlib.sha256(rom).hexdigest(),'prom_size':len(rom),'driver':(p/'driver').resolve().name if (p/'driver').exists() else None,'writes':0,'cold_state_verified':False}
(out/'capture.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
