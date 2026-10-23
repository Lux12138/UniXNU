#!/usr/bin/env python3
"""Put the marker squares back, without any kprintf.

They were removed along with the four probe inserters, because NABU_MARK(n) and the kprintf lines
came from the same insertion code. The squares are the boot progress display and are worth keeping;
the kprintf lines are what made the screen unreadable.

This inserts only NABU_MARK(n) calls. nabu-clean-probes.py strips lines containing 'NABU:' (with a
colon) and leaves NABU_MARK alone, so the two do not interfere.

Mark numbers:
  61/62  around kminit
  65     bsd_autoconf returned
  66     dtrace_postinit done
  67     loopattach
  68     ether_family_init
  69     net_init_run
  70     inittodr
  71     vfs_mountroot enter
  72     waitForService entered      <- where the boot actually stops
  73     waitForService returned
"""
import io
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
W = '/root/src/UniXNU/out/nabu/tree/.cache/xnu-work'

report = []


def add(path, anchors):
    """anchors: list of (anchor, addition, label, where) with where in {'after','before'}"""
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
        if where == 'after':
            end = idx + len(a)
        else:
            end = idx
        text = text[:end] + addition + text[end:]
        changed += 1
    io.open(path, 'w', encoding='utf-8', newline='').write(text)
    report.append('  %s: %d mark(s) inserted' % (os.path.basename(path), changed))


TAB = '\t'

add(W + '/bsd/kern/bsd_init.c', [
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

add(W + '/iokit/bsddev/IOKitBSDInit.cpp', [
    ('\t\tservice = IOService::waitForService( matching, &t );',
     '\t\tNABU_MARK(73);\n', 'waitForService returned', 'after'),
])

print('\n'.join(report))
