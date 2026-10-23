#!/usr/bin/env python3
"""Make every probe print at most three times.

The mount loop retries as fast as it can because the timeout is 0, so each pass reprints the whole
probe set and the frame buffer ends up with dozens of copies stacked on the same lines -- the screen
becomes unreadable. Three prints of each line is enough to see the sequence once.
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/iokit/bsddev/IOKitBSDInit.cpp'
text = io.open(SRC, encoding='utf-8').read()
original = len(text)

guard = '''{
\tstatic int n = 0;
\tif (n++ < 3) kprintf("NABU: t set addr=%p sec=%u nsec=%u\\n",
\t    (void *)&t, (unsigned)t.tv_sec, (unsigned)t.tv_nsec);
}'''

old_set = '''		kprintf("NABU: t set addr=%p sec=%u nsec=%u\\n",
		    (void *)&t, (unsigned)t.tv_sec, (unsigned)t.tv_nsec);'''

count = 0
if old_set in text:
    text = text.replace(old_set, '\t\t' + guard.replace('\n', '\n\t\t'))
    count += 1
    print('  gated  t set')

old_before = '''		kprintf("NABU: t before call addr=%p sec=%u nsec=%u\\n",
		    (void *)&t, (unsigned)t.tv_sec, (unsigned)t.tv_nsec);
'''

guard_before = '''		{
			static int n = 0;
			if (n++ < 3) kprintf("NABU: t before call addr=%p sec=%u nsec=%u\\n",
			    (void *)&t, (unsigned)t.tv_sec, (unsigned)t.tv_nsec);
		}
'''

if old_before in text:
    text = text.replace(old_before, guard_before)
    count += 1
    print('  gated  t before call')

if count == 0:
    print('  nothing to gate (already gated, or the probes are gone)')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print()
print('bytes: %d -> %d' % (original, len(text)))
