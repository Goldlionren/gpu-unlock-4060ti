#!/usr/bin/env python3
import argparse,json,pathlib,torch
parser=argparse.ArgumentParser()
parser.add_argument('--output',default='logs/fp8-investigation.json')
args=parser.parse_args()
out=[];torch.manual_seed(20261029);torch.backends.cuda.matmul.allow_tf32=False
for n in [256,2048]:
 for distribution in ['gaussian','dyadic','no_subnormals']:
  x=torch.randn(n,n,device='cuda')*.125;y=torch.randn(n,n,device='cuda')*.125
  if distribution=='dyadic':x=torch.randint(-4,5,(n,n),device='cuda').float()/8;y=torch.randint(-4,5,(n,n),device='cuda').float()/8
  if distribution=='no_subnormals':x=x.sign()*x.abs().clamp_min(1/64);y=y.sign()*y.abs().clamp_min(1/64)
  x=x.to(torch.float8_e4m3fn);y=y.to(torch.float8_e4m3fn).t()
  ref=x.double()@y.double();ref_cpu=x.float().cpu().double()@y.float().cpu().double() if n==256 else None
  def error(z):return {'max_abs':(z.double()-ref).abs().max().item(),'relative_l2':((z.double()-ref).norm()/ref.norm()).item()}
  for fast in [False,True]:
   one=torch.ones((),device='cuda');z=torch._scaled_mm(x,y,scale_a=one,scale_b=one,out_dtype=torch.float32,use_fast_accum=fast)
   row=dict(n=n,distribution=distribution,fast_accum=fast,**error(z))
   if ref_cpu is not None:row['gpu_vs_cpu_fp64_max']=(ref.cpu()-ref_cpu).abs().max().item()
   if not fast:
    total=torch.zeros(n,n,device='cuda')
    for k in range(0,n,32):
     xx=x[:,k:k+32].contiguous();yy=y[k:k+32,:].t().contiguous().t()
     total+=torch._scaled_mm(xx,yy,scale_a=one,scale_b=one,out_dtype=torch.float32,use_fast_accum=False)
    row['split_k32_error']=error(total)
    scaled=torch._scaled_mm(x,y,scale_a=one*.5,scale_b=one*.25,out_dtype=torch.float32,use_fast_accum=False)
    row['scale_consistency_max']=(scaled-z*.125).abs().max().item()
   out.append(row)
pathlib.Path(args.output).write_text(json.dumps(out,indent=2))
