"""Userdata payload: the raw image for the device's `userdata` partition.

It holds the unchanged OS and SystemOS disk images of the IPSW, byte for byte, behind a small manifest
(the SHNGROOT layout the native UFS root driver reads):

    0x000000  manifest block (4096 bytes), zero padding to 1 MiB
    0x100000  window "OS"        the whole attached OS disk image, 1 MiB aligned
    ....      window "SystemOS"  the whole attached SystemOS disk image, 1 MiB aligned

Manifest (little endian): "SHNGROOT", u32 version=1, u32 count, u64 image_bytes, then `count` 128-byte entries
{char name[32], u64 offset, u64 size, u32 block_size=512, u32 flags(1=read-only), u8 sha256[32], 40 reserved},
and at byte 4064 the SHA-256 of bytes 0..4063.

The images come from the IPSW (a local file or a remote URL, see ipsw.py) and are checked against the pins of
board.toml. The disk images are attached read-only without mounting (macOS hdiutil). Nothing is flashed: the
report prints the fastboot command, to be run by the user.
"""
import hashlib
import io
import json
import plistlib
import re
import struct
import subprocess
import sys

HOST = sys.platform

from . import udif
from .ipsw import Ipsw
from .util import Error, log, run, sha256_file, tool

MIB = 1 << 20
CHUNK = 8 * MIB


def paths(ctx):
    out = ctx.work / 'userdata'
    return out, out / 'userdata-root.img', out / 'userdata-root.json'


def is_udif(dmg):
    with open(dmg, 'rb') as handle:
        return udif.is_udif(handle)


def image_size(dmg):
    """Bytes the window will hold: the raw image for a bare one, the unpacked size for UDIF."""
    if not is_udif(dmg):
        return dmg.stat().st_size
    if HOST == 'Darwin':
        info = subprocess.run(['hdiutil', 'imageinfo', '-plist', str(dmg)],
                             capture_output=True, check=True).stdout
        return plistlib.loads(info)['Size Information']['Total Bytes']
    # 7z l -slt lists the dmg member first with Comment = Apple_APFS and its unpacked Size;
    # the inner APFS layer that follows carries no Size at all.
    listing = subprocess.run(['7z', 'l', '-slt', str(dmg)], capture_output=True,
                             text=True, check=True).stdout
    for block in listing.split('----------'):
        heading = {}
        for line in block.splitlines():
            if ' = ' in line and not line.startswith(' '):
                key, value = line.split(' = ', 1)
                heading[key] = value
        if heading.get('Comment') == 'Apple_APFS' and heading.get('Size', '').isdigit():
            return int(heading['Size'])
        if heading.get('Type') in ('APFS', 'HFS') and heading.get('Size', '').isdigit():
            return int(heading['Size'])
    raise Error(f'7z reported no APFS member in {dmg}')

def attach(dmg):
    """Return a path to the raw APFS image this dmg carries.

    A bare image is handed back untouched. A UDIF container is unpacked by walking its mish block
    map, which is what hdiutil would do on macOS -- 7-Zip walks the same map but ends up with the
    file tree instead of the raw partition, and build() needs the raw bytes.
    """
    if not is_udif(dmg):
        return str(dmg)

    out = dmg.parent / (dmg.stem + '.apfs')
    if out.is_file() and out.stat().st_size:
        return str(out)

    with open(dmg, 'rb') as handle:
        trailer = udif.read_trailer(handle)
        handle.seek(trailer['plist_offset'])
        plist = plistlib.loads(handle.read(trailer['plist_length']))

        entry = None
        for item in plist['resource-fork']['blkx']:
            if item.get('Name') in ('Apple_APFS', 'Apple_HFS', 'Apple_HFSX'):
                entry = item
                break
        if entry is None:
            raise Error(f'no APFS or HFS partition in {dmg}')

        runs = udif.read_runs(entry.get('Data', entry.get('data')))
        log(f'userdata: unpacking {entry.get("Name")} '
            f'({sum(r["sectors"] for r in runs) * 512 >> 20} MiB, {len(runs)} runs)')

        with open(out, 'wb') as sink:
            udif.unpack(handle, sink, runs, trailer['data_offset'])
    return str(out)


def detach(device):
    if HOST == 'Darwin':
        subprocess.run(['hdiutil', 'detach', device], capture_output=True)

def build(ctx, dry_run=False):
    log('userdata payload')
    spec = ctx.board.get('userdata')
    if not spec:
        raise Error('board.toml has no [userdata]')
    if HOST == 'Darwin':
        tool('hdiutil', 'the disk images are attached with macOS hdiutil')
    else:
        tool('7z', 'the disk images are unpacked with 7-Zip, which reads DMG with LZFSE')
    source = Ipsw(ctx)
    capacity = (spec['last_lba'] - spec['first_lba'] + 1) * spec.get('lba_bytes', 4096)
    if dry_run:
        for window in spec['windows']:
            name, size, _ = source.info(window['component'])
            log(f'userdata: {window["name"]} would be extracted from {name} ({size >> 20} MiB)')
        log('userdata: dry run, nothing extracted or written')
        return None
    sources = [(window['name'], source.extract(window['component'])) for window in spec['windows']]
    layout, cursor = [], MIB
    for name, dmg in sources:
        size = image_size(dmg)
        layout.append((name, cursor, size))
        cursor += (size + MIB - 1) // MIB * MIB
    total = cursor
    log(f'userdata: image {total} bytes ({total / 2**30:.2f} GiB) in a partition of {capacity} bytes')
    if total > capacity:
        raise Error('the image is larger than the userdata partition')
    for name, dmg in sources:
        log(f'userdata: {name} from {dmg.name}')
    out, image, report = paths(ctx)
    out.mkdir(parents=True, exist_ok=True)
    entries = []
    with image.open('wb') as target:
        target.truncate(total)
        for (name, offset, size), (_, dmg) in zip(layout, sources):
            device = attach(dmg)
            try:
                raw = (device.replace('/dev/disk', '/dev/rdisk') if HOST == 'Darwin' else device)
                digest = hashlib.sha256()
                target.seek(offset)
                done = 0
                with open(raw, 'rb', buffering=0) as handle:
                    while done < size:
                        want = min(CHUNK, size - done)
                        data = handle.read(want)
                        if len(data) != want:
                            raise Error(f'short read from {raw} at {done}')
                        digest.update(data)
                        target.write(data)
                        done += want
            finally:
                detach(device)
            entries.append((name, offset, size, digest.digest()))
            log(f'userdata: {name} {size} bytes at {offset:#x} sha256 {digest.hexdigest()}')
        header = bytearray(4096)
        header[0:8] = b'SHNGROOT'
        struct.pack_into('<IIQ', header, 8, 1, len(entries), total)
        for index, (name, offset, size, digest) in enumerate(entries):
            struct.pack_into('<32sQQII32s40s', header, 24 + 128 * index, name.encode(), offset, size, 512, 1, digest, bytes(40))
        header[4064:4096] = hashlib.sha256(bytes(header[:4064])).digest()
        target.seek(0)
        target.write(header)
    data = {'image_bytes': total, 'image_sha256': sha256_file(image), 'manifest_sha256': hashlib.sha256(bytes(header)).hexdigest(),
            'windows': [{'name': n, 'offset': o, 'size': s, 'sha256': d.hex()} for n, o, s, d in entries],
            'userdata_bytes': capacity, 'flash_command': f'fastboot flash userdata {image}',
            'source': 'remote' if source.remote else 'local', 'hardware_tested': False}
    report.write_text(json.dumps(data, indent=2) + '\n')
    log(f'userdata: {image}')
    log(f'flash it yourself with: {data["flash_command"]}')
    return image
