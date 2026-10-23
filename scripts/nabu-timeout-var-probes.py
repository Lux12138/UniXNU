#!/usr/bin/env python3
"""Find out who zeroes IOFindBSDRoot's mach_timespec_t.

ROOTDEVICETIMEOUT is 5, and IOFindBSDRoot does t.tv_sec = ROOTDEVICETIMEOUT, yet waitForService
computes timeoutNS = 0 -- so t is overwritten between the assignment and the call, or the pointer
is wrong. Print the address and the value on both sides of the call.
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


# right after the assignment
# Three-shot guards: the mount loop retries hundreds of times a second now that the timeout
# computes to zero, and ungated prints cover the screen in overlapping copies.
after('\t\tt.tv_sec = ROOTDEVICETIMEOUT;\n\t\tt.tv_nsec = 0;',
      '\t\t{ static int n = 0; if (n++ < 3) kprintf("NABU: t set addr=%p sec=%u nsec=%u\\n",\n'
      '\t\t    (void *)&t, (unsigned)t.tv_sec, (unsigned)t.tv_nsec); }',
      't after assignment')

before('\t\tservice = IOService::waitForService( matching, &t );',
       '\t\t{ static int n = 0; if (n++ < 3) kprintf("NABU: t before call addr=%p sec=%u nsec=%u\\n",\n'
       '\t\t    (void *)&t, (unsigned)t.tv_sec, (unsigned)t.tv_nsec); }\n',
       't before call')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))
for line in text.split('\n'):
    if 'NABU: t ' in line:
        print('  %s' % line.strip()[:80])
