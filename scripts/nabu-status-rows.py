#!/usr/bin/env python3
"""Insert the status rows by anchor.

Corrections after inspecting the file:

  * IOKitBSDInit.cpp already includes nabu_early_mark.h at line 29, so no separate declaration is
    needed -- that is why the declaration anchor missed.
  * copyExistingServices is not in this file at all; it lives in IOService.cpp. The walk marker is
    therefore dropped from this file rather than pointed at a nonexistent anchor.

Rows sit below the console band (console covers roughly y=240..1450 of 1600):

  1520  IOFindBSDRoot entered
  1550  A call wfs  ->  B returned N
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/iokit/bsddev/IOKitBSDInit.cpp'
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


def before(anchor, addition, label):
    global text
    if addition.strip() and addition.strip() in text:
        report.append('  skip   %s' % label)
        return
    idx = text.find(anchor)
    if idx < 0:
        report.append('  MISS   %s' % label)
        return
    text = text[:idx] + addition + text[idx:]
    report.append('  insert %s' % label)


# 1. IOFindBSDRoot entry
after('IOFindBSDRoot( char * rootName, unsigned int rootNameSize,\n    dev_t * root, u_int32_t * oflags )\n{',
      '\tnabu_mark_text("IOFindBSDRoot entered", 1520);\n',
      'row 1520 entry')

# 2. before and after the wait
before('\t\tservice = IOService::waitForService( matching, &t );',
       '\t\tnabu_mark_text("A call wfs", 1550);\n',
       'row 1550 A before call')

after('\t\tservice = IOService::waitForService( matching, &t );',
      '\t\tnabu_mark_num("B returned", (unsigned long)(service != NULL), 1550);',
      'row 1550 B after call')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))
for line in text.split('\n'):
    if 'nabu_mark' in line:
        print('  %s' % line.strip()[:84])
