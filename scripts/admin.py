#!/usr/bin/env python3
"""Explicit administrator installer. Never reboots, unbinds, resets or flashes."""
import argparse,hashlib,json,os,pathlib,shutil,subprocess,sys,time
PROJECT=pathlib.Path(__file__).resolve().parents[1]
VERSION='1.1.1'; NAME='gpu-unlock-sm1'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def reviewed_prom_hash():
 # Load by path so imports also work from offline installer unit tests.
 import importlib.util
 spec=importlib.util.spec_from_file_location('prom_profile',PROJECT/'scripts/prom_profile.py')
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 return module.verify_profile(PROJECT)['prom_sha256']
class Installation:
 def __init__(self,root):
  self.root=pathlib.Path(root); self.staged=root!='/'
  self.state=self.path('/var/lib/gpu-unlock-sm1');self.state.mkdir(parents=True,exist_ok=True)
  self.manifest=self.state/'manifest.json'
  self.records=json.loads(self.manifest.read_text()) if self.manifest.exists() else {}
 def path(self,p):return self.root/p.lstrip('/')
 def command(self,args):
  if self.staged:return
  subprocess.run(args,check=True,timeout=600)
 def put(self,path,data,mode=0o644):
  p=self.path(path)
  if p.is_symlink():raise RuntimeError('Refuse symlink: '+path)
  if path not in self.records:
   record={'existed':p.exists()}
   if p.exists():
    backup=self.state/'backups'/path.lstrip('/');backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,backup);record['backup']=str(backup);record['mode']=p.stat().st_mode&0o777
   self.records[path]=record
  elif p.exists() and self.records[path].get('installed_sha256')!=digest(p):raise RuntimeError('Configuration drift: '+path)
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data);p.chmod(mode)
  self.records[path]['installed_sha256']=digest(p);self.save()
 def save(self):self.manifest.write_text(json.dumps(self.records,indent=2))
 def backup_boot(self):
  if self.staged:return
  k=os.uname().release
  for name in ['vmlinuz-'+k,'initrd.img-'+k]:
   p=pathlib.Path('/boot')/name
   if not p.is_file():raise RuntimeError('Missing original boot artifact: '+str(p))
   dst=self.state/'original-boot'/name;dst.parent.mkdir(exist_ok=True)
   if not dst.exists():shutil.copy2(p,dst)
   if digest(dst)!=digest(p) and name.startswith('vmlinuz'):raise RuntimeError('Kernel backup mismatch')
  for folder in ['/etc/modprobe.d','/etc/initramfs-tools','/etc/default/grub']:
   src=pathlib.Path(folder);dst=self.state/'original-config'/folder.lstrip('/')
   if not dst.exists():
    dst.parent.mkdir(parents=True,exist_ok=True)
    if src.is_dir():shutil.copytree(src,dst)
    else:shutil.copy2(src,dst)
 def install(self):
  self.backup_boot()
  capture=PROJECT/'logs/board-capture/capture.json';rom=PROJECT/'logs/board-capture/prom.bin'
  c=json.loads(capture.read_text());sha=digest(rom)
  if sha!=c['prom_sha256'] or len(rom.read_bytes())!=1048576:raise RuntimeError('PROM capture mismatch')
  subprocess.run([str(PROJECT/'build/validate_prom'),str(rom)],check=True,capture_output=True)
  # A post-driver aperture dump is not the pre-driver admission baseline.
  # Keep both originals, and revalidate the reviewed full-image provenance.
  sha=reviewed_prom_hash()
  if not self.staged:
   subprocess.run(['systemctl','is-active','ssh.service'],check=True)
   subprocess.run(['ip','route','get','192.168.100.1'],check=True)
   # Existing module ownership must be unambiguous.
   installed=subprocess.run(['modinfo','-F','version','gpu_unlock'],capture_output=True,text=True)
   if installed.returncode==0 and installed.stdout.strip()!='1.1.1-sm1':raise RuntimeError('Different gpu_unlock already installed')
  for p in (PROJECT/'src/kernel').iterdir():
   if p.suffix in ('.c','.h') and p.name!='gpu_unlock.mod.c' or p.name in ['Makefile','Kbuild','dkms.conf','LICENSE']:
    self.put('/usr/src/gpu-unlock-sm1-1.1.1/'+p.name,p.read_bytes())
  for p in (PROJECT/'build/cache/assets').glob('*.bin'):
   self.put('/usr/lib/firmware/gpu-unlock/610.43.03/'+p.name,p.read_bytes())
  self.put('/etc/gpu-unlock-sm1/profile.conf',f"PROM_SHA256='{sha}'\nTB_UUID='be030000-0062-6c0e-03f2-8ddd6ac3f908'\n".encode())
  self.put('/usr/lib/gpu-unlock-sm1/before-nvidia',(PROJECT/'integration/before-nvidia').read_bytes(),0o755)
  self.put('/etc/initramfs-tools/hooks/gpu-unlock-sm1',(PROJECT/'integration/initramfs-hook').read_bytes(),0o755)
  self.put('/etc/systemd/system/gpu-unlock-verify.service',(PROJECT/'integration/gpu-unlock-verify.service').read_bytes())
  self.put('/usr/local/bin/gpu-unlock',f'#!/bin/sh\nexec /mnt/data_nvme/yinyue-comfy/conda-env/bin/python {PROJECT}/scripts/gpu-unlock "$@"\n'.encode(),0o755)
  if not self.staged:
   state=subprocess.run(['dkms','status','-m',NAME,'-v',VERSION],capture_output=True,text=True,check=True)
   if not state.stdout.strip():self.command(['dkms','add','-m',NAME,'-v',VERSION])
   self.command(['dkms','build','--force','-m',NAME,'-v',VERSION,'-k',os.uname().release])
   self.command(['dkms','install','--force','-m',NAME,'-v',VERSION,'-k',os.uname().release])
   self.command(['systemctl','daemon-reload']);self.command(['systemctl','enable','gpu-unlock-verify.service'])
  print('Installed; no module loaded. Persistent policy is '+('ENABLED' if self.path('/etc/gpu-unlock-sm1/enabled').exists() else 'disabled')+'. Rebuild initramfs after source updates.')
 def switch(self,enable):
  if not self.manifest.exists():raise RuntimeError('Install first')
  self.backup_boot()
  if enable:
   if not self.staged and not (PROJECT/'logs/local-recovery-confirmed').exists():raise RuntimeError('Record today\'s physical recovery confirmation first')
   self.put('/etc/gpu-unlock-sm1/enabled',b'enabled\n')
   self.put('/etc/modprobe.d/gpu-unlock-sm1.conf',b'install nvidia /usr/lib/gpu-unlock-sm1/before-nvidia $CMDLINE_OPTS\n')
  else:
   # Preserve manifest entry so rollback restores any pre-existing content.
   for name in ['/etc/gpu-unlock-sm1/enabled','/etc/modprobe.d/gpu-unlock-sm1.conf']:
    p=self.path(name)
    if p.exists():
     if name not in self.records or digest(p)!=self.records[name]['installed_sha256']:raise RuntimeError('Configuration drift: '+name)
     p.unlink();self.records[name]['installed_sha256']=None
   self.save()
  self.command(['update-initramfs','-u','-k',os.uname().release])
  print('Next-boot policy: '+('enabled' if enable else 'disabled')+'. Current GPU state unchanged; no reboot performed.')
 def rollback(self):
  # Validate every managed file before changing anything.
  for name,r in self.records.items():
   p=self.path(name)
   if p.exists() and digest(p)!=r['installed_sha256']:raise RuntimeError('Configuration drift: '+name)
  if not self.staged:
   self.command(['systemctl','disable','gpu-unlock-verify.service'])
   self.command(['dkms','remove','-m',NAME,'-v',VERSION,'--all'])
  for name,r in reversed(list(self.records.items())):
   p=self.path(name)
   if r['existed']:
    p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(r['backup'],p)
   else:p.unlink(missing_ok=True)
  self.records={};self.save()
  if not self.staged:
   self.command(['systemctl','daemon-reload']);self.command(['depmod','-a']);self.command(['update-initramfs','-u','-k',os.uname().release])
  print('Managed files restored. No module unloaded; current hardware state unchanged.')
def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['install','enable','disable','rollback']);p.add_argument('--root',default='/');a=p.parse_args()
 if a.root=='/' and os.geteuid()!=0:raise SystemExit('Administrator required: run this exact command with sudo locally. No action taken.')
 i=Installation(a.root);getattr(i,a.action)() if a.action in ('install','rollback') else i.switch(a.action=='enable')
if __name__=='__main__':main()
