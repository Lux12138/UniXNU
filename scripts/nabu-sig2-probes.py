#!/usr/bin/env python3
"""Paint the reason inside psignal_with_reason."""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/bsd/kern/kern_sig.c'
if not SRC.endswith('kern_sig.c'):
    sys.exit(0)

src = io.open(SRC, encoding='utf-8').read()
report = []

DECL = ('\n/* status-strip markers */\n'
        'extern void nabu_mark_num(const char *label, unsigned long v, unsigned int y);\n')
if 'extern void nabu_mark_num' not in src:
    hdr = '#include <sys/proc.h>'
    if hdr in src:
        src = src.replace(hdr, hdr + DECL, 1)
    else:
        src = DECL + src
    report.append('  insert declaration')

ANCHOR = 'psignal_with_reason(proc_t p, int signum, struct os_reason *signal_reason)'
INJECT = (ANCHOR + '\n'
          '{\n'
          '\tnabu_mark_num ("PN2", signal_reason'
          ' ? (unsigned long)signal_reason->osr_namespace : 7777, 2340);\n'
          '\tnabu_mark_num ("PC3", signal_reason'
          ' ? (unsigned long)signal_reason->osr_code : 7777, 2420);\n'
          '\tnabu_mark_num ("PSG", (unsigned long)signum, 2500);')

if 'nabu_mark_num ("PN2"' in src:
    report.append('  skip   PN2 present')
elif ANCHOR in src:
    # replace the signature line plus the following '{'
    import re
    idx = src.find(ANCHOR)
    brace = src.find('{', idx)
    src = src[:idx] + INJECT + src[brace + 1:]
    report.append('  insert PN2/PC3/PSG in psignal_with_reason')
else:
    report.append('  MISS   psignal_with_reason anchor')

io.open(SRC, 'w', encoding='utf-8', newline='').write(src)
print('\n'.join(report))
