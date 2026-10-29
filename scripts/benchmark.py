#!/usr/bin/env python3
"""Device-resident GEMM; FP64 sampled-row reference uses quantized operands."""
import argparse, datetime, hashlib, json, pathlib, subprocess, time
p=argparse.ArgumentParser(); p.add_argument('--output',default='logs/benchmark.json'); p.add_argument('--sizes',nargs='+',type=int,default=[2048,4096,8192]); a=p.parse_args()
import torch
r={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'torch':torch.__version__,'cuda':torch.version.cuda,'source_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'seed':20261029,'state':'stock_candidate_unverified','results':[]}
def telemetry():
 q=subprocess.run(['nvidia-smi','--query-gpu=uuid,pci.bus_id,driver_version,vbios_version,power.draw,power.limit,temperature.gpu,clocks.sm,clocks.mem,utilization.gpu','--format=csv'],capture_output=True,text=True,timeout=10)
 return q.stdout or q.stderr
def save(): pathlib.Path(a.output).write_text(json.dumps(r,indent=2))
r['telemetry_before']=telemetry()
if not torch.cuda.is_available():
 r['error']='CUDA unavailable';save();raise SystemExit(2)
torch.manual_seed(r['seed']);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction=False
torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction=False
r['precision']={'tf32':False,'fp16_reduced_reduction':False,'bf16_reduced_reduction':False,'fp8_fast_accum':False}
r['device']=torch.cuda.get_device_name(0)
for n in a.sizes:
 for name,dtype in [('fp32',torch.float32),('fp16',torch.float16),('bf16',torch.bfloat16),('fp8_e4m3',torch.float8_e4m3fn),('fp8_e5m2',torch.float8_e5m2),('int8',torch.int8)]:
  row={'n':n,'mode':name};r['results'].append(row)
  try:
   free,_=torch.cuda.mem_get_info()
   if free < n*n*32: raise RuntimeError('insufficient memory reserve')
   x=(torch.randn(n,n,device='cuda')*.125).to(dtype);y=(torch.randn(n,n,device='cuda')*.125).to(dtype).t()
   if name=='int8':
    x=torch.randint(-4,5,(n,n),device='cuda',dtype=torch.int8);y=torch.randint(-4,5,(n,n),device='cuda',dtype=torch.int8).t()
   scale=torch.ones((),device='cuda')
   def op():
    if name=='int8': return torch._int_mm(x,y)
    if name.startswith('fp8'): return torch._scaled_mm(x,y,scale_a=scale,scale_b=scale,out_dtype=torch.float32,use_fast_accum=False)
    return x@y
   for _ in range(3): z=op()
   torch.cuda.synchronize();times=[]
   wall=time.perf_counter()
   for _ in range(7):
    start,end=torch.cuda.Event(enable_timing=True),torch.cuda.Event(enable_timing=True)
    start.record();z=op();end.record();end.synchronize();times.append(start.elapsed_time(end))
   row.update(ms=times,median_tflops=2*n**3/(sorted(times)[3]*1e9),wall_seconds=time.perf_counter()-wall,telemetry=telemetry())
   # 32 evenly spaced full rows, every column. FP64 accumulation reference.
   idx=torch.linspace(0,n-1,32,device='cuda').long()
   ref=x.float()[idx].double()@y.double(); actual=z[idx].double();err=(actual-ref).abs()
   row.update(reference='FP64 on quantized inputs; 32 evenly spaced rows, all columns',max_abs=err.max().item(),rmse=err.square().mean().sqrt().item(),relative_l2=(err.norm()/ref.norm()).item(),finite=bool(torch.isfinite(z).all().item()))
   row['throughput_unit']='TOP/s' if name=='int8' else 'TFLOP/s'
   row['numeric_pass']=row['finite'] and row['relative_l2'] < (1e-5 if name in ('fp32','fp8_e4m3','fp8_e5m2') else .005)
   if name=='int8': row['numeric_pass']=row['finite'] and row['max_abs']==0
   del x,y,z,ref,actual,err
  except (RuntimeError,NotImplementedError,ValueError) as e: row['error']=str(e)
  torch.cuda.empty_cache();save()
r['telemetry_after']=telemetry();save()
