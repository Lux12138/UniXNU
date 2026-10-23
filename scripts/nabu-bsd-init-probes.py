#!/usr/bin/env python3
"""Insert the bsd_init probes by text replacement instead of a unified diff.

A unified diff has to guess line numbers and reproduce context byte for byte; every miss here cost
a build round. This inserts after unique anchor strings instead, is idempotent, and reports what it
changed. build-xnu-4k-baseline.sh already writes files directly (the nabu_early_mark.h heredoc), so
patching the work tree from the script is the established pattern.
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/bsd/kern/bsd_init.c'
text = io.open(SRC, encoding='utf-8').read()
original_len = len(text)
report = []


def after(anchor, addition, label):
    """Insert addition right after the line containing anchor, once."""
    global text
    if addition in text:
        report.append('  skip   %s (already present)' % label)
        return
    index = text.find(anchor)
    if index < 0:
        report.append('  MISS   %s (anchor not found)' % label)
        return
    end = index + len(anchor)
    text = text[:end] + addition + text[end:]
    report.append('  insert %s' % label)


def before(anchor, addition, label):
    global text
    if addition in text:
        report.append('  skip   %s (already present)' % label)
        return
    index = text.find(anchor)
    if index < 0:
        report.append('  MISS   %s (anchor not found)' % label)
        return
    text = text[:index] + addition + text[index:]
    report.append('  insert %s' % label)


# 1. the include for NABU_MARK
before('#include <sys/param.h>\n',
       '#include "../../osfmk/arm/nabu_early_mark.h"\n',
       'include')

# 2. around bsd_autoconf()
after('\tbsd_autoconf();\n',
      '\tNABU_MARK(65);\n'
      '\tkprintf("NABU: bsd_autoconf returned\\n");\n'
      '\tkprintf("NABU: dtrace_postinit\\n");\n',
      'bsd_autoconf returned')

after('\tdtrace_postinit();\n',
      '\tNABU_MARK(66);\n'
      '\tkprintf("NABU: dtrace done\\n");\n',
      'dtrace done')

# 3. loopattach
before('\tbsd_init_kprintf("calling loopattach\\n");\n',
       '\tNABU_MARK(67);\n'
       '\tkprintf("NABU: loopattach\\n");\n',
       'loopattach enter')
after('\tloopattach();                   /* XXX */\n',
      '\tkprintf("NABU: loopattach done\\n");\n',
      'loopattach done')

# 4. ether_family_init
before('\tbsd_init_kprintf("calling ether_family_init\\n");\n',
       '\tNABU_MARK(68);\n'
       '\tkprintf("NABU: ether_family_init\\n");\n',
       'ether enter')
after('\tether_family_init();\n',
      '\tkprintf("NABU: ether done\\n");\n',
      'ether done')

# 5. net_init_run
before('\tbsd_init_kprintf("calling net_init_run\\n");\n',
       '\tNABU_MARK(69);\n'
       '\tkprintf("NABU: net_init_run\\n");\n',
       'net enter')
after('\tnet_init_run();\n',
      '\tkprintf("NABU: net done\\n");\n',
      'net done')

# 6. inittodr
before('\tbsd_init_kprintf("calling inittodr\\n");\n',
       '\tNABU_MARK(70);\n'
       '\tkprintf("NABU: inittodr\\n");\n',
       'inittodr enter')
after('\tinittodr(0);\n',
      '\tkprintf("NABU: inittodr done\\n");\n',
      'inittodr done')

# 7. vfs_mountroot
after('\t\tbsd_init_kprintf("vfs_mountroot\\n");\n',
      '\t\tNABU_MARK(71);\n'
      '\t\tkprintf("NABU: vfs_mountroot enter\\n");\n',
      'vfs_mountroot enter')

# 8. kminit brackets
after('\tkprintf("bsd_autoconf: calling kminit\\n");\n',
      '\tkprintf("NABU: before kminit\\n");\n'
      '\tNABU_MARK(61);\n',
      'before kminit')
after('\tkminit();\n',
      '\tkprintf("NABU: after kminit\\n");\n'
      '\tNABU_MARK(62);\n',
      'after kminit')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)

print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original_len, len(text)))

count = text.count('NABU_MARK')
print('NABU_MARK occurrences: %d (expect 8)' % count)
probes = sorted(set(line.strip() for line in text.split('\n') if 'NABU: ' in line))
print('probes:')
for probe in probes:
    print('  %s' % probe)
