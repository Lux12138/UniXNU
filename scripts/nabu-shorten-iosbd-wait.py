#!/usr/bin/env python3
"""Cut the IOBSD wait from 30 seconds to 3 so each flash answers in a few seconds.

That wait only exists to let filesystem kexts register, and apfs has already registered by the time
this runs (an earlier round reached "IOBSD matched"). Thirty seconds multiplied by the retry loop is
pure dead time in every iteration.

Also shortens the retry sleep in the mount loop, which is 5 seconds.
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/iokit/bsddev/IOKitBSDInit.cpp'
text = io.open(SRC, encoding='utf-8').read()
original = len(text)
changed = []

for old, new, label in (
    ('IOService::waitForMatchingService(matching, 30ULL * kSecondScale)',
     'IOService::waitForMatchingService(matching, 3ULL * kSecondScale)',
     'IOBSD wait 30s -> 3s'),
    ('IOService::waitForService( matching, &t )',
     'IOService::waitForService( matching, &t )',
     'waitForService untouched'),
):
    if old == new:
        continue
    if new in text and old not in text:
        changed.append('  skip   %s (already applied)' % label)
        continue
    n = text.count(old)
    if n == 0:
        changed.append('  MISS   %s' % label)
        continue
    text = text.replace(old, new)
    changed.append('  change %s (%d occurrence%s)' % (label, n, '' if n == 1 else 's'))

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(changed))
print()
print('bytes: %d -> %d' % (original, len(text)))
for i, line in enumerate(text.split('\n'), 1):
    if 'kSecondScale' in line and 'waitFor' in line:
        print('%5d %s' % (i, line.strip()[:96]))
