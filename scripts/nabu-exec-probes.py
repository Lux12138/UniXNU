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


# create_unix_stack: the numbers behind the protect range
USZ = 'if (load_result->user_stack_alloc_size > 0) {'
if 'nabu_mark_num ("usz"' in src:
    report.append('  skip   usz already present')
elif USZ in src:
    src = src.replace(USZ,
        USZ + '\n'
        '\t\tnabu_mark_num ("usz", (unsigned long)load_result->user_stack_alloc_size, 1780);', 1)
    report.append('  insert usz row')
else:
    report.append('  MISS   alloc_size anchor')

PRT = 'prot_size = vm_map_trunc_page(size - load_result->user_stack_size, vm_map_page_mask(map));'
if 'nabu_mark_num ("prt"' in src:
    report.append('  skip   prt already present')
elif PRT in src:
    src = src.replace(PRT,
        PRT + '\n'
        '\t\tnabu_mark_num ("prt", (unsigned long)prot_size, 1860);\n'
        '\t\tnabu_mark_num ("rls", (unsigned long)load_result->user_stack_size, 1940);', 1)
    report.append('  insert prt + rls rows')
else:
    report.append('  MISS   protect anchor')


# exec_add_apple_strings: the last writer into the user stack
AAS = 'error = exec_add_apple_strings(imgp, &load_result);'
if 'nabu_mark_num ("aasr"' in src:
    report.append('  skip   aas probes already present')
elif AAS in src:
    src = src.replace(AAS,
        'nabu_mark_num ("aas", 1, 2020);\n'
        '\t' + AAS + '\n'
        '\t\t/* retired: 2180 is taken by cp2; cpo0 proves success */', 1)
    report.append('  insert aas + aasr rows')
else:
    report.append('  MISS   exec_add_apple_strings anchor')

# what does it actually write? capture the stack pointer it uses
AASAP = 'exec_add_apple_strings(struct image_params *imgp, const load_result_t *load_result)'
if 'nabu_mark_num ("aasap"' in src:
    report.append('  skip   aasap already present')
elif AASAP in src:
    idx = src.find(AASAP)
    line_end = src.find('{', idx)
    if line_end > 0:
        src = src[:line_end + 1] + '\n\t/* retired: 2100 is taken by dnk */' + src[line_end + 1:]
        report.append('  insert aasap row')
    else:
        report.append('  MISS   function body')
else:
    report.append('  MISS   function anchor')


# the three copyoutptr calls after the dynlinker block
DLF = 'error = copyoutptr((user_addr_t)load_result.dynlinker_fd, ap, 8);'
DLM = 'error = copyoutptr(load_result.dynlinker_mach_header, ap + 8, 8);'
MBF = 'error = copyoutptr((user_addr_t)main_binary_fd, ap + 16, 8);'

for anchor, label, row in ((DLF, 'dlf', 2420), (DLM, 'dlm', 2500), (MBF, 'mbf', 2340)):
    tag = 'nabu_mark_num ("%s"' % label
    if tag in src:
        report.append('  skip   %s already present' % label)
    elif anchor in src:
        idx = src.find(anchor)
        line_end = src.find('\n', idx)
        src = (src[:line_end + 1] +
               '\t\tnabu_mark_num ("%s", (unsigned long)error, %d);\n' % (label, row) +
               src[line_end + 1:])
        report.append('  insert %s row %d' % (label, row))
    else:
        report.append('  MISS   %s anchor' % label)


# free page count at exec time: does page-in have anything to give?
FREEPG = 'nabu_mark_num ("aas", 1, 2020);'
if 'nabu_mark_num ("freepg"' in src:
    report.append('  skip   freepg already present')
elif FREEPG in src:
    decl = ('\n/* vm page counters, for the page-in failure hypothesis */\n'
            'extern unsigned int vm_page_free_count, vm_page_wire_count;\n')
    if 'extern unsigned int vm_page_free_count' not in src:
        hdr = '#include <sys/imgact.h>'
        src = src.replace(hdr, hdr + decl, 1) if hdr in src else decl + src
    src = src.replace(FREEPG,
        FREEPG + '\n'
        '\t\tnabu_mark_num ("freepg", (unsigned long)vm_page_free_count, 2420);\n'
        '\t\tnabu_mark_num ("wirepg", (unsigned long)vm_page_wire_count, 2500);', 1)
    report.append('  insert freepg + wirepg rows')
else:
    report.append('  MISS   anchor')


# Move the prefault ahead of the stack writes: fault-in cannot be relied on here.
# exec_prefault_data is declared void, so this only proves it ran before the writes.
PF_ANCHOR = '\t\tap = p->user_stack;'
if 'nabu_mark_text ("pf-early"' in src:
    report.append('  skip   early prefault already present')
elif PF_ANCHOR in src:
    src = src.replace(PF_ANCHOR,
        '\t\t/* NABU: prefault before any stack write -- fault-in panics instead of mapping here. */\n'
        '\t\texec_prefault_data(p, imgp, &load_result);\n'
        '\t\tnabu_mark_text ("pf-early", 2500);\n'
        + PF_ANCHOR, 1)
    report.append('  insert early prefault')
else:
    report.append('  MISS   user_stack anchor')

io.open(SRC, 'w', encoding='utf-8', newline='').write(src)
print('\n'.join(report))
