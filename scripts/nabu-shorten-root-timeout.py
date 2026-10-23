#!/usr/bin/env python3
"""Shorten ROOTDEVICETIMEOUT so each flash gives an answer in 20 seconds instead of 120.

A timeout is not a failure here: waitForService returns NULL, the loop prints "still waiting for
root device", sleeps 5s and retries. So a short timeout costs nothing and makes the failure visible
immediately.
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/iokit/bsddev/IOKitBSDInit.cpp'
text = io.open(SRC, encoding='utf-8').read()

if 'NABU: ROOTDEVICETIMEOUT shortened' in text:
    print('already shortened')
    sys.exit(0)

old = '#define ROOTDEVICETIMEOUT'
count = text.count(old)
if count == 0:
    print('MISS: ROOTDEVICETIMEOUT not found')
    sys.exit(1)

# annotate each definition and force the value to 5
lines = text.split('\n')
changed = 0
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped.startswith('#define ROOTDEVICETIMEOUT'):
        lines[i] = '#define ROOTDEVICETIMEOUT       5   /* NABU: ROOTDEVICETIMEOUT shortened */'
        changed += 1

text = '\n'.join(lines)
io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('redefined %d occurrence(s) to 5 seconds' % changed)
for line in text.split('\n'):
    if 'ROOTDEVICETIMEOUT' in line and 'define' in line:
        print('  %s' % line.strip())
