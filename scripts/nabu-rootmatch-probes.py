#!/usr/bin/env python3
"""Probe what happens after root-matching is read: the waitForMatchingService that resolves it.

The boot now prints "root-matching Present" and then stops, so the next question is whether the
UUID match resolves, times out, or returns something unexpected.
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/iokit/bsddev/IOKitBSDInit.cpp'
text = io.open(SRC, encoding='utf-8').read()
original = len(text)
report = []


def after(anchor, addition, label):
    global text
    if addition in text:
        report.append('  skip   %s' % label)
        return
    a = anchor if anchor.endswith('\n') else anchor + '\n'
    index = text.find(a)
    if index < 0:
        report.append('  MISS   %s' % label)
        return
    end = index + len(a)
    text = text[:end] + addition + text[end:]
    report.append('  insert %s' % label)


def before(anchor, addition, label):
    global text
    if addition in text:
        report.append('  skip   %s' % label)
        return
    index = text.find(anchor)
    if index < 0:
        report.append('  MISS   %s' % label)
        return
    text = text[:index] + addition + text[index:]
    report.append('  insert %s' % label)


# after the root-matching dictionary is adopted
after('\t\t\t\t\tcontinue;',
      '\t\t\t\t\tkprintf("NABU: root-matching adopted, searching IOMedia\\n");',
      'root-matching adopted')

# the search that follows the /chosen block -- find the next waitForMatchingService use
lines = text.split('\n')
first_wait = '\tif ((service = IOService::waitForMatchingService(matching, 30ULL * kSecondScale))) {'
count = text.count(first_wait)
report.append('  info   waitForMatchingService occurrences: %d' % count)

# instrument every wait call site
marker = '\tif ((service = IOService::waitForMatchingService('
inserted = 0
while True:
    idx = text.find(marker, 0 if inserted == 0 else text.find('NABU: wait#%d' % inserted) + 1)
    if idx < 0:
        break
    inserted += 1
    label = '\tkprintf("NABU: wait#%d for %s\\n", "a service");\n' % inserted
    if 'NABU: wait#%d' % inserted in text:
        report.append('  skip   wait#%d' % inserted)
        continue
    text = text[:idx] + '\tkprintf("NABU: wait#%d\\n");\n' % inserted + text[idx:]
    report.append('  insert wait#%d' % inserted)
    if inserted > 6:
        break

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))
for line in text.split('\n'):
    if 'NABU: root-matching adopted' in line or 'NABU: wait#' in line:
        print('  %s' % line.strip()[:80])
