#!/usr/bin/env python3
"""Insert probes around IOFindBSDRoot's wait and its per-attempt path.

Same text-anchor approach as the bsd_init inserter: idempotent, reports what it did.
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
    index = text.find(anchor)
    if index < 0:
        report.append('  MISS   %s' % label)
        return
    end = index + len(anchor)
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


# entry to IOFindBSDRoot
after('{\n\tmach_timespec_t     t;',
      '\tkprintf("NABU: IOFindBSDRoot enter\\n");\n',
      'IOFindBSDRoot enter')

# the IOBSD wait
before('\tmatching = IOService::serviceMatching(gIOResourcesKey);',
       '\tkprintf("NABU: IOBSD wait start\\n");\n',
       'IOBSD wait start')

before('\tif ((service = IOService::waitForMatchingService(matching, 30ULL * kSecondScale))) {',
       '\tkprintf("NABU: IOBSD waitForMatchingService\\n");\n',
       'IOBSD waitForMatchingService')

after('\t\tOSSafeReleaseNULL(service);',
      '\t\tkprintf("NABU: IOBSD matched\\n");',
      'IOBSD matched')

after('\t\tIOLog("!BSD\\n");',
      '\t\tkprintf("NABU: IOBSD wait timed out\\n");',
      'IOBSD timed out')

# after the wait, before reading root-matching
before('\tif ((regEntry = IORegistryEntry::fromPath( "/chosen", gIODTPlane ))) {',
       '\tkprintf("NABU: IOBSD read /chosen\\n");\n',
       'read /chosen')

# the root-matching branch
after('\t\t\tdata = OSDynamicCast(OSData, regEntry->getProperty( "root-matching" ));',
      '\t\t\tkprintf("NABU: root-matching %s\\n", data ? "present" : "absent");',
      'root-matching presence')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))
for line in text.split('\n'):
    if 'NABU:' in line:
        print('  %s' % line.strip()[:80])
