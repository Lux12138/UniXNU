#!/usr/bin/env python3
"""Skip non-IOMedia services when the match table asks for IOMedia.

Evidence from the screen:

  walk 1
  IODTNVRAM
  options

The walk examined exactly one service -- the IODTNVRAM node named 'options' -- and stopped. instanceMatch
calls service->matchInternal(table, ...) for each service, and matchInternal reads every property the
table names. The root-matching table names UUID under IOPropertyMatch, so every service visited gets
getProperty("UUID") called on it. IODTNVRAM resolves properties through NVRAM, which is not ready
here, so it blocks -- holding the IOCatalogue write lock, which is why the 5-second timeout in
waitForService never fires either.

The table itself already says IOProviderClass = IOMedia, so services of any other class are
irrelevant. Skipping them keeps the walk moving and avoids touching NVRAM at all.

This is a real fix, not a probe: with it, waitForService(IOMedia+UUID) should return.
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/iokit/Kernel/IOService.cpp'
text = io.open(SRC, encoding='utf-8').read()
original = len(text)
report = []


def replace(old, new, label):
    global text
    if new in text and old not in text:
        report.append('  skip   %s' % label)
        return
    if old not in text:
        report.append('  MISS   %s' % label)
        return
    text = text.replace(old, new, 1)
    report.append('  change %s' % label)


# insert the class filter right after the locals, before the match loop
old_head = '''	done = 0;
	do{'''

new_head = '''	done = 0;

	// Only services of the class the table asks for are relevant. Without this, a table carrying
	// IOPropertyMatch walks every service in the system and reads the named properties on each --
	// including IODTNVRAM nodes, whose property lookups go through NVRAM and block while NVRAM is
	// not ready. That block holds the IOCatalogue lock, so waitForService's timeout never fires.
	{
		OSString * wantClass = OSDynamicCast(OSString, table->getObject(gIOProviderClassKey));
		if (wantClass && !service->metaCast(wantClass->getCStringNoCopy())) {
			return false;
		}
	}

	do{'''

replace(old_head, new_head, 'class filter before the match loop')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))

# show the region
lines = io.open(SRC, encoding='utf-8').read().split('\n')
for i, l in enumerate(lines):
    if 'wantClass' in l:
        for n in range(max(0, i - 6), min(len(lines), i + 10)):
            print('%5d %s' % (n + 1, lines[n].rstrip()[:96]))
        break
