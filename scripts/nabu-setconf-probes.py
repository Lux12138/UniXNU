#!/usr/bin/env python3
"""Probe setconf() itself, and the mount loop around it.

If IOFindBSDRoot's own entry probe does not print, the question is whether setconf() is reached at
all -- so instrument the caller too. Idempotent, anchor-based.
"""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/bsd/kern/bsd_init.c'
text = io.open(SRC, encoding='utf-8').read()
original = len(text)
report = []


def after(anchor, addition, label):
    global text
    if addition in text:
        report.append('  skip   %s' % label)
        return
    # insert on a fresh line: a probe glued to the anchor's last token compiles but is unreadable
    if not anchor.endswith('\n'):
        anchor = anchor + '\n'
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


# --- inside setconf() -----------------------------------------------------------
# entry: right after its opening brace and the two locals
after('setconf(void)\n{\n\tu_int32_t       flags;\n\tkern_return_t   err;\n',
      '\tkprintf("NABU: setconf enter\\n");\n',
      'setconf enter')

# just before the call
before('\terr = IOFindBSDRoot(rootdevice, sizeof(rootdevice), &rootdev, &flags);',
       '\tkprintf("NABU: setconf calling IOFindBSDRoot\\n");\n',
       'setconf before IOFindBSDRoot')

# right after it returns
after('\terr = IOFindBSDRoot(rootdevice, sizeof(rootdevice), &rootdev, &flags);',
      '\tkprintf("NABU: setconf IOFindBSDRoot=%d\\n", err);',
      'setconf after IOFindBSDRoot')

# --- the mount loop around setconf ----------------------------------------------
before('\t\tbsd_init_kprintf("calling setconf\\n");',
       '\t\tkprintf("NABU: mount loop iteration\\n");\n',
       'mount loop iteration')

before('\t\tbsd_init_kprintf("vfs_mountroot\\n");',
       '\t\tkprintf("NABU: after setconf\\n");\n',
       'after setconf')

io.open(SRC, 'w', encoding='utf-8', newline='').write(text)
print('\n'.join(report))
print()
print('bytes: %d -> %d' % (original, len(text)))
for line in text.split('\n'):
    if 'NABU:' in line:
        print('  %s' % line.strip()[:86])
