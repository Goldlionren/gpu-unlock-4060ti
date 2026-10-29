import importlib.util,pathlib,unittest
p=pathlib.Path(__file__).resolve().parents[1]/'scripts/analyze_prom.py'
s=importlib.util.spec_from_file_location('analyze_prom',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class PromAnalysis(unittest.TestCase):
 def test_equal(self):self.assertTrue(m.compare(b'abc',b'abc')['same'])
 def test_first_offset(self):self.assertEqual(m.compare(b'abc',b'axc')['first_difference'],1)
 def test_truncated(self):
  r=m.compare(b'abc',b'ab');self.assertFalse(r['same']);self.assertEqual(r['first_difference'],2);self.assertEqual(r['length_difference'],-1)
 def test_block_boundary(self):self.assertEqual(m.compare(bytes(8192),bytes(4096)+b'x'+bytes(4095))['different_4k_blocks'],[4096])
