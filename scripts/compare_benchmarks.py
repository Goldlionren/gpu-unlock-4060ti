#!/usr/bin/env python3
import argparse,json,pathlib
p=argparse.ArgumentParser();p.add_argument('stock');p.add_argument('candidate');p.add_argument('--output',default='logs/comparison.json');a=p.parse_args()
x=json.load(open(a.stock));y=json.load(open(a.candidate))
checks={k:x.get(k)==y.get(k) for k in ['torch','cuda','source_sha256','seed','precision','device']}
def fixed(r):
 lines=r['telemetry_before'].splitlines();cols=[c.strip() for c in lines[0].split(',')];vals=[c.strip() for c in lines[1].split(',')];d=dict(zip(cols,vals))
 return {k:d[k] for k in ['uuid','driver_version','vbios_version','power.limit [W]']}
checks['hardware_stack_power']=fixed(x)==fixed(y)
rows=[];ys={(r['n'],r['mode']):r for r in y['results']}
for row in x['results']:
 key=row['n'],row['mode'];other=ys.get(key,{})
 pair={'n':key[0],'mode':key[1]}
 if 'median_tflops' in row and 'median_tflops' in other:
  pair.update(stock_rate=row['median_tflops'],candidate_rate=other['median_tflops'],ratio=other['median_tflops']/row['median_tflops'],stock_relative_l2=row['relative_l2'],candidate_relative_l2=other['relative_l2'],stock_numeric_pass=row['numeric_pass'],candidate_numeric_pass=other['numeric_pass'])
 else:pair['unavailable']={'stock':row.get('error'),'candidate':other.get('error','missing')}
 rows.append(pair)
result={'compatibility_checks':checks,'comparable_metadata':all(checks.values()),'rows':rows,'caution':'Clocks, power samples, background workloads, dispatch and repeated-run variation still require assessment; ratio alone is not causal proof.'}
pathlib.Path(a.output).write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
raise SystemExit(0 if all(checks.values()) else 2)
