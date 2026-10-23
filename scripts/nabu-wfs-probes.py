#!/usr/bin/env python3
"""Probe waitForService itself: IOFindBSDRoot reaches it but never reaches
waitForMatchingService, so the gap is inside this wrapper.

    IOService::waitForService(matching, timeout)
    {
        if (timeout) {
            timeoutNS = timeout->tv_sec;      <- read of the caller's mach_timespec_t
            timeoutNS *= kSecondScale;
            timeoutNS += timeout->tv_nsec;
        } else {
            timeoutNS = UINT64_MAX;
        }
        result = waitForMatchingService(matching, timeoutNS);   <- never reached

Also forces ROOTDEVICETIMEOUT down, which the earlier script failed to do.
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/iokit/Kernel/IOService.cpp'
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


# --- inside waitForService -----------------------------------------------------
sig = ('IOService::waitForService( OSDictionary * matching,\n'
       '    mach_timespec_t * timeout )\n{\n')
after(sig,
      '\tkprintf("NABU: wfs enter timeoutptr=%p\\n", (void *)timeout);',
      'wfs enter')

before('\tif (timeout) {\n\t\ttimeoutNS = timeout->tv_sec;',
       '\tkprintf("NABU: wfs about to read tv_sec\\n");\n',
       'wfs before tv_sec')

after('\t\ttimeoutNS += timeout->tv_nsec;',
      '\tkprintf("NABU: wfs timeoutNS=%llu\\n", (unsigned long long)timeoutNS);',
      'wfs timeoutNS')

before('\tresult = waitForMatchingService(matching, timeoutNS);',
       '\tkprintf("NABU: wfs calling waitForMatchingService\\n");\n',
       'wfs before wfms')

after('\tresult = waitForMatchingService(matching, timeoutNS);',
      '\tkprintf("NABU: wfs result=%p\\n", (void *)result);',
      'wfs result')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))
for line in text.split('\n'):
    if 'NABU: wfs ' in line:
        print('  %s' % line.strip()[:82])
