"""UDIF helpers for userdata.py, following the published DMG format.

Sources: the DMG format specification (dil4rd/dpp udif/docs/FORMATS.md) and aaru-dps/docs/DMG.html.

Layout this relies on:

  koly trailer   512 bytes at end; plist offset at 216, plist length at 224
  mish header    204 bytes; the real run count is at offset 200, not 36
  block run      40 bytes from 204: type, comment, sector, sectors, comp_offset, comp_length
  block types    0 zero-fill, 1 raw, 2 ignore, 0x80000005 zlib, 0x80000006 bzip2,
                 0x80000007 LZFSE, 0x80000008 XZ
  sectors        always 512 bytes
"""
import struct
import subprocess

MISH = b'mish'
KOLY = b'koly'
MISH_HEADER = 204
RUN_SIZE = 40

ZERO = 0x00000000
RAW = 0x00000001
IGNORE = 0x00000002
ZLIB = 0x80000005
BZIP2 = 0x80000006
LZFSE = 0x80000007
XZ = 0x80000008
COMMENT = 0x7FFFFFFE
END = 0xFFFFFFFF


def is_udif(handle):
    handle.seek(0)
    head = handle.read(4)
    handle.seek(-512, 2)
    tail = handle.read(4)
    return head in (b'bvxn', b'bvx2', b'bvx-') or tail == KOLY


def read_trailer(handle):
    handle.seek(-512, 2)
    t = handle.read(512)
    if t[:4] != KOLY:
        raise ValueError('no koly trailer')
    return {
        'data_offset': struct.unpack_from('>Q', t, 24)[0],
        'data_length': struct.unpack_from('>Q', t, 32)[0],
        'plist_offset': struct.unpack_from('>Q', t, 216)[0],
        'plist_length': struct.unpack_from('>Q', t, 224)[0],
    }


def read_runs(mish):
    """Parse one partition's mish table into block runs."""
    if mish[:4] != MISH:
        raise ValueError('not a mish block')
    count = struct.unpack_from('>I', mish, 200)[0]
    runs = []
    pos = MISH_HEADER
    for _ in range(count):
        if pos + RUN_SIZE > len(mish):
            break
        kind, comment, sector, sectors, comp_off, comp_len = struct.unpack_from('>IIQQQQ', mish, pos)
        runs.append({
            'kind': kind,
            'sector': sector,
            'sectors': sectors,
            'offset': comp_off,
            'length': comp_len,
        })
        pos += RUN_SIZE
    return runs


def decompress(kind, blob):
    """Turn one compressed block into its output bytes."""
    if kind == ZLIB:
        import zlib
        return zlib.decompress(blob)
    if kind == BZIP2:
        import bz2
        return bz2.decompress(blob)
    if kind == LZFSE:
        return _lzfse(blob)
    if kind == XZ:
        return subprocess.run(['xz', '-dc'], input=blob, capture_output=True, check=True).stdout
    raise ValueError('unsupported block type %#x' % kind)


def _lzfse(blob):
    """Apple's lzfse handles bvxn, bvx- and bvx$ through the bundled decoder."""
    import tempfile
    from pathlib import Path
    with tempfile.NamedTemporaryFile(suffix='.in', delete=False) as src:
        src.write(blob)
        src_path = src.name
    with tempfile.NamedTemporaryFile(suffix='.out', delete=False) as dst:
        out_path = dst.name
    try:
        subprocess.run(['/usr/bin/lzfse', '-decode', '-i', src_path, '-o', out_path], check=True)
        return Path(out_path).read_bytes()
    finally:
        Path(src_path).unlink(missing_ok=True)
        Path(out_path).unlink(missing_ok=True)


def unpack(handle, sink, runs, base):
    """Write every run to sink in order, reading compressed bytes from handle at base+offset."""
    total = 0
    for run in runs:
        size = run['sectors'] * 512
        if run['kind'] in (END, COMMENT):
            # Terminators and comments carry no output.
            continue
        if run['kind'] in (ZERO, IGNORE):
            sink.write(b'\0' * size)
        elif run['kind'] == RAW:
            handle.seek(base + run['offset'])
            sink.write(handle.read(run['length']))
        else:
            handle.seek(base + run['offset'])
            sink.write(decompress(run['kind'], handle.read(run['length'])))
        total += size
    return total
