#!/usr/bin/env python3
"""Extend the working RANGE panic in pmap.c with max_mem and vm_page_free_count.

The RANGE panic built and printed; the vm_resident one could not be made to recompile. So stay in pmap.c
and add the two values that decide whether freepg's 91 million is even related to this code path.

    end - first         = 4.67 GiB   (measured, matches owned_memory_size)
    avail_page_count    =   122,436  (measured, 10x below (end-first)/4096)
    max_mem             = ?          (expected 4864 MiB)
    vm_page_free_count  = ?          (expected <= 122,436; freepg reported 91,199,441)
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/osfmk/arm/pmap/pmap.c'
if not SRC.endswith('pmap.c'):
    sys.exit(0)

src = io.open(SRC, encoding='utf-8').read()
report = []

DECL = '\n/* for the range panic */\nextern unsigned int vm_page_free_count;\nextern uint64_t max_mem;\n'
if 'extern unsigned int vm_page_free_count' not in src:
    hdr = '#include <vm/vm_page.h>'
    if hdr in src:
        src = src.replace(hdr, hdr + DECL, 1)
    else:
        src = DECL + src
    report.append('  insert declarations')

ANCHOR = 'avail_page_count = atop(end - first);'
INJECT = (
    'avail_page_count = atop(end - first);\n'
    '\t{\n'
    '\t\tchar __b[192];\n'
    '\t\tsnprintf(__b, sizeof(__b), "V2 fp=%u mm=%llu pg=%u",\n'
    '\t\t    vm_page_free_count, (unsigned long long)(max_mem >> 20), avail_page_count);\n'
    '\t\tpanic ("%s", __b);\n'
    '\t}'
)

if 'freepg=%u' in src:
    report.append('  skip   already extended')
elif ANCHOR in src:
    src = src.replace(ANCHOR, INJECT, 1)
    report.append('  insert extended range panic')
else:
    report.append('  MISS   anchor')

io.open(SRC, 'w', encoding='utf-8', newline='').write(src)
print('\n'.join(report))
