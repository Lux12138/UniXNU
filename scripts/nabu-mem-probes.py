#!/usr/bin/env python3
"""Paint vm_page_free_count at two points in vm_resident.c.

Measured so far (each cost one flash-and-photo round trip):
    initialize_ram_ranges      0
    after pmap_startup         1,207,626
    end of vm_page_bootstrap   1,207,621   (wire 37,563, matching)
    at execve                  91,199,441

Both earlier probes used panic, which stops the machine after the first one. Painting instead lets every
point coexist in one boot:

    1780  P0  initialize_ram_ranges     (pmap.c)
    1860  P1  after pmap_startup        (here)
    1940  P2  end of vm_page_bootstrap  (here)
    2020  P3  IOFindBSDRoot entry       (IOKitBSDInit.cpp)

Row spacing is 80px because each mark clears 61px above its baseline.
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/osfmk/vm/vm_resident.c'
src = io.open(SRC, encoding='utf-8').read()
report = []

if SRC.endswith('vm_resident.c'):
    DECL = ('\n/* for the free-page probes */\n'
            'extern void nabu_mark_num(const char *label, unsigned long v, unsigned int y);\n')
    if 'extern void nabu_mark_num' not in src:
        hdr = '#include <vm/vm_page.h>'
        if hdr in src:
            src = src.replace(hdr, hdr + DECL, 1)
        else:
            src = DECL + src
        report.append('  insert declaration')

    A1 = '\tpmap_startup(&virtual_space_start, &virtual_space_end);'
    I1 = ('\tpmap_startup(&virtual_space_start, &virtual_space_end);\n'
          '\tnabu_mark_num ("P1", vm_page_free_count, 1860);')
    if 'nabu_mark_num ("P1"' in src:
        report.append('  skip   P1 present')
    elif A1 in src:
        src = src.replace(A1, I1, 1)
        report.append('  insert P1 at 1860')
    else:
        report.append('  MISS   P1 anchor')

    A2 = '\tkernel_debug_string_early("vm_page_bootstrap complete");'
    I2 = ('\tnabu_mark_num ("P2", vm_page_free_count, 1940);\n' + A2)
    if 'nabu_mark_num ("P2"' in src:
        report.append('  skip   P2 present')
    elif A2 in src:
        src = src.replace(A2, I2, 1)
        report.append('  insert P2 at 1940')
    else:
        report.append('  MISS   P2 anchor')

    io.open(SRC, 'w', encoding='utf-8', newline='').write(src)

elif SRC.endswith('pmap.c'):
    DECL = ('\n/* for the free-page probes */\n'
            'extern void nabu_mark_num(const char *label, unsigned long v, unsigned int y);\n')
    if 'extern void nabu_mark_num' not in src:
        hdr = '#include <vm/vm_page.h>'
        if hdr in src:
            src = src.replace(hdr, hdr + DECL, 1)
        else:
            src = DECL + src
        report.append('  insert declaration')

    A0 = 'avail_page_count = atop(end - first);'
    I0 = (A0 + '\n\tnabu_mark_num ("P0", avail_page_count, 1780);')
    if 'nabu_mark_num ("P0"' in src:
        report.append('  skip   P0 present')
    elif A0 in src:
        src = src.replace(A0, I0, 1)
        report.append('  insert P0 at 1780')
    else:
        report.append('  MISS   P0 anchor')

    io.open(SRC, 'w', encoding='utf-8', newline='').write(src)

else:
    report.append('  skip   unknown file')

print('\n'.join(report))
