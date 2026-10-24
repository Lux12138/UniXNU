#!/usr/bin/env python3
"""Record the creator of any EXEC-namespace os_reason."""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/bsd/kern/sys_reason.c'
if not SRC.endswith('sys_reason.c'):
    sys.exit(0)

src = io.open(SRC, encoding='utf-8').read()
report = []

DECL = ('\n/* status-strip markers */\n'
        'extern void nabu_mark_num(const char *label, unsigned long v, unsigned int y);\n')
if 'extern void nabu_mark_num' not in src:
    hdr = '#include <sys/reason.h>'
    if hdr in src:
        src = src.replace(hdr, hdr + DECL, 1)
    else:
        src = DECL + src
    report.append('  insert declaration')

ANCHOR = '\treturn new_reason;'
INJECT = (
    '\tif (osr_namespace == 9) {\n'
    '\t\tnabu_mark_num ("RN", (unsigned long)osr_code, 2100);\n'
    '\t\tnabu_mark_num ("RA", (unsigned long)(uintptr_t)__builtin_return_address(0) & 0xffffffff, 2180);\n'
    '\t}\n'
    '\treturn new_reason;'
)

if 'nabu_mark_num ("RN"' in src:
    report.append('  skip   RN present')
elif ANCHOR in src:
    src = src.replace(ANCHOR, INJECT, 1)
    report.append('  insert RN/RA')
else:
    report.append('  MISS   return anchor')

io.open(SRC, 'w', encoding='utf-8', newline='').write(src)
print('\n'.join(report))
