#!/usr/bin/env python3
"""The only status reporter: fixed rows at the bottom of the panel.

Every other probe in this area has been disabled. They all kprintf into the frame buffer the console
owns, and with the mount loop retrying quickly the lines stack until nothing is readable. What this
script writes goes to rows the console never redraws, overwriting the same row each call.

Rows
  1440  where execution is in IOFindBSDRoot
  1470  the timeout value being handed to waitForService
  1500  result of copyExistingServices over IOMedia
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


after('#include <IOKit/IOKitDebug.h>',
      '\nextern "C" void nabu_mark_num(const char *label, unsigned long v, unsigned int y);\n'
      'extern "C" void nabu_mark_text(const char *s, unsigned int y);\n',
      'declare nabu_mark_num')

# entry to IOFindBSDRoot
after('\tkprintf("NABU: IOFindBSDRoot enter\\n");',
      '\tnabu_mark_text("IOFindBSDRoot", 1440);',
      'row 1440 entry')

# the timeout just before the call, and after the call returns
old_call = '''		matching->retain();
		kprintf("NABU: waitForService enter\\n");
		service = IOService::waitForService( matching, &t );'''
new_call = '''		matching->retain();
		nabu_mark_num("wfs sec", (unsigned long)t.tv_sec, 1470);
		service = IOService::waitForService( matching, &t );
		nabu_mark_num("wfs returned", (unsigned long)(service != NULL), 1470);'''
replace(old_call, new_call, 'row 1470 around the call')

# the IOMedia walk
old_walk = '''		result = (IOService *) copyExistingServices( matching,
		    kIOServiceMatchedState, kIONotifyOnce );'''
new_walk = '''		nabu_mark_text("walking IOMedia", 1500);
		result = (IOService *) copyExistingServices( matching,
		    kIOServiceMatchedState, kIONotifyOnce );
		nabu_mark_num("copyExisting", (unsigned long)(result != NULL), 1500);'''
replace(old_walk, new_walk, 'row 1500 walk state')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))
for line in text.split('\n'):
    if 'nabu_mark' in line:
        print('  %s' % line.strip()[:84])
