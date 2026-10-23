#!/usr/bin/env python3
"""Report the timeout diagnostics on fixed screen rows instead of through kprintf.

nabu_mark_num(label, value, y) writes a label and a value at row y and overwrites that row every
call, so it never scrolls and never collides with the console's own output. kprintf shares the frame
buffer with the marker squares and produced the overlapping mess.

Rows 40..43 are far below the marker strip, which occupies the early rows.
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/iokit/bsddev/IOKitBSDInit.cpp'
text = io.open(SRC, encoding='utf-8').read()
original = len(text)
report = []


def replace_once(old, new, label):
    global text
    if new in text and old not in text:
        report.append('  skip   %s' % label)
        return
    if old not in text:
        report.append('  MISS   %s' % label)
        return
    text = text.replace(old, new, 1)
    report.append('  change %s' % label)


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


# the declaration has to be visible from this C++ file
after('#include <IOKit/IOKitDebug.h>',
      '\nextern "C" void nabu_mark_num(const char *label, unsigned long v, unsigned int y);\n'
      'extern "C" void nabu_mark_text(const char *s, unsigned int y);\n',
      'nabu_mark declarations')

# replace the two gated kprintf probes with fixed-row writes
old_set = '''		{ static int n = 0; if (n++ < 3) kprintf("NABU: t set addr=%p sec=%u nsec=%u\\n",
		    (void *)&t, (unsigned)t.tv_sec, (unsigned)t.tv_nsec); }'''
new_set = '''		nabu_mark_num("t.sec after set", (unsigned long)t.tv_sec, 40);'''
replace_once(old_set, new_set, 't.sec after set -> row 40')

old_call = '''		{ static int n = 0; if (n++ < 3) kprintf("NABU: t before call addr=%p sec=%u nsec=%u\\n",
		    (void *)&t, (unsigned)t.tv_sec, (unsigned)t.tv_nsec); }'''
new_call = '''		nabu_mark_num("t.sec before call", (unsigned long)t.tv_sec, 41);
		nabu_mark_num("ROOTDEVICETIMEOUT", (unsigned long)ROOTDEVICETIMEOUT, 42);
		nabu_mark_num("t addr", (unsigned long)(uintptr_t)&t, 43);'''
replace_once(old_call, new_call, 't.sec before call -> rows 41..43')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))
for line in text.split('\n'):
    if 'nabu_mark_num' in line or 'nabu_mark_text' in line:
        print('  %s' % line.strip()[:90])
