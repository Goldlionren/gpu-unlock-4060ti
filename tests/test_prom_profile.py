import importlib.util
import pathlib
import struct
import json
import tempfile
import shutil
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prom_profile', ROOT/'scripts/prom_profile.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture():
    data = bytearray(512)
    data[:2] = b'\x55\xaa'
    struct.pack_into('<H', data, 24, 32)
    data[32:36] = b'PCIR'
    struct.pack_into('<H', data, 42, 24)
    struct.pack_into('<H', data, 48, 1)
    data[53] = 128
    return data


class RomChain(unittest.TestCase):
    def test_complete_and_every_truncation(self):
        data = fixture()
        self.assertEqual(m.rom_chain(data)[1], 512)
        for n in range(512):
            with self.assertRaises(ValueError):
                m.rom_chain(data[:n])

    def test_unterminated_or_zero_size(self):
        for off, value in ((53, 0), (48, 0), (0, 0), (32, 0)):
            data = fixture(); data[off] = value
            with self.assertRaises(ValueError):
                m.rom_chain(data)

    def test_npde_continuation(self):
        data = fixture() + fixture()
        data[64:68] = b'NPDE'
        struct.pack_into('<HHH', data, 68, 0x100, 11, 1)
        data[74] = 0
        images, end = m.rom_chain(data)
        self.assertEqual(end, 1024)
        self.assertEqual(len(images), 2)
        struct.pack_into('<H', data, 70, 9)
        with self.assertRaises(ValueError):
            m.rom_chain(data)

    @unittest.skipUnless((ROOT/'logs/board-capture/prom.bin').exists(), 'local board evidence absent')
    def test_reviewed_local_evidence(self):
        profile = m.verify_profile()
        self.assertEqual(profile['rom_chain_end'], 0x9a200)
        self.assertNotEqual(profile['prom_sha256'], profile['original_sha256'])

    @unittest.skipUnless((ROOT/'logs/board-capture/prom.bin').exists(), 'local board evidence absent')
    def test_profile_rejects_changed_tail_and_firmware(self):
        profile = m.verify_profile()
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root/'src').mkdir()
            for field in ('original_path', 'candidate_path', 'repeat_path'):
                dst = root/profile[field]
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/profile[field], dst)
            path = root/'src/pre-driver-prom.json'
            path.write_text(json.dumps(profile))
            candidate = root/profile['candidate_path']
            data = candidate.read_bytes()
            for offset in (0x45848, 0xfffff):
                changed = bytearray(data); changed[offset] ^= 1
                candidate.write_bytes(changed)
                with self.assertRaisesRegex(ValueError, 'full PROM capture mismatch'):
                    m.verify_profile(root)
            # Even editing the local candidate pin cannot justify a changed chain.
            changed = bytearray(data); changed[0x45848] ^= 1
            candidate.write_bytes(changed)
            (root/profile['repeat_path']).write_bytes(changed)
            profile['prom_sha256'] = m.sha(changed)
            path.write_text(json.dumps(profile))
            with self.assertRaisesRegex(ValueError, 'Firmware chain differs'):
                m.verify_profile(root)
