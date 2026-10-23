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
      '\tnabu_mark_text("IOFindBSDRoot entered", 2420);\n'
      # Clock probe: every timed path here fails identically and all read mach_absolute_time().
      # tA = low 32 bits of the first read (0 = clock reads zero);
      # tD = t2 - t1 (0 = clock does not advance). The spin uses yield only, so it cannot hang.
      '\t{\n'
      '\t\tuint64_t t1 = mach_absolute_time ();\n'
      '\t\tfor (unsigned spin = 0; spin < 200000; ++spin) { __asm__ volatile ("yield" ::: "memory"); }\n'
      '\t\tuint64_t t2 = mach_absolute_time ();\n'
      '\t\t/* tA is known non-zero (3967735401); only the delta matters. */\n'
      '\t\tnabu_mark_text (t2 > t1 ? "clock:advances" : "clock:STUCK", 1780);\n'
      '\t\t/* literal strings: the numeric path was silent even though tD is in the kernel */\n'
      '\t}\n',
      'row 1520 entry')


after('mach_timespec_t     t;',
      '\n\t/* Initialise the timeout: this variable was read uninitialised and passed straight to\n'
      '\t * waitForService below, so the call could never time out. 3s makes the result observable. */\n'
      '\tt.tv_sec = 3;\n'
      '\tt.tv_nsec = 0;\n',
      'row timeout init')

# 2. before and after the wait
before('\t\tservice = IOService::waitForService( matching, &t );',
       '\t\tnabu_mark_text("A call wfs", 2500);\n',
       'row 1550 A before call')

after('\t\tservice = IOService::waitForService( matching, &t );',
      '\t\tnabu_mark_num("B returned", (unsigned long)(service != NULL), 2500);',
      'row 1550 B after call')



# 5. enumerate IOMedia: count + first UUID
COUNT_MEDIA = (
    '\t\t/* How many IOMedia exist, and what UUID does the first carry? Distinguishes "no media at all"\n'
    '\t\t * (missing IOBlockStorageDriver) from "media exist with another UUID" (manifest mismatch). */\n'
    '\t\t{\n'
    '\t\t\tOSDictionary *__mm = IOService::serviceMatching ("IOMedia");\n'
    '\t\t\tOSIterator *__mi = __mm ? IOService::getMatchingServices (__mm) : NULL;\n'
    '\t\t\tunsigned __nmedia = 0;\n'
    '\t\t\tchar __uuid[16];\n'
    '\t\t\tfor (int __i = 0; __i < 15; ++__i) { __uuid[__i] = 0; }\n'
    '\t\t\tif (__mi) {\n'
    '\t\t\t\tIOService *__us;\n'
    '\t\t\t\twhile ((__us = OSDynamicCast (IOService, __mi->getNextObject ())) != NULL && __nmedia < 16) {\n'
    '\t\t\t\t\tif (__nmedia == 0) {\n'
    '\t\t\t\t\t\tOSString *__uu = OSDynamicCast (OSString, __us->getProperty ("UUID"));\n'
    '\t\t\t\t\t\tif (__uu) {\n'
    '\t\t\t\t\t\t\tconst char *__cs = __uu->getCStringNoCopy ();\n'
    '\t\t\t\t\t\t\tfor (int __i = 0; __i < 12 && __cs[__i]; ++__i) { __uuid[__i] = __cs[__i]; }\n'
    '\t\t\t\t\t\t} else {\n'
    '\t\t\t\t\t\t\tconst char *__nk = "no-UUID-prop";\n'
    '\t\t\t\t\t\t\tfor (int __i = 0; __nk[__i]; ++__i) { __uuid[__i] = __nk[__i]; }\n'
    '\t\t\t\t\t\t}\n'
    '\t\t\t\t\t}\n'
    '\t\t\t\t\t++__nmedia;\n'
    '\t\t\t\t}\n'
    '\t\t\t\t__mi->release ();\n'
    '\t\t\t}\n'
    '\t\t\tif (__mm) { __mm->release (); }\n'
    '\t\t\tif (__nmedia == 0) {\n'
    '\t\t\t\tconst char *__nk = "none";\n'
    '\t\t\t\tfor (int __i = 0; __nk[__i]; ++__i) { __uuid[__i] = __nk[__i]; }\n'
    '\t\t\t}\n'
    '\t\t\tnabu_mark_num ("iomedia", (unsigned long)__nmedia, 1780);\n'
    '\t\t\tnabu_mark_text (__uuid, 1860);\n'
    '\t\t}\n'
)

# 4. replace the sleeping wait with a busy poll
# waitForService parks the thread and relies on a timer-interrupt wakeup; sleeping does not work here
# yet (5s timeout never fires), while busy waits do. Ask the catalogue directly instead.
SLEEPY = '\t\tservice = IOService::waitForService( matching, &t );'
BUSY = (
    '\t\t/* NABU: busy poll instead of waitForService -- sleeping does not come back yet. */\n'
    '\t\tservice = NULL;\n'
    '\t\t{\n'
    '\t\t\t/* Count passes: mach_absolute_time units are not nanoseconds here, so a\n'
    '\\t\\t\\t * +5000000000ULL deadline ran for thousands of seconds. 200 is bounded. */\n'
    '\t\t\tfor (unsigned __try = 0; __try < 200 && !service; ++__try) {\n'
    '\t\t\t\tOSIterator *__it = IOService::getMatchingServices (matching);\n'
    '\t\t\t\tif (__it) {\n'
    '\t\t\t\t\tservice = OSDynamicCast (IOService, __it->getNextObject ());\n'
    '\t\t\t\t\t__it->release ();\n'
    '\t\t\t\t}\n'
    '\t\t\t\tif (service) break;\n'
    '\t\t\t\tfor (unsigned __s = 0; __s < 20000; ++__s) { __asm__ volatile ("yield" ::: "memory"); }\n'
    '\t\t\t}\n'
    '\t\t}\n'
)
# substitution, not insertion: the original call must disappear
if SLEEPY in text:
    text = text.replace(SLEEPY, BUSY, 1)
    report.append('  replace row busy poll instead of waitForService')
else:
    report.append('  MISS   row busy poll instead of waitForService')


after('\t\tnabu_mark_num("B returned", (unsigned long)(service != NULL), 2500);',
      COUNT_MEDIA,
      'row iomedia enumeration')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))
for line in text.split('\n'):
    if 'nabu_mark' in line:
        print('  %s' % line.strip()[:84])
