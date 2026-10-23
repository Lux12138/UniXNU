#!/usr/bin/env python3
"""Bring back the marker squares, and the include they need.

Two things were lost when the probe inserters were deleted: the NABU_MARK calls and, in bsd_init.c,
the #include of nabu_early_mark.h that declares them. Without the include the file no longer
compiles:

  bsd/kern/bsd_init.c:926: error: call to undeclared function 'NABU_MARK'

nabu-clean-probes.py strips lines containing 'NABU:' (with a colon) and leaves NABU_MARK alone, so
the include and the calls coexist.

IOKitBSDInit.cpp already includes the header at line 29 and must not get a second one.
"""
import io
import os

W = '/root/src/UniXNU/out/nabu/tree/.cache/xnu-work'
report = []


def add(path, anchors):
    global report
    try:
        text = io.open(path, encoding='utf-8').read()
    except IOError:
        report.append('  missing %s' % path)
        return
    changed = 0
    for anchor, addition, label, where in anchors:
        if addition.strip() and addition.strip() in text:
            continue
        a = anchor if anchor.endswith('\n') else anchor + '\n'
        idx = text.find(a)
        if idx < 0:
            report.append('  MISS   %s' % label)
            continue
        end = idx + len(a) if where == 'after' else idx
        text = text[:end] + addition + text[end:]
        changed += 1
    io.open(path, 'w', encoding='utf-8', newline='').write(text)
    report.append('  %s: %d insertion(s)' % (os.path.basename(path), changed))


# --- bsd_init.c: the include, then the marks -----------------------------------------
add(W + '/bsd/kern/bsd_init.c', [
    ('#include <sys/param.h>',
     '#include "../../osfmk/arm/nabu_early_mark.h"\n',
     'include nabu_early_mark.h', 'before'),
    ('\tkprintf("bsd_autoconf: calling kminit\\n");', '\tNABU_MARK(61);\n', 'kminit in', 'after'),
    ('\tkminit();', '\tNABU_MARK(62);\n', 'kminit out', 'after'),
    ('\tbsd_autoconf();', '\tNABU_MARK(65);\n', 'bsd_autoconf returned', 'after'),
    ('\tdtrace_postinit();', '\tNABU_MARK(66);\n', 'dtrace done', 'after'),
    ('\tloopattach();                   /* XXX */', '\tNABU_MARK(67);\n', 'loopattach', 'after'),
    ('\tether_family_init();', '\tNABU_MARK(68);\n', 'ether', 'after'),
    ('\tnet_init_run();', '\tNABU_MARK(69);\n', 'net', 'after'),
    ('\tinittodr(0);', '\tNABU_MARK(70);\n', 'inittodr', 'after'),
    ('\t\tbsd_init_kprintf("vfs_mountroot\\n");', '\t\tNABU_MARK(71);\n', 'vfs_mountroot', 'after'),
])

# --- IOKitBSDInit.cpp: the include is already there, only the mark -----------------------
add(W + '/iokit/bsddev/IOKitBSDInit.cpp', [
    ('\t\tservice = IOService::waitForService( matching, &t );',
     '\t\tNABU_MARK(73);\n', 'waitForService returned', 'after'),
])

print('\n'.join(report))
