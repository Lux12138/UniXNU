#!/usr/bin/env python3
"""Read vm_page_free_count right after pmap_startup.

pmap.c already shows fp=0 at initialize_ram_ranges. This second point answers whether the counter is
still sane immediately after the page structures are built, or whether pmap_startup itself corrupts it.
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/osfmk/vm/vm_resident.c'
src = io.open(SRC, encoding='utf-8').read()
report = []

if SRC.endswith('vm_resident.c'):
    DECL = '\n/* for the post-startup probe */\nextern void nabu_mark_text(const char *s, unsigned int y);\n'
    # A probe retired: it read 1,207,626, which is sane. Moving to the end of vm_page_bootstrap.
    ANCHOR = '\tkernel_debug_string_early("vm_page_bootstrap complete");'
    INJECT = (
        '\t{\n'
        '\t\tchar __b[96];\n'
        '\t\tsnprintf(__b, sizeof(__b), "B fp=%u w=%u",\n'
        '\t\t    vm_page_free_count, vm_page_wire_count);\n'
        '\t\tpanic ("%s", __b);\n'
        '\t}\n'
        '\tkernel_debug_string_early("vm_page_bootstrap complete");'
    )
    if True:  # B probe retired after reading 1,207,621 / wire 37,563
        pass
    elif False:
        report.append('  skip   bootstrap-end probe already present')
    elif ANCHOR in src:
        src = src.replace(ANCHOR, INJECT, 1)
        report.append('  insert bootstrap-end probe')
    else:
        report.append('  MISS   bootstrap-end anchor')
    io.open(SRC, 'w', encoding='utf-8', newline='').write(src)

elif SRC.endswith('pmap.c'):
    # pmap.c probe retired: it fires inside pmap_startup and blocks the post-startup probe.
    # Its data is recorded -- fp=0 mm=4864 pg=122436.
    report.append('  skip   pmap probe retired')
else:
    report.append('  skip   unknown file')

print('\n'.join(report))
