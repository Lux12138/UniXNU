#!/usr/bin/env python3
"""Probe the three blocking points after root-matching: waitQuiet, waitForService, and the exit.

The boot prints "root-matching Present" and stops. Between there and the successful
"return kIOReturnSuccess" at the iofrootx label, IOFindBSDRoot calls waitQuiet() and then
waitForService() with a timeout. IOLog may not reach this console, so use kprintf.
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


# the didRam block, so we know whether a RAMDisk device was created
before('\tif (!didRam) {',
       '\tkprintf("NABU: didRam=%d\\n", didRam);\n',
       'didRam check')

before('\t\t\t\t(void)mdevadd(-1, ml_static_ptovirt(ramdParms[0]) >> 12, (unsigned int) (ramdParms[1] >> 12), 0);',
       '\t\t\t\tkprintf("NABU: mdevadd ramdisk base=%lx size=%lx\\n", (unsigned long)ramdParms[0], (unsigned long)ramdParms[1]);\n',
       'mdevadd')

after('\t\t\t\t(void)mdevadd(-1, ml_static_ptovirt(ramdParms[0]) >> 12, (unsigned int) (ramdParms[1] >> 12), 0);',
      '\t\t\t\tkprintf("NABU: mdevadd returned\\n");',
      'mdevadd returned')

# past the ramdisk and rd=md0 branch
before('\tif ((!matching) && rdBootVar[0]) {',
       '\tkprintf("NABU: past ramdisk, matching=%s rd=%s\\n",\n'
       '\t    matching ? "set" : "null", rdBootVar[0] ? rdBootVar : "none");\n',
       'past ramdisk')

# the matching search
before('\tif (!matching) {',
       '\tkprintf("NABU: about to build default IOMedia match\\n");\n',
       'build default match')

before('\t\tIOLog( "Waiting for matching to complete\\n" );',
       '\t\tkprintf("NABU: waiting for matching to complete\\n");\n',
       'waiting for matching')

before('\t\tIOService::getPlatform()->waitQuiet();',
       '\t\tkprintf("NABU: waitQuiet enter\\n");\n',
       'waitQuiet enter')

after('\t\tIOService::getPlatform()->waitQuiet();',
      '\t\tkprintf("NABU: waitQuiet done\\n");',
      'waitQuiet done')

before('\t\tservice = IOService::waitForService( matching, &t );',
       '\t\tkprintf("NABU: waitForService enter\\n");\n',
       'waitForService enter')

after('\t\tservice = IOService::waitForService( matching, &t );',
      '\t\tkprintf("NABU: waitForService=%p\\n", (void *)service);',
      'waitForService result')

before('\t\t\tIOLog( "Still waiting for root device\\n" );',
       '\t\t\tkprintf("NABU: still waiting for root device\\n");\n',
       'still waiting')

# the exits
before('iofrootx:',
       '\tkprintf("NABU: reached iofrootx\\n");\n',
       'iofrootx')

before('\tIOService::setRootMedia(service);',
       '\tkprintf("NABU: setRootMedia enter\\n");\n',
       'setRootMedia enter')

after('\tIOService::setRootMedia(service);',
      '\tkprintf("NABU: setRootMedia done\\n");',
      'setRootMedia done')

before('\treturn kIOReturnSuccess;\n}',
       '\tkprintf("NABU: IOFindBSDRoot success, rootName=%s\\n", rootName);\n',
       'IOFindBSDRoot success')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))
missing = [line for line in report if 'MISS' in line]
if missing:
    print()
    print('MISSES:')
    for line in missing:
        print(line)
