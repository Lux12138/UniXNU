#!/usr/bin/env python3
"""Paint kr inside proc_process_signature."""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/bsd/kern/kern_exec.c'
if not SRC.endswith('kern_exec.c'):
    sys.exit(0)

src = io.open(SRC, encoding='utf-8').read()
report = []

DECL = ('\n/* status-strip markers */\n'
        'extern void nabu_mark_num(const char *label, unsigned long v, unsigned int y);\n')
if 'extern void nabu_mark_num' not in src:
    hdr = '#include <sys/imgact.h>'
    if hdr in src:
        src = src.replace(hdr, hdr + DECL, 1)
    else:
        src = DECL + src
    report.append('  insert declaration')

ANCHOR = '\tkern_return_t kr = machine_task_process_signature(proc_get_task_raw(p), proc_platform(p), proc_sdk(p), &error_msg);'
INJECT = (ANCHOR + '\n'
          '\tnabu_mark_num ("KR", (unsigned long)kr, 2340);\n'
          '\tnabu_mark_num ("EM", (unsigned long)(error_msg != NULL), 2420);')

if 'nabu_mark_num ("KR"' in src:
    report.append('  skip   KR present')
elif ANCHOR in src:
    src = src.replace(ANCHOR, INJECT, 1)
    report.append('  insert KR/EM in proc_process_signature')
else:
    report.append('  MISS   machine_task_process_signature anchor')

io.open(SRC, 'w', encoding='utf-8', newline='').write(src)
print('\n'.join(report))
