#!/usr/bin/env python3
"""Paint labelupdateerror at the tail of mac_cred_label_update_execve."""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/security/mac_vfs.c'
if not SRC.endswith('mac_vfs.c'):
    sys.exit(0)

src = io.open(SRC, encoding='utf-8').read()
report = []

DECL = ('\n/* status-strip markers */\n'
        'extern void nabu_mark_num(const char *label, unsigned long v, unsigned int y);\n')
if 'extern void nabu_mark_num' not in src:
    hdr = '#include <security/mac_internal.h>'
    if hdr in src:
        src = src.replace(hdr, hdr + DECL, 1)
    else:
        src = DECL + src
    report.append('  insert declaration')

ANCHOR = '\t*labelupdateerror = error;'
INJECT = ('\tnabu_mark_num ("LU", (unsigned long)(unsigned int)error, 2100);\n' + ANCHOR)

if 'nabu_mark_num ("LU"' in src:
    report.append('  skip   LU present')
elif ANCHOR in src:
    src = src.replace(ANCHOR, INJECT, 1)
    report.append('  insert LU at 2500')
else:
    report.append('  MISS   labelupdateerror anchor')

io.open(SRC, 'w', encoding='utf-8', newline='').write(src)
print('\n'.join(report))
