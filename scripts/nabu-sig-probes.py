#!/usr/bin/env python3
"""Paint AMFI state and kill reason at the initproc SIGKILL guard."""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/bsd/kern/kern_sig.c'
if not (SRC.endswith('kern_sig.c') or SRC.endswith('kern_exec.c')):
    sys.exit(0)

src = io.open(SRC, encoding='utf-8').read()
report = []

DECL = ('\n/* status-strip markers */\n'
        '#include <pexpert/pexpert.h>\n'
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
    '\t\t\t/* 2500/2580 are the last two rows clear of the console (which paints to 1780) and of the\n'
    '\t\t\t   sleh probes at 1560..2420. Pack two values per row. */\n'
    '\t\t\t/* AMx already answered: AMFI parsed = 1, CS_KILLED = 0. The remaining\n'
    '\t\t\t   question is which exit reason killed launchd, so paint namespace/code. */\n'
    '\t\t\t(void)__got; (void)__amfi;\n'
    '\t\t\tnabu_mark_num ("SIG", signal_reason\n'
    '\t\t\t    ? (unsigned long)(signal_reason->osr_namespace * 100000\n'
    '\t\t\t        + (signal_reason->osr_code % 100000))\n'
    '\t\t\t    : 7777777, 2500);\n'
    '\t\t}'
)

if 'nabu_mark_num ("AM"' in src:
    report.append('  skip   AM present')
elif ANCHOR in src:
    src = src.replace(ANCHOR, INJECT, 1)
    report.append('  insert AM/CS/NS/CD')
else:
    report.append('  MISS   initproc guard anchor')

# paint the reason at the delivery point
SIG2 = 'psignal_with_reason(p, SIGKILL, signature_failure_reason);'
if True:  # SN/SC/SU answered: 9 / 8 / 0. LU needs their rows.
    report.append('  skip   SN retired (rows freed for LU/EM)')
elif SIG2 in src:
    src = src.replace(SIG2,
        'nabu_mark_num ("SN", signature_failure_reason'
        ' ? (unsigned long)signature_failure_reason->osr_namespace : 7777, 2100);\n'
        '\t\t\tnabu_mark_num ("SC", signature_failure_reason'
        ' ? (unsigned long)signature_failure_reason->osr_code : 7777, 2180);\n'
        '\t\t\tnabu_mark_num ("SU", (unsigned long)require_success, 2260);\n'
        '\t\t\t' + SIG2, 1)
    report.append('  insert SN/SC/SU at the signature SIGKILL')
else:
    report.append('  MISS   signature SIGKILL anchor')

io.open(SRC, 'w', encoding='utf-8', newline='').write(src)
print('\n'.join(report))
