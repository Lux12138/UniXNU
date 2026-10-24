#!/usr/bin/env python3
"""Paint AMFI state and kill reason at the initproc SIGKILL guard."""
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

ANCHOR = '\tif (signum == SIGKILL && p == initproc) {'
INJECT = (
    '\tif (signum == SIGKILL && p == initproc) {\n'
    '\t\t{\n'
    '\t\t\tint __amfi = 0;\n'
    '\t\t\tboolean_t __got = PE_parse_boot_argn("amfi_get_out_of_my_way", &__amfi, sizeof(__amfi));\n'
    '\t\t\tnabu_mark_num ("AM", (unsigned long)(__got ? (unsigned long)__amfi : 999), 1500);\n'
    '\t\t\tnabu_mark_num ("CS", (unsigned long)(proc_getcsflags(p) & CS_KILLED), 1580);\n'
    '\t\t\tnabu_mark_num ("NS", signal_reason ? (unsigned long)signal_reason->osr_namespace : 888, 1660);\n'
    '\t\t\tnabu_mark_num ("CD", signal_reason ? (unsigned long)signal_reason->osr_code : 777, 1740);\n'
    '\t\t}'
)

if 'nabu_mark_num ("AM"' in src:
    report.append('  skip   AM present')
elif ANCHOR in src:
    src = src.replace(ANCHOR, INJECT, 1)
    report.append('  insert AM/CS/NS/CD')
else:
    report.append('  MISS   initproc guard anchor')

io.open(SRC, 'w', encoding='utf-8', newline='').write(src)
print('\n'.join(report))
