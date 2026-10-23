#!/usr/bin/env python3
"""Probe the four blocking points inside waitForMatchingServiceWithToken.

waitForService just forwards to this function, so a 5-second timeout should make it return NULL.
It does not return at all, so it is stuck at one of:

  6564  LOCKWRITENOTIFY()                       taking the catalogue write lock
  6570  copyExistingServices(...)               walking every registered service
  6575  setNotification(gIOMatchedNotification) registering for future matches
  6581  absolute_timeout / thread wait          the timeout itself
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


# entry to the function (only the one with the checkInToken signature)
after('IOService::waitForMatchingServiceWithToken( OSDictionary * matching,\n    uint64_t timeout,\n    IOUserServerCheckInToken * checkInToken)\n{',
      '\tkprintf("NABU: wfms enter timeout=%llu\\n", (unsigned long long)timeout);',
      'wfms enter')

before('\tLOCKWRITENOTIFY();',
       '\tkprintf("NABU: wfms before LOCKWRITENOTIFY\\n");\n',
       'before LOCKWRITENOTIFY')

after('\tLOCKWRITENOTIFY();',
      '\tkprintf("NABU: wfms got write lock\\n");',
      'got write lock')

before('\t\tresult = (IOService *) copyExistingServices( matching,',
       '\t\tkprintf("NABU: wfms copyExistingServices enter\\n");\n',
       'copyExistingServices enter')

after('\t\tresult = (IOService *) copyExistingServices( matching,\n\t\t    kIOServiceMatchedState, kIONotifyOnce );',
      '\t\tkprintf("NABU: wfms copyExistingServices=%p\\n", (void *)result);',
      'copyExistingServices result')

before('\t\tnotify = IOService::setNotification( gIOMatchedNotification, matching,',
       '\t\tkprintf("NABU: wfms setNotification enter\\n");\n',
       'setNotification enter')

after('\t\t    &result, priority );',
      '\t\tkprintf("NABU: wfms notify=%p\\n", (void *)notify);',
      'setNotification result')

before('\t\tif (UINT64_MAX != timeout) {',
       '\t\tkprintf("NABU: wfms arming timeout\\n");\n',
       'arming timeout')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))
for line in text.split('\n'):
    if 'NABU: wfms' in line:
        print('  %s' % line.strip()[:80])
