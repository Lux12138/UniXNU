#!/usr/bin/env python3
"""Strip every leftover NABU probe line, then write the status rows.

Earlier inserter versions left kprintf probes behind in these files, and unixnu tree's reset does not
clear them, so disabling the inserters was not enough -- the stale lines kept compiling and kept
flooding the console. Removing them here makes this script the single authority over what these two
files print.
"""
import io
import re
import sys

report = []


def strip_probe_lines(path, label):
    try:
        text = io.open(path, encoding='utf-8').read()
    except IOError:
        report.append('  missing %s' % label)
        return
    lines = text.split('\n')
    kept = [line for line in lines if 'NABU:' not in line]
    removed = len(lines) - len(kept)
    if removed:
        io.open(path, 'w', encoding='utf-8', newline='').write('\n'.join(kept))
    report.append('  %s: removed %d NABU line(s)' % (label, removed))


W = '/root/src/UniXNU/out/nabu/tree/.cache/xnu-work'
strip_probe_lines(W + '/iokit/Kernel/IOService.cpp', 'IOService.cpp')
strip_probe_lines(W + '/iokit/bsddev/IOKitBSDInit.cpp', 'IOKitBSDInit.cpp')
strip_probe_lines(W + '/bsd/kern/bsd_init.c', 'bsd_init.c')

print('\n'.join(report))
