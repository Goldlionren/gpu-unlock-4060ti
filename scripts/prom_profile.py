"""Offline verification of the reviewed pre-driver PROM profile; no hardware I/O.

The complete candidate digest is pinned in source-controlled profile data.
ROM-chain equivalence supplies independent provenance, never a runtime hash bypass.
"""
import hashlib
import json
import pathlib
import struct
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]


def rom_chain(data):
    """Walk PCI/NVIDIA image headers, including NPDE continuation and bounds."""
    def check(off, length):
        if off < 0 or length < 0 or off + length > len(data):
            raise ValueError('ROM structure exceeds image bounds')

    def word(off):
        check(off, 2)
        return struct.unpack_from('<H', data, off)[0]

    pos, images = 0, []
    for _ in range(8):
        check(pos, 26)
        if word(pos) not in (0xaa55, 0x4e56, 0xbb77):
            raise ValueError('Invalid ROM signature')
        pcir = pos + word(pos + 24)
        check(pcir, 24)
        if data[pcir:pcir+4] not in (b'PCIR', b'NPDS', b'RGIS'):
            raise ValueError('Invalid ROM data signature')
        size, last = word(pcir + 16) * 512, bool(data[pcir + 21] & 128)
        npde = (pcir + word(pcir + 10) + 15) & ~15
        if data[npde:npde+4] == b'NPDE':
            check(npde, 10)
            if word(npde + 4) in (0x100, 0x101):
                length = word(npde + 6)
                if length < 10:
                    raise ValueError('Short NPDE')
                check(npde, length)
                sub = word(npde + 8) * 512
                last = bool(data[npde+10] & 128) if length > 10 else last and sub >= size
                size = sub
        if not size:
            raise ValueError('Empty ROM image')
        check(pos, size)
        if pcir + 24 > pos + size:
            raise ValueError('ROM data header outside its image')
        images.append({'offset': pos, 'size': size, 'type': data[pcir + 20], 'last': last})
        pos += size
        if last:
            return images, pos
    raise ValueError('Unterminated ROM chain')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_profile(root=ROOT):
    root = pathlib.Path(root)
    profile = json.loads((root/'src/pre-driver-prom.json').read_text())
    if profile.get('reviewed') is not True:
        raise ValueError('Pre-driver image has not been reviewed')
    original = (root/profile['original_path']).read_bytes()
    candidate = (root/profile['candidate_path']).read_bytes()
    repeat = (root/profile['repeat_path']).read_bytes()
    for data, digest in ((original, profile['original_sha256']),
                         (candidate, profile['prom_sha256']), (repeat, profile['prom_sha256'])):
        if len(data) != 1048576 or sha(data) != digest:
            raise ValueError('Reviewed full PROM capture mismatch')
    images, end = rom_chain(original)
    if (images, end) != rom_chain(candidate) or end != profile['rom_chain_end']:
        raise ValueError('ROM geometry mismatch')
    if original[:end] != candidate[:end] or sha(candidate[:end]) != profile['rom_chain_sha256']:
        raise ValueError('Firmware chain differs from original trusted capture')
    if candidate[end:] != b'\xff' * (len(candidate) - end):
        raise ValueError('Unexpected early aperture tail')
    parsed = []
    for name in ('original_path', 'candidate_path', 'repeat_path'):
        result = subprocess.run([str(root/'build/validate_prom'), str(root/profile[name])],
                                capture_output=True, text=True, check=True)
        parsed.append(json.loads(result.stdout))
    if not all(x == profile['fwsec'] for x in parsed):
        raise ValueError('Independent FWSEC parser geometry mismatch')
    return profile


if __name__ == '__main__':
    print(json.dumps(verify_profile(), indent=2))
