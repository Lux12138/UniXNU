#!/usr/bin/env python3
"""Re-add the wfms probes, but only print when the timeout is finite.

Every other caller of waitForService passes NULL, which becomes UINT64_MAX, and those calls fire
constantly -- they filled the screen and buried the one call we care about. IOFindBSDRoot is the
only caller with a real timeout (5s after the shortening), so gating on
"timeout != UINT64_MAX" isolates it.
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


# entry: only announce finite timeouts, that is IOFindBSDRoot
after('IOService::waitForMatchingServiceWithToken( OSDictionary * matching,\n    uint64_t timeout,\n    IOUserServerCheckInToken * checkInToken)\n{',
      '\tif (UINT64_MAX != timeout) {\n'
      '\t\tkprintf("NABU: ROOT wfms enter timeout=%llu\\n", (unsigned long long)timeout);\n'
      '\t}',
      'ROOT wfms enter')

# gate each later probe on the same condition, one line each
# LOCKWRITENOTIFY() appears several times in this file; only this sequence is unique to
# waitForMatchingServiceWithToken, where 'timeout' is actually in scope.
lock_anchor = '\tLOCKWRITENOTIFY();\n\tdo{\n\t\tif (cancelArgs.canceled) {'
before(lock_anchor,
       '\tif (UINT64_MAX != timeout) kprintf("NABU: ROOT before lock\\n");\n',
       'ROOT before lock')
after(lock_anchor,
      '\tif (UINT64_MAX != timeout) kprintf("NABU: ROOT got lock\\n");',
      'ROOT got lock')

before('\t\tresult = (IOService *) copyExistingServices( matching,',
       '\t\tif (UINT64_MAX != timeout) kprintf("NABU: ROOT copyExisting enter\\n");\n',
       'ROOT copyExisting enter')

after('\t\tresult = (IOService *) copyExistingServices( matching,\n\t\t    kIOServiceMatchedState, kIONotifyOnce );',
      '\t\tif (UINT64_MAX != timeout) kprintf("NABU: ROOT copyExisting=%p\\n", (void *)result);',
      'ROOT copyExisting result')

before('\t\tnotify = IOService::setNotification( gIOMatchedNotification, matching,',
       '\t\tif (UINT64_MAX != timeout) kprintf("NABU: ROOT setNotification enter\\n");\n',
       'ROOT setNotification enter')

after('\t\t    &result, priority );',
      '\t\tif (UINT64_MAX != timeout) kprintf("NABU: ROOT notify=%p\\n", (void *)notify);',
      'ROOT notify result')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))
for line in text.split('\n'):
    if 'NABU: ROOT' in line:
        print('  %s' % line.strip()[:86])
