"""Offline admission/state-machine prototype. No hardware-write backend."""
import re
IDENTITY = {'vendor':'0x10de','device':'0x2803','subsystem_vendor':'0x1462','subsystem_device':'0x5174','revision':'0xa1','class':'0x030000'}
VBIOS = '95.06.34.00.F3'
TB_UUID = 'be030000-0062-6c0e-03f2-8ddd6ac3f908'

def admit(devices, evidence, profile):
    matches=[d for d in devices if all(d.get(k)==v for k,v in IDENTITY.items())]
    def reject(reason): return {'decision':'skip','reason':reason,'writes':0,'continue_boot':True}
    if len(matches)!=1: return reject('missing or ambiguous board identity')
    d=matches[0]
    if not re.fullmatch(r'[0-9a-f]{4}:[0-9a-f]{2}:[0-9a-f]{2}\.[0-7]',d.get('bdf','')): return reject('invalid BDF')
    if d.get('driver'): return reject('driver already bound')
    if d.get('boot_vga')!='0': return reject('display ownership unknown or active')
    for key,value in [('tb_uuid',TB_UUID),('authorized',True),('iommu',True),('stable_samples',3),('vbios',VBIOS)]:
        if evidence.get(key)!=value: return reject('missing or mismatched '+key)
    digest=profile.get('prom_sha256','')
    if not isinstance(digest,str) or not re.fullmatch('[0-9a-f]{64}',digest) or digest=='0'*64: return reject('board PROM profile incomplete')
    if evidence.get('prom_sha256')!=digest: return reject('PROM mismatch')
    if evidence.get('wpr2_hi')!=0: return reject('WPR2 not fresh')
    state=evidence.get('selector_state')
    if not isinstance(state,list) or state not in profile.get('approved_selector_states',[]): return reject('unknown register state')
    if not evidence.get('firmware_hashes_verified'): return reject('firmware not verified')
    if not profile.get('reviewed'): return reject('profile not reviewed')
    return {'decision':'simulation_eligible','bdf':d['bdf'],'writes':0,'continue_boot':True,'module_options':['targets='+d['bdf'],'ad106_experimental=1']}

def simulate_transaction(events):
    """Each gate corresponds to evidence required from an eventual kernel adapter."""
    stages=['identity_recheck','prom_recheck','fresh_wpr2','firmware_verified','fwsec','payload_halted','permissions','selector_readback','flr_containment','post_flr_selectors','driver_compute']
    log=[]
    for stage in stages:
        ok=events.get(stage) is True;log.append({'stage':stage,'passed':ok})
        if not ok:
            return {'state':'failed','log':log,'retry':False,'rollback_guaranteed':False,'hardware_writes':0}
    return {'state':'simulated_success','log':log,'retry':False,'hardware_writes':0}
