import importlib.util,json,os,pathlib,subprocess,tempfile,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('admin',ROOT/'scripts/admin.py');admin=importlib.util.module_from_spec(spec);spec.loader.exec_module(admin)
class Installer(unittest.TestCase):
 def test_idempotence_backup_restore_and_drift(self):
  with tempfile.TemporaryDirectory() as d:
   i=admin.Installation(d);p=i.path('/etc/example');p.parent.mkdir();p.write_bytes(b'original')
   i.put('/etc/example',b'new');i.put('/etc/example',b'new');i.put('/etc/added',b'new')
   p.write_bytes(b'other')
   with self.assertRaises(RuntimeError):i.rollback()
   p.write_bytes(b'new');i.rollback();self.assertEqual(p.read_bytes(),b'original');self.assertFalse(i.path('/etc/added').exists())
class Coordinator(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.r=pathlib.Path(self.tmp.name)
  self.base=self.r/'etc/gpu-unlock-sm1';self.base.mkdir(parents=True)
  self.sys=self.r/'sys';(self.sys/'bus/pci/devices').mkdir(parents=True)
  tb=self.sys/'bus/thunderbolt/devices/0-1';tb.mkdir(parents=True)
  (tb/'unique_id').write_text('known');(tb/'authorized').write_text('1')
  domain=tb.parent/'domain0';domain.mkdir();(domain/'iommu_dma_protection').write_text('1')
  self.dev=self.sys/'devices/pci0000:00/0000:00:07.0/0000:43:00.0';self.dev.mkdir(parents=True)
  (self.sys/'bus/pci/devices/0000:43:00.0').symlink_to(self.dev)
  for k,v in dict(vendor='0x10de',device='0x2803',subsystem_vendor='0x1462',subsystem_device='0x5174',revision='0xa1',boot_vga='0').items():(self.dev/k).write_text(v)
  (self.base/'enabled').touch();(self.base/'profile.conf').write_text("TB_UUID='known'\nPROM_SHA256='testhash'\n")
  self.calls=self.r/'calls';self.stub=self.r/'modprobe'
  self.stub.write_text(f'''#!/bin/sh
printf '%s\\n' "$*" >> {self.calls}
if [ "$1" = gpu_unlock ]; then
mkdir -p {self.sys}/module/gpu_unlock/parameters
printf '%s' "${{TEST_HANDOFF:-Y}}" > {self.sys}/module/gpu_unlock/parameters/handoff_safe
fi
''');self.stub.chmod(0o755)
  s=(ROOT/'integration/before-nvidia').read_text()
  for old,new in [('/etc/gpu-unlock-sm1',str(self.base)),('/run/gpu-unlock-sm1',str(self.r/'run')),('/sys',str(self.sys)),('/dev/kmsg',str(self.r/'kmsg')),('/sbin/modprobe',str(self.stub))]:s=s.replace(old,new)
  self.script=self.r/'wrapper';self.script.write_text(s)
 def invoke(self,unsafe=False):
  return subprocess.run(['sh',str(self.script)],env=dict(os.environ,TEST_HANDOFF='N' if unsafe else 'Y'),capture_output=True,text=True,timeout=5)
 def test_exact_dynamic_target_once(self):
  self.assertEqual(self.invoke().returncode,0);self.assertEqual(self.invoke().returncode,0)
  calls=self.calls.read_text();self.assertEqual(calls.count('gpu_unlock targets='),1);self.assertIn('targets=0000:43:00.0',calls)
 def test_disabled(self):
  (self.base/'enabled').unlink();self.assertEqual(self.invoke().returncode,0);self.assertNotIn('gpu_unlock',self.calls.read_text())
 def test_wrong_subsystem(self):
  (self.dev/'subsystem_device').write_text('0x0000');self.invoke();self.assertNotIn('gpu_unlock',self.calls.read_text())
 def test_bound(self):
  (self.dev/'driver').mkdir();self.invoke();self.assertNotIn('gpu_unlock',self.calls.read_text())
 def test_unauthorized(self):
  (self.sys/'bus/thunderbolt/devices/0-1/authorized').write_text('0');self.invoke();self.assertNotIn('gpu_unlock',self.calls.read_text())
 def test_no_device(self):
  (self.sys/'bus/pci/devices/0000:43:00.0').unlink();self.invoke();self.assertNotIn('gpu_unlock',self.calls.read_text())
 def test_failed_handoff_never_driver_or_retry(self):
  self.assertEqual(self.invoke(unsafe=True).returncode,1);self.assertEqual(self.invoke().returncode,1)
  calls=self.calls.read_text();self.assertEqual(calls.count('gpu_unlock targets='),1);self.assertNotIn('--ignore-install',calls)
