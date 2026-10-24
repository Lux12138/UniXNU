#!/usr/bin/env python3
"""Paint the copyio recovery lookup inside handle_kernel_abort."""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/osfmk/arm64/sleh.c'
if not SRC.endswith('sleh.c'):
    sys.exit(0)

src = io.open(SRC, encoding='utf-8').read()
report = []

ANCHOR = '\tstruct copyio_recovery_entry *recover = find_copyio_recovery_entry(state);'
INJECT = (
    ANCHOR + '\n'
    '\tnabu_mark_num ("RV", (unsigned long)recover, 1900);\n'
    '\tnabu_mark_num ("PCOF",\n'
    '\t    (unsigned long)copyio_recovery_offset(get_saved_state_pc(state)), 1980);\n'
    '\tnabu_mark_num ("TB", (unsigned long)copyio_recover_table, 2060);'
)

if 'nabu_mark_num ("RV"' in src:
    report.append('  skip   RV present')
elif ANCHOR in src:
    src = src.replace(ANCHOR, INJECT, 1)
    report.append('  insert RV/PCOF/TB')
else:
    report.append('  MISS   recover anchor')

io.open(SRC, 'w', encoding='utf-8', newline='').write(src)
print('\n'.join(report))
