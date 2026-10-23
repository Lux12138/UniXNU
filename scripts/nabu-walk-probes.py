#!/usr/bin/env python3
"""Report which IOMedia service the walk stops on.

waitForService(IOMedia+UUID) never returns while waitForService(IOResources+IOBSD) does, and the
timeout is a valid 5 seconds, so the block is inside the walk -- before the timeout can fire, which
also means it holds IOCatalogue and no deadline is observed.

copyExistingServices is the walk. Print the name of the service currently being examined on one
fixed row; the last name left on screen is the one it died on. One row, overwritten each time, so it
cannot flood the console.
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/iokit/Kernel/IOService.cpp'
text = io.open(SRC, encoding='utf-8').read()
original = len(text)
report = []


def after(anchor, addition, label):
    global text
    if addition.strip() and addition.strip() in text:
        report.append('  skip   %s' % label)
        return
    a = anchor if anchor.endswith('\n') else anchor + '\n'
    idx = text.find(a)
    if idx < 0:
        report.append('  MISS   %s' % label)
        return
    end = idx + len(a)
    text = text[:end] + addition + text[end:]
    report.append('  insert %s' % label)


# the file needs the marker prototypes
if 'nabu_mark_text' not in text.split('IOService::waitForService')[0]:
    after('#include <IOKit/IOKitDebug.h>',
          '\nextern "C" void nabu_mark_text(const char *s, unsigned int y);\n',
          'declare nabu_mark_text')

# inside the walk: mark each service as it is examined
after('\tresult = (IOService *) copyExistingServices( matching,',
      '\tnabu_mark_text("copyExisting entered", 1600);',
      'row 1600 walk entered')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))
for line in text.split('\n'):
    if 'nabu_mark' in line:
        print('  %s' % line.strip()[:84])

print()
print('=== where copyExistingServices itself lives ===')
for i, line in enumerate(text.split('\n'), 1):
    if 'copyExistingServices(' in line and ('OSIterator' in line or '::' in line or 'static' in line):
        print('%5d %s' % (i, line.strip()[:96]))
