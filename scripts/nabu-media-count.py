#!/usr/bin/env python3
"""Count IOMedia instances, and stop bsd_boot_to_recovery from waiting forever.

keys == 1 showed the walk belongs to bsd_boot_to_recovery's serviceMatching("IODTNVRAM"), which
passes no timeout and therefore waits forever. That is why the boot appears frozen after the root
device lookup has already failed -- the kernel is trying to record why it failed and gets stuck.

Two changes:

  * that wait gets a 2 second timeout, so the failure path can finish and the boot can report what
    happens next instead of hanging silently;
  * IOFindBSDRoot counts IOMedia instances right before it asks for one, so the screen says whether
    the UFS block device ever became an IOMedia at all. Zero means NativeUfs never published it,
    which moves the problem into the storage driver rather than anywhere in IOKit.
"""
import io

SRC = '/root/src/UniXNU/out/nabu/tree/.cache/xnu-work/iokit/bsddev/IOKitBSDInit.cpp'
text = io.open(SRC, encoding='utf-8').read()
original = len(text)
report = []


def replace(old, new, label):
    global text
    if new in text and old not in text:
        report.append('  skip    %s' % label)
        return
    if old not in text:
        report.append('  MISS    %s' % label)
        return
    text = text.replace(old, new, 1)
    report.append('  change  %s' % label)


# 1. the failure path must not block forever
replace(
    '''nvram = OSDynamicCast(IODTNVRAM, IOService::waitForService(
			    IOService::serviceMatching("IODTNVRAM")));''',
    '''/* Bounded: this runs on the boot-failure path, and with no timeout the kernel hung here
		 * forever, hiding whatever came next. */
		{
			mach_timespec_t nvt;
			nvt.tv_sec = 2;
			nvt.tv_nsec = 0;
			nvram = OSDynamicCast(IODTNVRAM, IOService::waitForService(
			    IOService::serviceMatching("IODTNVRAM"), &nvt));
		}''',
    'bsd_boot_to_recovery IODTNVRAM wait bounded to 2s')

# 2. count IOMedia instances just before asking for one
replace(
    '''	do {
		t.tv_sec = ROOTDEVICETIMEOUT;''',
    '''	/* How many IOMedia instances exist at all? Zero means the UFS block device never published
	 * one, so no amount of matching will find a root volume. */
	{
		OSDictionary * nmm = IOService::serviceMatching("IOMedia");
		unsigned long nmedia = 0;
		if (nmm) {
			OSIterator * nit = IOService::getMatchingServices(nmm);
			if (nit) {
				while (nit->getNextObject()) {
					nmedia++;
				}
				nit->release();
			}
			nmm->release();
		}
		nabu_mark_num("IOMedia", nmedia, 1850);
	}

	do {
		t.tv_sec = ROOTDEVICETIMEOUT;''',
    'IOMedia instance count before the lookup')

# 3. the iterator type needs its header
if 'libkern/c++/OSIterator.h' not in text:
    replace('#include <libkern/c++/OSAllocation.h>',
            '#include <libkern/c++/OSAllocation.h>\n#include <libkern/c++/OSIterator.h>',
            'include OSIterator.h')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))

lines = io.open(SRC, encoding='utf-8').read().split('\n')
for i, l in enumerate(lines):
    if 'nmedia' in l:
        for n in range(max(0, i - 3), min(len(lines), i + 18)):
            print('%5d %s' % (n + 1, lines[n].rstrip()[:92]))
        break
