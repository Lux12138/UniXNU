#!/usr/bin/env python3
"""Keep one status line, on a row the console never reaches.

Console occupies roughly y=240..1450 on this panel (1600 tall). The status rows were written at
1440..1500, right inside that band, so they were overwritten or stacked with console text.

Everything that has already been established is dropped: the whole bsd_autoconf..inittodr run
succeeds, IOFindBSDRoot is entered, IOBSD matches, root-matching is present, the RAMDisk is created,
and execution stops inside waitForService. None of that needs reporting again.

What remains is a single letter at y=1520 that changes as execution moves:

    A  waitForService entered
    B  waitForService returned (and whether it returned non-NULL)
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/iokit/bsddev/IOKitBSDInit.cpp'
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


# move the entry marker far below the console band
replace('	nabu_mark_text("IOFindBSDRoot", 1440);',
        '	nabu_mark_text("IOFindBSDRoot entered", 1520);',
        'row 1520 entry')

# the timeout write and the post-call write move to 1550 and gain a visible letter
replace('''		nabu_mark_num("wfs sec", (unsigned long)t.tv_sec, 1470);''',
        '''		nabu_mark_text("A call wfs", 1550);''',
        'row 1550 A before call')

replace('''		nabu_mark_num("wfs returned", (unsigned long)(service != NULL), 1470);''',
        '''		nabu_mark_num("B returned", (unsigned long)(service != NULL), 1550);''',
        'row 1550 B after call')

# the IOMedia walk marker, also below the console band
replace('		nabu_mark_text("walking IOMedia", 1500);',
        '		nabu_mark_text("walking IOMedia", 1580);',
        'row 1580 walk')

replace('		nabu_mark_num("copyExisting", (unsigned long)(result != NULL), 1500);',
        '		nabu_mark_num("walk result", (unsigned long)(result != NULL), 1580);',
        'row 1580 walk result')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))
for line in text.split('\n'):
    if 'nabu_mark' in line:
        print('  %s' % line.strip()[:80])
