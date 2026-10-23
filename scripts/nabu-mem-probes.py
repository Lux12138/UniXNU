#!/usr/bin/env python3
"""Dump the physical range through panic, with the numbers pre-formatted into a string.

The panic hook in debug.c paints its format string and then treats each vararg as a char*:

    nabu_mark_text(str, 1000);
    if (_a0 != 0) nabu_mark_text(_a0, 1040);

so integers paint nothing -- observed directly: "NABU-RANGE end=%llx first=%llx pages=%u" appeared with
its placeholders intact. snprintf into a buffer and panic("%s", buf) makes _a0 a real string.

initialize_ram_ranges() is the one place where first_avail, avail_end and avail_page_count all exist,
and avail_page_count = atop(end - first) is what pmap_free_pages() hands to vm_page_bootstrap -- the
number that ends up as freepg (91,199,441 / 44 / 43 across three boots, i.e. computed, not random).
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/osfmk/arm/pmap/pmap.c'
if not SRC.endswith('pmap.c'):
    print('  skip   not pmap.c')
    sys.exit(0)

src = io.open(SRC, encoding='utf-8').read()
report = []

ANCHOR = 'avail_page_count = atop(end - first);'
INJECT = (
    'avail_page_count = atop(end - first);\n'
    '\t{\n'
    '\t\tchar __b[128];\n'
    '\t\tsnprintf(__b, sizeof(__b), "NABU-RANGE end=%llx first=%llx pages=%u",\n'
    '\t\t    (unsigned long long)end, (unsigned long long)first, avail_page_count);\n'
    '\t\tpanic ("%s", __b);\n'
    '\t}'
)

if 'NABU-RANGE' in src:
    report.append('  skip   range panic already present')
elif ANCHOR in src:
    src = src.replace(ANCHOR, INJECT, 1)
    report.append('  insert formatted range panic')
else:
    report.append('  MISS   avail_page_count anchor')

io.open(SRC, 'w', encoding='utf-8', newline='').write(src)
print('\n'.join(report))
