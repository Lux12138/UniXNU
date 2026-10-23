#!/usr/bin/env python3
"""Name the service the IOMedia walk dies on.

waitForService(IOMedia+UUID) never returns while waitForService(IOResources+IOBSD) does, with a
valid 5-second timeout, so the block is inside the walk -- before the deadline can fire, meaning the
IOCatalogue lock is held and no timeout is observed either.

instanceMatch runs once per service being examined. Writing the service name to a fixed row on every
call leaves the last one examined on screen when the walk stops; a counter row shows how far it got.

Rows (below the console band, alongside the existing status rows):
  1560  walk=N            how many services examined
  1580  the name of the service being examined right now
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


# the marker prototypes. IOService.cpp has no IOKitDebug.h include -- its first include is
# <IOKit/system.h> at line 29 -- which is why the earlier anchor missed and the probes
# failed to compile with "use of undeclared identifier 'nabu_mark_text'".
after('#include <IOKit/system.h>',
      '\nextern "C" void nabu_mark_text(const char *s, unsigned int y);\n'
      'extern "C" void nabu_mark_num(const char *label, unsigned long v, unsigned int y);\n',
      'declare nabu_mark_*')

# entry into instanceMatch: count this service and name it
after('\tdone = 0;\n\tdo{',
      '\t{\n'
      '\t\tstatic unsigned long walkN = 0;\n'
      '\t\tnabu_mark_num("walk", ++walkN, 1560);\n'
      '\t\tnabu_mark_text(service->getName(), 1580);\n'
      '\t}\n',
      'walk counter + service name')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))
for line in text.split('\n'):
    if 'nabu_mark' in line:
        print('  %s' % line.strip()[:84])
