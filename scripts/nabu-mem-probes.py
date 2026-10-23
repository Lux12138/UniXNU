#!/usr/bin/env python3
"""Probe xmaxmem / maxmem in arm_init.c."""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/osfmk/arm/arm_init.c'
src = io.open(SRC, encoding='utf-8').read()
report = []

DECL = ('\n/* status-strip markers */\n'
        'extern void nabu_mark_num(const char *label, unsigned long v, unsigned int y);\n')
if 'extern void nabu_mark_num' not in src:
    hdr = '#include <pexpert/pexpert.h>'
    if hdr in src:
        src = src.replace(hdr, hdr + DECL, 1)
    else:
        src = DECL + src
    report.append('  insert declarations')

CALL = 'arm_vm_init(xmaxmem, args);'
if 'nabu_mark_num ("xmem"' in src:
    report.append('  skip   xmem already present')
elif CALL in src:
    src = src.replace(CALL,
        'nabu_mark_num ("xmem", (unsigned long)(xmaxmem >> 20), 1180);\n'
        '\tnabu_mark_num ("mmv", (unsigned long)maxmem, 1260);\n'
        '\t' + CALL, 1)
    report.append('  insert xmem + mmv rows')
else:
    report.append('  MISS   arm_vm_init call')

io.open(SRC, 'w', encoding='utf-8', newline='').write(src)
print('\n'.join(report))
