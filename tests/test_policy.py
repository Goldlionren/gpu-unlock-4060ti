import copy,sys,pathlib,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'src'))
from policy import IDENTITY,VBIOS,TB_UUID,admit,simulate_transaction
class PolicyTests(unittest.TestCase):
 def setUp(self):
  self.d=dict(IDENTITY,bdf='0000:05:00.0',driver=None,boot_vga='0')
  self.p={'prom_sha256':'a'*64,'reviewed':True,'approved_selector_states':[[0,0]]}
  self.e=dict(tb_uuid=TB_UUID,authorized=True,iommu=True,stable_samples=3,vbios=VBIOS,prom_sha256='a'*64,wpr2_hi=0,selector_state=[0,0],firmware_hashes_verified=True)
 def test_relocated_bdf(self):
  self.d['bdf']='0000:43:00.0';self.assertEqual(admit([self.d],self.e,self.p)['bdf'],'0000:43:00.0')
 def test_identity_fields(self):
  for k in IDENTITY:
   d=dict(self.d);d[k]='0xffff';self.assertEqual(admit([d],self.e,self.p)['decision'],'skip')
 def test_absent_and_ambiguous(self):
  for ds in [[],[self.d,self.d]]:self.assertEqual(admit(ds,self.e,self.p)['decision'],'skip')
 def test_missing_evidence(self):
  for k in self.e:
   e=dict(self.e);e.pop(k);self.assertEqual(admit([self.d],e,self.p)['decision'],'skip',k)
 def test_bound_warm_unknown(self):
  for key,value in [('wpr2_hi',16),('selector_state',[1,2]),('authorized',False),('prom_sha256','b'*64)]:
   e=dict(self.e);e[key]=value;self.assertEqual(admit([self.d],e,self.p)['decision'],'skip')
  self.d['driver']='nvidia';self.assertEqual(admit([self.d],self.e,self.p)['decision'],'skip')
 def test_unreviewed(self):
  self.p['reviewed']=False;self.assertEqual(admit([self.d],self.e,self.p)['decision'],'skip')
 def test_discovery_profile_cannot_admit(self):
  import json
  profile=json.loads((pathlib.Path(__file__).resolve().parents[1]/'src/board-profile.json').read_text())
  self.assertEqual(admit([self.d],self.e,profile)['decision'],'skip')
 def test_failure_never_retries(self):
  stages=['identity_recheck','prom_recheck','fresh_wpr2','firmware_verified','fwsec','payload_halted','permissions','selector_readback','flr_containment','post_flr_selectors','driver_compute']
  for stage in stages:
   e=dict.fromkeys(stages,True);e[stage]=False;r=simulate_transaction(e)
   self.assertEqual(r['log'][-1]['stage'],stage);self.assertFalse(r['retry']);self.assertEqual(r['hardware_writes'],0)
if __name__=='__main__':unittest.main()
