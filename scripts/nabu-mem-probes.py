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

# also probe pmap.c when that file is passed
if SRC.endswith('pmap.c'):
    pm = io.open(SRC, encoding='utf-8').read()
    rep2 = []
    R2 = 'avail_page_count = atop(end - first);'
    if 'NABU-RANGE' in pm:
        rep2.append('  skip   range panic already present')
    elif R2 in pm:
        pm = pm.replace(R2,
            'avail_page_count = atop(end - first);\n'
            '\tpanic ("NABU-RANGE end=%llx first=%llx pages=%u",\n'
            '\t    (unsigned long long)end, (unsigned long long)first, avail_page_count);', 1)
        io.open(SRC, 'w', encoding='utf-8', newline='').write(pm)
        rep2.append('  insert range panic')
    else:
        rep2.append('  MISS   avail_page_count anchor')
    print('\n'.join(rep2))
