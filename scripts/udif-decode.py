"""Decode an Apple UDIF (.dmg) image on Linux, without hdiutil.

UDIF is a container. A 512-byte "koly" trailer at the end records where the compressed data fork
and the XML property list live. The plist's resource-fork/blkx array holds one entry per partition
("MBR", "Primary GPT Header", "Apple_HFS", ...), and each entry's Data is a binary mish table:

    u32  'mish'
    u32  version
    u64  first_sector
    u64  sector_count
    u64  data_offset
    u32  buffers_needed
    u32  block_descriptors
    u8   reserved[24]
    run[block_descriptors]        40 bytes each:
        u32 type, u32 comment, u64 sector, u64 sectors, u64 offset, u64 length

Chunk types:
  0x00000000 / 0x00000002  zero
  0x00000001               raw
  0x80000004               zlib
  0x80000005               bzip2
  0x80000007               lzfse
  0x80000008               lzvn

Usage:
  udif-decode.py <in.dmg> <out.img> [--info] [--entry NAME]
"""
import bz2
import plistlib
import struct
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path

MISH = b'mish'
ENTRY_HEADER = 64
RUN_SIZE = 40

TYPE_NAMES = {
    0x00000000: 'zero',
    0x00000001: 'raw',
    0x00000002: 'zero',
    0x80000004: 'zlib',
    0x80000005: 'bzip2',
    0x80000007: 'lzfse',
    0x80000008: 'lzvn',
}


def trailer(data):
    t = data[-512:]
    if t[:4] != b'koly':
        raise SystemExit('not a UDIF image: no koly magic')
    return {
        'version': struct.unpack_from('>I', t, 0x04)[0],
        'flags': struct.unpack_from('>I', t, 0x0C)[0],
        'data_offset': struct.unpack_from('>Q', t, 0x18)[0],
        'data_length': struct.unpack_from('>Q', t, 0x20)[0],
        'xml_offset': struct.unpack_from('>Q', t, 0xD8)[0],
        'xml_length': struct.unpack_from('>Q', t, 0xE0)[0],
        'sector_count': struct.unpack_from('>Q', t, 0x1EC)[0],
    }


def entries(data, koly):
    """Every resource-fork/blkx entry, with its binary mish table already parsed."""
    blob = data[koly['xml_offset']:koly['xml_offset'] + koly['xml_length']]
    plist = plistlib.loads(blob)
    out = []
    for item in plist['resource-fork']['blkx']:
        raw = item.get('Data', item.get('data'))
        name = item.get('Name', item.get('name', ''))
        out.append({'name': name, 'runs': parse_mish(raw)})
    return out


def parse_mish(raw):
    if raw[:4] != MISH:
        raise SystemExit('blkx entry does not start with mish: %r' % raw[:8])
    version = struct.unpack_from('>I', raw, 4)[0]
    first_sector = struct.unpack_from('>Q', raw, 8)[0]
    sector_count = struct.unpack_from('>Q', raw, 16)[0]
    data_offset = struct.unpack_from('>Q', raw, 24)[0]
    block_descriptors = struct.unpack_from('>I', raw, 36)[0]

    # Some writers put 0 in block_descriptors and rely on the buffer size instead; fall back to
    # "as many as fit".
    if not block_descriptors:
        block_descriptors = (len(raw) - ENTRY_HEADER) // RUN_SIZE

    runs = []
    pos = ENTRY_HEADER
    for _ in range(block_descriptors):
        if pos + RUN_SIZE > len(raw):
            break
        kind, comment, sector, sectors, offset, length = struct.unpack_from('>IIQQQQ', raw, pos)
        runs.append({'kind': kind, 'comment': comment, 'sector': sector,
                     'sectors': sectors, 'offset': offset, 'length': length})
        pos += RUN_SIZE
    return {'version': version, 'first_sector': first_sector, 'sector_count': sector_count,
            'data_offset': data_offset, 'runs': runs}


def inflate(kind, blob):
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


def decode(src, dst, info_only=False, only=None):
    data = Path(src).read_bytes()
    koly = trailer(data)
    print('koly: version=%(version)d flags=%(flags)d' % koly)
    print('      data fork at %(data_offset)d (%(data_length)d bytes)' % koly)
    print('      xml at %(xml_offset)d (%(xml_length)d bytes)' % koly)
    print('      whole image sector_count=%(sector_count)d (%.2f GiB)'
          % (koly['sector_count'], koly['sector_count'] * 512 / 2**30))

    parts = entries(data, koly)
    print('partitions: %d' % len(parts))
    for part in parts:
        plan = part['runs']
        size = plan['sector_count'] * 512
        print('  %-28s sector %8d + %8d  = %10d bytes  runs=%d'
              % (part['name'], plan['first_sector'], plan['sector_count'], size, len(plan['runs'])))

    if info_only:
        print()
        for part in parts:
            seen = {}
            for run in part['runs']['runs']:
                label = TYPE_NAMES.get(run['kind'], hex(run['kind']))
                seen[label] = seen.get(label, 0) + run['sectors'] * 512
            if seen:
                print('  %s:' % part['name'])
                for label, size in sorted(seen.items(), key=lambda kv: -kv[1]):
                    print('    %-8s %14d bytes' % (label, size))
        return

    target = None
    if only:
        for part in parts:
            if part['name'] == only:
                target = part
                break
        if target is None:
            raise SystemExit('no partition named %r' % only)
    else:
        # The whole disk is the largest partition.
        target = max(parts, key=lambda p: p['runs']['sector_count'])

    plan = target['runs']
    size = plan['sector_count'] * 512
    print('writing %r: %d bytes (%.2f GiB), %d runs'
          % (target['name'], size, size / 2**30, len(plan['runs'])))

    base = koly['data_offset']
    written = 0
    with open(dst, 'wb') as out:
        for index, run in enumerate(plan['runs']):
            count = run['sectors'] * 512
            if run['kind'] in (0x00000000, 0x00000002):
                out.write(b'\0' * count)
            elif run['kind'] == 0x00000001:
                out.write(data[base + run['offset']:base + run['offset'] + run['length']])
            else:
                chunk = data[base + run['offset']:base + run['offset'] + run['length']]
                out.write(inflate(run['kind'], chunk))
            written += count
            if index % 100 == 0 or index == len(plan['runs']) - 1:
                print('  %d/%d runs, %d bytes' % (index + 1, len(plan['runs']), written), flush=True)

    print('wrote %s (%d bytes)' % (dst, written))


if __name__ == '__main__':
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    only = None
    if '--entry' in sys.argv:
        only = sys.argv[sys.argv.index('--entry') + 1]
    decode(sys.argv[1], sys.argv[2], info_only='--info' in sys.argv, only=only)
