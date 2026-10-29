#!/usr/bin/env python3
"""Offline byte-level comparison. Never opens sysfs or GPU devices."""
import argparse,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
def describe(p):
 data=pathlib.Path(p).read_bytes()
 parsed=subprocess.run([str(ROOT/'build/validate_prom'),str(p)],capture_output=True,text=True)
 spans=[]
 for val in (0,255):
  start=None
  for i,b in enumerate(data+b'\x7f'):
   if b==val and start is None:start=i
   elif b!=val and start is not None:
    if i-start>=256:spans.append({'offset':start,'length':i-start,'byte':val})
    start=None
 return data,{'path':str(p),'length':len(data),'sha256':hashlib.sha256(data).hexdigest(),'zero_bytes':data.count(0),'ff_bytes':data.count(255),'constant_spans':spans,'fwsec_validation_exit':parsed.returncode,'fwsec_validation_output':parsed.stdout,'prefix64':data[:64].hex()}
def compare(a,b):
 offsets=[i for i,(x,y) in enumerate(zip(a,b)) if x!=y]
 first=offsets[0] if offsets else min(len(a),len(b)) if len(a)!=len(b) else None
 blocks=sorted(set(i//4096*4096 for i in offsets))
 return {'same':a==b,'first_difference':first,'different_bytes_in_shared_length':len(offsets),'length_difference':len(b)-len(a),'different_4k_blocks':blocks,'context':None if first is None else {'start':max(0,first-16),'expected':a[max(0,first-16):first+32].hex(),'observed':b[max(0,first-16):first+32].hex()}}
def main():
 p=argparse.ArgumentParser();p.add_argument('expected');p.add_argument('observed');p.add_argument('--repeat');p.add_argument('--output',default='logs/prom-comparison.json');args=p.parse_args()
 a,aa=describe(args.expected);b,bb=describe(args.observed);r={'expected':aa,'observed':bb,'comparison':compare(a,b)}
 if args.repeat:
  c,cc=describe(args.repeat);r['repeat']=cc;r['stability']=compare(b,c)
 pathlib.Path(args.output).write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
if __name__=='__main__':main()
