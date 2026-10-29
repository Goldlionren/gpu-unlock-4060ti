#!/usr/bin/env python3
import json,torch
assert torch.cuda.is_available()
torch.backends.cuda.matmul.allow_tf32=False
torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction=False
torch.backends.cuda.matmul.allow_bf16_reduced_precision_reduction=False
results={}
for name,dtype in [('fp16',torch.float16),('bf16',torch.bfloat16)]:
 # Exact integer dot products below both output formats' exact range.
 x=(torch.arange(128*128,device='cuda').reshape(128,128)%3-1).to(dtype)
 y=(torch.arange(128*128,device='cuda').reshape(128,128)%5-2).to(dtype)
 z=x@y;reference=x.double()@y.double()
 results[name]={'pass':bool(torch.equal(z.double(),reference)),'max_abs':(z.double()-reference).abs().max().item()}
torch.cuda.synchronize();print(json.dumps(results));assert all(x['pass'] for x in results.values())
