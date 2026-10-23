#!/usr/bin/env python3
"""Skip non-media services, accepting IOProviderClass as either OSString or OSSymbol.

The first attempt did nothing because OSUnserializeXML may store the IOProviderClass value as an
OSSymbol, so OSDynamicCast(OSString, ...) returned NULL and the guard short-circuited:

    OSString * wantClass = OSDynamicCast(OSString, table->getObject(gIOProviderClassKey));
    if (wantClass && !service->metaCast(...))   // never taken when wantClass is NULL

Now both types are accepted, and a diagnostic reports on screen whether the guard is armed, so a
silent miss cannot happen again:

    row 1310   "guard 1" when the class filter is active, "guard 0" when the table names no class

Row 1310 rather than 1660 because nabu_mark_text clears a ten-line band starting at y-12 before it
draws. With rows written in the order guard, walk, class, name, a guard at 1660 sat inside the band
that the walk row (1450, clearing 1438..1738) wipes, so it was erased immediately. At 1310 it is
above every later band.
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/iokit/Kernel/IOService.cpp'
text = io.open(SRC, encoding='utf-8').read()
original = len(text)
report = []

# remove the previous, ineffective guard if present
old_guard_start = '\t// Only services of the class the table asks for are relevant.'
if old_guard_start in text:
    start = text.index(old_guard_start)
    end_marker = '\tdo{'
    end = text.index(end_marker, start)
    text = text[:start] + text[end:]
    report.append('  removed the previous guard')

new_guard = '''	// Only services of the class the table asks for are relevant. Without this, a table carrying
	// IOPropertyMatch walks every service and reads the named properties on each -- including
	// IODTNVRAM nodes, whose property lookups go through NVRAM and block while NVRAM is not ready.
	// That block holds the IOCatalogue lock, so waitForService's timeout never fires either.
	//
	// The value may have been deserialized as OSSymbol rather than OSString, so accept both;
	// casting only to OSString silently produced NULL and disabled the whole guard.
	{
		OSObject * wantObj = table->getObject(gIOProviderClassKey);
		const char * wantName = NULL;
		if (OSString * ws = OSDynamicCast(OSString, wantObj)) {
			wantName = ws->getCStringNoCopy();
		} else if (OSSymbol * wm = OSDynamicCast(OSSymbol, wantObj)) {
			wantName = wm->getCStringNoCopy();
		}
		nabu_mark_num("guard", wantName ? 1 : 0, 1310);
		if (wantName && !service->metaCast(wantName)) {
			return false;
		}
	}'''

anchor = '\tdone = 0;\n'
idx = text.find(anchor)
if idx < 0:
    print('MISS: done = 0; not found')
    sys.exit(1)
end = idx + len(anchor)
text = text[:end] + new_guard + text[end:]
report.append('  inserted the hardened guard')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))

lines = io.open(SRC, encoding='utf-8').read().split('\n')
for i, l in enumerate(lines):
    if 'wantObj' in l:
        for n in range(max(0, i - 4), min(len(lines), i + 18)):
            print('%5d %s' % (n + 1, lines[n].rstrip()[:94]))
        break
