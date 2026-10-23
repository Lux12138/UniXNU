"""Decode an Apple UDIF (.dmg) image on Linux, without hdiutil.

UDIF is a container. A 512-byte "koly" trailer at the end of the file records where the compressed
data fork and the XML property list live; the plist carries a base64 "blkx" blob that describes
every chunk -- its compressed type, offset, packed length and unpacked length. The payload is a
plain concatenation of those chunks.

Handled chunk types:
  bvxn / 0x80000008  lzvn    -> lzfse -decode
  bvx2 / 0x80000007  lzfse   -> lzfse -decode
  bvx- / 0x80000005  bzip2   -> bz2
  bvx$ / 0x80000004  zlib    -> zlib
  0x00000001         raw     -> copied
  0x00000000/2       zero    -> zeros

Usage:
  udif-decode.py <in.dmg> <out.img> [--info]
"""
import base64
import bz2
import plistlib
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

MISH = b'mish'


def _trailer(data):
    """The 512-byte koly trailer at the end of the file."""
    trailer = data[-512:]
    if trailer[:4] != b'koly':
        raise SystemExit('not a UDIF image: no koly magic')
    fields = {
        'version': struct.unpack_from('>I', trailer, 0x04)[0],
        'header_size': struct.unpack_from('>I', trailer, 0x08)[0],
        'flags': struct.unpack_from('>I', trailer, 0x0C)[0],
        'running_offset': struct.unpack_from('>Q', trailer, 0x10)[0],
        'data_offset': struct.unpack_from('>Q', trailer, 0x18)[0],
        'data_length': struct.unpack_from('>Q', trailer, 0x20)[0],
        'rsrc_offset': struct.unpack_from('>Q', trailer, 0x28)[0],
        'rsrc_length': struct.unpack_from('>Q', trailer, 0x30)[0],
        'xml_offset': struct.unpack_from('>Q', trailer, 0xD8)[0],
        'xml_length': struct.unpack_from('>Q', trailer, 0xE0)[0],
        'sector_count': struct.unpack_from('>Q', trailer, 0x1EC)[0],
    }
    return fields


def _blkx(data, trailer):
    """Pull the blkx blob out of the XML plist the trailer points at."""
    start = trailer['xml_offset']
    length = trailer['xml_length']
    if not length:
        raise SystemExit('the trailer records no XML plist')
    blob = data[start:start + length]
    if blob[:8] == b'bplist02' or blob[:6] == b'bplist':
        plist = plistlib.loads(blob)
    else:
        head = blob[:200].decode('utf-8', errors='replace')
        if '<plist' not in head:
            raise SystemExit('the XML area is not a plist: %r' % head[:80])
        plist = plistlib.loads(blob)
    entries = plist.get('resource-fork', {}).get('blkx')
    if not entries:
        raise SystemExit('the plist has no resource-fork/blkx')
    first = entries[0]
    return first.get('Data', first.get('data')), first.get('Name', '')


def _runs(blob):
    """blkx is a mish-wrapped, base64, zlib stream describing the chunks."""
    if blob[:4] != MISH:
        raise SystemExit('blkx does not start with mish')
    # Two newline-terminated header lines, then base64.
    first = blob.find(b'\n')
    second = blob.find(b'\n', first + 1)
    payload = b''.join(blob[second + 1:].split())
    table = zlib.decompress(base64.b64decode(payload))

    magic, version, first_sector, sector_count, data_offset = struct.unpack_from('>4sIQQQ', table, 0)
    if magic != MISH:
        raise SystemExit('unexpected decompressed magic %r' % magic)
    count = struct.unpack_from('>I', table, 200)[0]
    pos = 204
    runs = []
    for _ in range(count):
        kind, comment, sector, sectors, comp_off, comp_len = struct.unpack_from('>IIQQQ', table, pos)
        runs.append({'kind': kind, 'comment': comment, 'sector': sector,
                     'sectors': sectors, 'offset': comp_off, 'length': comp_len})
        pos += 40
    return {'first_sector': first_sector, 'sector_count': sector_count,
            'data_offset': data_offset, 'runs': runs}


TYPE_NAMES = {
    0x00000000: 'zero',
    0x00000001: 'raw',
    0x00000002: 'zero',
    0x80000004: 'zlib',
    0x80000005: 'bzip2',
    0x80000007: 'lzfse',
    0x80000008: 'lzvn',
}


def _inflate(kind, blob):
    if kind == 0x80000005:
        return bz2.decompress(blob)
    if kind == 0x80000004:
        return zlib.decompress(blob)
    if kind in (0x80000007, 0x80000008):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.in') as src:
            src.write(blob)
            src_path = src.name
        with tempfile.NamedTemporaryFile(delete=False, suffix='.out') as dst:
            out_path = dst.name
        try:
            subprocess.run(['/usr/bin/lzfse', '-decode', '-i', src_path, '-o', out_path], check=True)
            return Path(out_path).read_bytes()
        finally:
            Path(src_path).unlink(missing_ok=True)
            Path(out_path).unlink(missing_ok=True)
    raise SystemExit('unsupported chunk type %#x (%s)' % (kind, TYPE_NAMES.get(kind, '?')))


def decode(src, dst, info_only=False):
    data = Path(src).read_bytes()
    trailer = _trailer(data)
    print('koly: version=%(version)d flags=%(flags)d' % trailer)
    print('      data fork at %(data_offset)d (%(data_length)d bytes)' % trailer)
    print('      xml at %(xml_offset)d (%(xml_length)d bytes)' % trailer)
    gib = trailer['sector_count'] * 512 / 2**30
    print('      sector_count=%d (%.2f GiB)' % (trailer['sector_count'], gib))

    blob, name = _blkx(data, trailer)
    print('blkx: %r' % name)
    plan = _runs(blob)
    print('blkx: first_sector=%d sector_count=%d runs=%d' % (
        plan['first_sector'], plan['sector_count'], len(plan['runs'])))

    total = sum(run['sectors'] for run in plan['runs']) * 512
    print('unpacked size: %d bytes (%.2f GiB)' % (total, total / 2**30))

    if info_only:
        seen = {}
        for run in plan['runs']:
            label = TYPE_NAMES.get(run['kind'], hex(run['kind']))
            seen[label] = seen.get(label, 0) + run['sectors'] * 512
        for label, size in sorted(seen.items(), key=lambda kv: -kv[1]):
            print('  %-8s %14d bytes' % (label, size))
        return

    base = trailer['data_offset']
    with open(dst, 'wb') as out:
        for index, run in enumerate(plan['runs']):
            size = run['sectors'] * 512
            if run['kind'] in (0x00000000, 0x00000002):
                out.write(b'\0' * size)
            elif run['kind'] == 0x00000001:
                out.write(data[base + run['offset']:base + run['offset'] + run['length']])
            else:
                chunk = data[base + run['offset']:base + run['offset'] + run['length']]
                out.write(_inflate(run['kind'], chunk))
            if index % 100 == 0 or index == len(plan['runs']) - 1:
                print('  %d/%d runs' % (index + 1, len(plan['runs'])), flush=True)

    print('wrote %s' % dst)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    decode(sys.argv[1], sys.argv[2], info_only='--info' in sys.argv)
