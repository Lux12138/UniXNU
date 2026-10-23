"""Decode an Apple UDIF (.dmg) image on Linux, without hdiutil.

UDIF is a container: a "koly" trailer at the end points at a blkx table that describes every chunk
of the payload -- its compressed type, where it starts, how big it is packed and unpacked. The
payload itself is a plain concatenation of those chunks.

What this handles:
  bvxn  lzvn   -> lzfse -decode
  bvx2  lzfse  -> lzfse -decode
  bvx-  bzip2  -> bzip2 -d
  bvx$  zlib   -> zlib.decompress
  rawz  raw    -> copied as-is

Usage:
  udif-decode.py <in.dmg> <out.img> [--info]
"""
import base64
import bz2
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

KOLY = b'koly'
MISH = b'mish'


def _koly(data):
    """Read the 512-byte trailer that sits at the end of every UDIF image."""
    trailer = data[-512:]
    if trailer[:4] != KOLY:
        raise SystemExit('not a UDIF image: no koly trailer')
    fields = struct.unpack_from('>4sIIIII', trailer, 0)
    _, version, header_size, flags, running_offset, data_offset = fields
    xml_offset, xml_length = struct.unpack_from('>QQ', trailer, 0xd8)
    return {
        'version': version,
        'header_size': header_size,
        'data_offset': data_offset,
        'xml_offset': xml_offset,
        'xml_length': xml_length,
        'trailer': trailer,
    }


def _blkx_table(trailer):
    """The blkx entries live in the trailer's resource-fork section."""
    # Trailer layout after the fixed header: a run of
    #   u32 type, u32 size, u64 offset   -- offset counts from the start of the trailer
    pos = 0x40
    entries = []
    while pos + 16 <= 0x1d0:
        kind, size, offset = struct.unpack_from('>IIQ', trailer, pos)
        if kind == 0 or size == 0:
            break
        entries.append((kind, size, offset))
        pos += 16
    return entries


def _decode_blkx(blob):
    """blkx data is Mish-wrapped: a little header, then base64 of a zlib stream."""
    if blob[:4] != MISH:
        raise SystemExit('blkx block does not start with mish')
    start = blob.find(b'\n', blob.find(b'\n') + 1)   # skip the two header lines
    payload = blob[start + 1:]
    payload = b''.join(payload.split())
    return zlib.decompress(base64.b64decode(payload))


def _runs(table):
    """Parse the decompressed blkx table into chunk descriptors."""
    magic, version, first_sector, sector_count, data_offset = struct.unpack_from('>4sIQQQ', table, 0)
    if magic != MISH:
        raise SystemExit('unexpected blkx magic %r' % magic)
    count = struct.unpack_from('>I', table, 200)[0]
    pos = 204
    out = []
    for _ in range(count):
        entry = table[pos:pos + 40]
        kind, comment, sector, sectors, comp_off, comp_len = struct.unpack_from('>IIQQQ', entry, 0)
        out.append({
            'kind': kind,
            'sector': sector,
            'sectors': sectors,
            'offset': comp_off,
            'length': comp_len,
        })
        pos += 40
    return {
        'first_sector': first_sector,
        'sector_count': sector_count,
        'data_offset': data_offset,
        'runs': out,
    }


TYPE_NAMES = {
    0x00000000: 'zero',
    0x00000001: 'raw',
    0x00000002: 'zero',
    0x10000005: 'ADC',
    0x80000004: 'zlib',
    0x80000005: 'bzip2',
    0x80000006: 'ADC',
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
        subprocess.run(['/usr/bin/lzfse', '-decode', '-i', src_path, '-o', out_path], check=True)
        data = Path(out_path).read_bytes()
        Path(src_path).unlink(missing_ok=True)
        Path(out_path).unlink(missing_ok=True)
        return data
    if kind in (0x00000000, 0x00000002):
        return b''
    raise SystemExit('unsupported chunk type %#x (%s)' % (kind, TYPE_NAMES.get(kind, '?')))


def decode(src, dst, info_only=False):
    data = Path(src).read_bytes()
    koly = _koly(data)
    print('koly: version=%d data_offset=%d xml=%d bytes' % (
        koly['version'], koly['data_offset'], koly['xml_length']))

    entries = _blkx_table(koly['trailer'])
    print('trailer entries: %d' % len(entries))
    blkx = None
    for kind, size, offset in entries:
        blob = koly['trailer'][offset:offset + size]
        if blob[:4] == MISH:
            blkx = blob
            print('blkx: type=%#x size=%d at trailer offset %d' % (kind, size, offset))
            break
    if blkx is None:
        raise SystemExit('no mish block found in the trailer')

    table = _decode_blkx(blkx)
    plan = _runs(table)
    print('blkx: first_sector=%d sector_count=%d runs=%d' % (
        plan['first_sector'], plan['sector_count'], len(plan['runs'])))

    total = sum(run['sectors'] for run in plan['runs']) * 512
    print('output would be %d bytes (%.2f GiB)' % (total, total / 2**30))

    if info_only:
        seen = {}
        for run in plan['runs']:
            name = TYPE_NAMES.get(run['kind'], hex(run['kind']))
            seen[name] = seen.get(name, 0) + run['sectors'] * 512
        for name, size in sorted(seen.items(), key=lambda kv: -kv[1]):
            print('  %-8s %12d bytes' % (name, size))
        return

    written = 0
    with open(dst, 'wb') as out:
        for index, run in enumerate(plan['runs']):
            size = run['sectors'] * 512
            if run['kind'] in (0x00000000, 0x00000002):
                out.write(b'\0' * size)
            elif run['kind'] == 0x00000001:
                start = koly['data_offset'] + run['offset']
                out.write(data[start:start + run['length']])
            else:
                start = koly['data_offset'] + run['offset']
                blob = data[start:start + run['length']]
                out.write(_inflate(run['kind'], blob))
            written += size
            if index % 200 == 0 or index == len(plan['runs']) - 1:
                print('  %d/%d runs, %d bytes' % (index + 1, len(plan['runs']), written), flush=True)

    print('wrote %s (%d bytes)' % (dst, written))


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    decode(sys.argv[1], sys.argv[2], info_only='--info' in sys.argv)
