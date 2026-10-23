#!/usr/bin/env python3
"""Add exec-time probes showing user_stack and the copyout result."""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/bsd/kern/kern_exec.c'
src = io.open(SRC, encoding='utf-8').read()
report = []

# declare the helpers: kern_exec.c cannot see nabu_early_mark.h
DECL = ('\n/* status-strip markers from nabu_early_mark.c */\n'
        'extern void nabu_mark_num(const char *label, unsigned long v, unsigned int y);\n'
        'extern void nabu_mark_text(const char *s, unsigned int y);\n')
if 'extern void nabu_mark_num' not in src:
    hdr = '#include <sys/imgact.h>'
    if hdr in src:
        src = src.replace(hdr, hdr + DECL, 1)
        report.append('  insert marker declarations')
    else:
        src = DECL + src
        report.append('  prepend marker declarations')

anchor = '\t\tap = p->user_stack;' 
if 'nabu_mark_num ("ustk"' in src:
    report.append('  skip   exec probes already present')
elif anchor in src:
    src = src.replace(anchor,
        anchor + '\n'
        '\t\tnabu_mark_num ("ustk", (unsigned long)ap, 2260);', 1)
    report.append('  insert ustk row')
else:
    report.append('  MISS   user_stack anchor')

call = '\t\terror = exec_copyout_strings(imgp, &ap);'
if 'nabu_mark_num ("cpo"' in src:
    report.append('  skip   copyout result already present')
elif call in src:
    src = src.replace(call,
        call + '\n'
        '\t\tnabu_mark_num ("cpo", (unsigned long)error, 2340);', 1)
    report.append('  insert cpo row')
else:
    report.append('  MISS   copyout call anchor')


# dynlinker branch: the second copyout into the user stack. The fault's FAR sits at user_stack - 0x90,
# which is exactly where thread_adjuserstack + copyoutptr land when launchd is dynamically linked.
DL_ANCHOR = 'if (load_result.dynlinker || load_result.is_rosetta) {'
if 'nabu_mark_num ("dnk"' in src:
    report.append('  skip   dnk already present')
elif DL_ANCHOR in src:
    src = src.replace(DL_ANCHOR,
        DL_ANCHOR + '\n'
        '\t\tnabu_mark_num ("dnk", (unsigned long)(load_result.dynlinker != 0), 2100);', 1)
    report.append('  insert dnk row')
else:
    report.append('  MISS   dynlinker anchor')

CP2 = 'error = copyoutptr(load_result.mach_header, ap, new_ptr_size);'
if 'nabu_mark_num ("cp2"' in src:
    report.append('  skip   cp2 already present')
elif CP2 in src:
    idx = src.find(CP2)
    line_end = src.find('\n', idx)
    src = src[:line_end + 1] + '\t\tnabu_mark_num ("cp2", (unsigned long)error, 2180);\n' + src[line_end + 1:]
    report.append('  insert cp2 row')
else:
    report.append('  MISS   copyoutptr anchor')

io.open(SRC, 'w', encoding='utf-8', newline='').write(src)
print('\n'.join(report))
