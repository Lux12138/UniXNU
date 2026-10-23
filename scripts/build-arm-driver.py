#!/usr/bin/env python3
"""Compile the generic platform expert against the actual source-kernel ABI."""
import argparse
import os
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('component', choices=['ArmVirtPlatform', 'ArmDTPlatform', 'ArmCpu', 'NativeAES', 'NativeVirtioBlock', 'NativeRamBlock', 'NativeMobileDisplay', 'NativeVirtioConsole', 'NativeLegacyDisplay', 'NativeGOPPresenter', 'NativeOfflineGPU', 'NativeOfflineAccelerator', 'NativeIOGPUProviderProbe', 'NativeUfs', 'NativeHidInput', 'NativeKeyStoreEvents', 'NativeAdreno'])
parser.add_argument('--negative-aes-kat', action='store_true', help='Isolated own-source wrong-answer refusal control; never changes original inputs')
parser.add_argument('--verified-root', action='store_true', help='Authenticate all actual disk reads against an independently signed immutable policy')
parser.add_argument('--verified-root-bundle', action='store_true', help='Select exactly one capacity-matching policy per device, then independently authenticate it')
parser.add_argument('--negative-verified-block', action='store_true', help='Negative own-buffer control: corrupt only the completed DMA snapshot')
# Bring-up mode from UniXNU-uke: compile the NativeUfs transport without the
# verified-root policy bundle, so the running controller can be adopted before any
# signed policy exists. Without it the fork expects kits/VerifiedRoot, which this
# tree does not carry.
parser.add_argument('--unverified', action='store_true', help='NativeUfs: compile the bring-up transport without the verified-root policy bundle')
args = parser.parse_args()
if args.unverified and args.component != 'NativeUfs':
    parser.error('--unverified currently applies to the NativeUfs bring-up transport only')
if args.verified_root_bundle and not args.verified_root:
    parser.error('A policy bundle requires verified block mode')
if args.verified_root_bundle and args.negative_verified_block:
    parser.error('Select either bundle policy qualification or the isolated DMA snapshot fault')
if (args.verified_root or args.negative_verified_block) and args.component != 'NativeVirtioBlock':
    parser.error('Verified block mode requires the concrete read-only block transport')
if args.negative_verified_block and not args.verified_root:
    parser.error('The isolated input fault requires verified block mode')
component = args.component
recipe = ROOT / 'build/xnu/ios-obj/DEVELOPMENT_ARM64_BCM2837/iokit/DEVELOPMENT/IOPlatformExpert.cpo.json'
record = json.loads(recipe.read_text().strip().rstrip(','))
source = ROOT / 'drivers' / ('NativeMobileDisplay' if component in ('NativeLegacyDisplay','NativeGOPPresenter') else 'NativeMetal' if component in ('NativeOfflineGPU','NativeOfflineAccelerator','NativeIOGPUProviderProbe') else component) / {'NativeAdreno':'NativeAdrenoService.cpp'}.get(component, component + '.cpp')

if component == 'NativeUfs' and os.environ.get('XNU_NABU_UFS_REGISTER_PROBE') == '1':
    # Read-only register probe in place of the block driver. No MMIO store, no DMA, no
    # SCSI command, no block device -- it only reports what the GCC and UFSHCI windows
    # read as, which is the question a bring-up has to answer first.
    source = ROOT / 'scripts/nabu-ufs-register-probe.cpp'
    if not source.is_file():
        raise SystemExit('Missing nabu UFS register probe source')
out = ROOT / 'build' / {'ArmVirtPlatform': 'armvirt-platform', 'ArmDTPlatform': 'armdt-platform', 'ArmCpu': 'armcpu', 'NativeAES': 'native-aes',
                        'NativeVirtioBlock': 'native-virtio-block', 'NativeRamBlock': 'native-ram-block',
                        'NativeMobileDisplay': 'native-mobile-display', 'NativeVirtioConsole': 'native-virtio-console',
                        'NativeLegacyDisplay': 'native-legacy-display', 'NativeGOPPresenter': 'native-gop-presenter', 'NativeOfflineGPU':'native-offline-gpu','NativeOfflineAccelerator':'native-offline-accelerator','NativeIOGPUProviderProbe':'native-original-provider', 'NativeUfs':'native-ufs', 'NativeHidInput':'native-hid-input', 'NativeKeyStoreEvents':'native-keystore-events', 'NativeAdreno':'native-adreno'}[component]
if args.verified_root:
    out = ROOT / ('build/native-virtio-block-verified-fault' if args.negative_verified_block else 'build/native-virtio-block-verified')
    if args.verified_root_bundle:
        out = ROOT / 'build/native-virtio-block-verified-bundle'
out.mkdir(parents=True, exist_ok=True)
if args.negative_aes_kat:
    if component != 'NativeAES':
        parser.error('The own-source KAT control requires NativeAES')
    out = ROOT / 'build/native-aes-kat-negative'
    out.mkdir(parents=True, exist_ok=True)
    text = source.read_text()
    marker = '0x76,0x49,0xab,0xac'
    if text.count(marker) != 1:
        raise SystemExit('The exact own-source NIST answer was not uniquely identified')
    (out / 'OriginalAESABI.h').write_bytes(source.with_name('OriginalAESABI.h').read_bytes())
    source = out / 'NativeAES.cpp'
    source.write_text(text.replace(marker, '0x77,0x49,0xab,0xac'))
destination = out / (component + '.o')
arguments = record['arguments']
command = []
index = 0
while index < len(arguments):
    value = arguments[index]
    if value == record['file']:
        command.append(str(source))
    elif value == '-o':
        command.extend(['-o', str(destination)])
        index += 1
    elif value == '-Xclang' and arguments[index + 1].startswith('-W'):
        index += 1
    elif not value.startswith('-W'):
        command.append(value)
    index += 1
# Xcode 26.0.1's clang added -Wunnecessary-virtual-specifier, which fires on the exported xnu
# C++ headers this driver includes (OSSymbol.h declares a virtual inside a final class). The
# -Werror below turned it into a build failure before the kernel could link.
command.extend(['-Wall', '-Wextra', '-Werror', '-Wno-unused-parameter',
                '-Wno-c99-designator', '-Wno-reorder-init-list', '-Wno-deprecated-enum-enum-conversion',
                '-Wno-unnecessary-virtual-specifier', '-Wno-suggest-override',
                '-Wno-suggest-destructor-override',
                '-I', str(ROOT / '.cache/xnu-work/osfmk')])
if component in ('NativeVirtioBlock', 'NativeRamBlock', 'NativeUfs'):
    command += ['-I', str(ROOT / 'build/storage-abi/include')]
    if args.verified_root:
        command += ['-I', str(ROOT / 'kits/VerifiedRoot/include'), '-DNATIVE_VERIFIED_BLOCK=1']
    if args.negative_verified_block:
        command += ['-DNATIVE_VERIFIED_BLOCK_INJECT_FAULT=1']
    if args.verified_root_bundle:
        command += ['-DNATIVE_VERIFIED_BLOCK_MULTI_POLICY=1']
if component == 'NativeUfs':
    # The ufsReadWindow template always accesses the verified view member, so the
    # verified-block personality is structural. nabu supplies the VerifiedRoot symbols
    # through a stub archive with policy_count=0 (device is never published until a
    # real signed policy exists); sheng supplies them through build-verified-root-probe.
    #
    # --unverified is the bring-up alternative UniXNU-uke uses: compile the transport with the
    # policy bundle switched off so the running controller can be adopted before any signed
    # policy exists. Without it the build requires kits/VerifiedRoot, which this tree lacks.
    # verified_root.h and VerifiedBlockPolicy.h are included unconditionally at the top of
    # NativeUfs.cpp; only the bodies are behind #if NATIVE_VERIFIED_BLOCK. The include path is
    # therefore required in both modes -- the switch decides whether the policy path compiles in.
    command += ['-I', str(ROOT / 'kits/VerifiedRoot/include'),
                '-I', str(ROOT / 'drivers/NativeVirtioBlock'), '-mgeneral-regs-only']
    if args.unverified:
        command += ['-DNATIVE_VERIFIED_BLOCK=0']
    else:
        command += ['-DNATIVE_VERIFIED_BLOCK=1', '-DNATIVE_VERIFIED_BLOCK_MULTI_POLICY=1']
if component=='NativeOfflineGPU':
    command += ['-I',str(ROOT/'drivers/NativeVirtioConsole')]
if component in ('NativeLegacyDisplay','NativeHidInput'):
    command += ['-I', str(out)]
if component == 'NativeAdreno':
    command += ['-I', str(ROOT / 'kits/ArmSmmu4K'), '-I', str(ROOT / 'kits/AdrenoPM4'),
                '-I', str(ROOT / 'kits/sheng'), '-I', str(ROOT / 'kits/AdrenoFirmware'),
                '-I', str(ROOT / 'build/sheng-gmu')]
(out / 'compile-command.json').write_text(json.dumps(command, indent=2) + '\n')
result = subprocess.run(command, cwd=record['directory'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
(out / 'compile.log').write_text(result.stdout)
if result.returncode:
    # The tail alone is useless under -Weverything: the last 3500 characters are warnings, and the
    # errors that mattered sit above them. Quote the error lines first.
    _lines = result.stdout.split('\n')
    _picked = []
    for _index, _line in enumerate(_lines):
        if 'error:' in _line:
            _picked.extend(_lines[max(0, _index - 1):min(len(_lines), _index + 3)])
    if _picked:
        import sys as _sys
        print('\n'.join(_picked[-6000:]), file=_sys.stderr)
    raise SystemExit(result.stdout[-3500:])
data = destination.read_bytes()
magic, cpu, subtype, kind, count, size = struct.unpack_from('<6I', data)
if (magic, cpu, subtype, kind) != (0xfeedfacf, 0x100000c, 0, 1):
    raise SystemExit('Unexpected platform object architecture')
offset = 32
deployment = None
for _ in range(count):
    cmd, length = struct.unpack_from('<II', data, offset)
    if cmd == 0x32:
        deployment = struct.unpack_from('<II', data, offset + 8)
    offset += length
if deployment != (2, 0x110000):
    raise SystemExit(f'Unexpected platform deployment {deployment}')
archive = out / ('lib' + component + '.a')
archive.unlink(missing_ok=True)
subprocess.run(['xcrun', 'ar', 'rcs', archive, destination], check=True)
print(f'{component}: -Werror build and actual ARM64/iOS 17 object audit passed')
