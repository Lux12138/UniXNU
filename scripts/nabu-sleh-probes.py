#!/usr/bin/env python3
"""Paint the copyio recovery lookup inside handle_kernel_abort."""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/osfmk/arm64/sleh.c'
if not SRC.endswith('sleh.c'):
    sys.exit(0)

src = io.open(SRC, encoding='utf-8').read()
report = []

ANCHOR = '\tstruct copyio_recovery_entry *recover = find_copyio_recovery_entry(state);'
INJECT = (
    ANCHOR + '\n'
    '\tnabu_mark_num ("RV", (unsigned long)recover, 1900);\n'
    '\tnabu_mark_num ("PCOF",\n'
    '\t    (unsigned long)copyio_recovery_offset(get_saved_state_pc(state)), 1980);\n'
    '\tnabu_mark_num ("TB", (unsigned long)copyio_recover_table, 2060);'
)

if 'nabu_mark_num ("RV"' in src:
    report.append('  skip   RV present')
elif ANCHOR in src:
    src = src.replace(ANCHOR, INJECT, 1)
    report.append('  insert RV/PCOF/TB')
else:
    report.append('  MISS   recover anchor')


# --- FIX: strip PAC/slide before the copyio table lookup -------------------------------
# CopyioRecover uses the raw saved PC, which carries PAC bits on this build, so the offset
# misses every table entry and recover stays NULL. Wrap it the same way the rest of sleh.c
# treats this value.
FIX_OLD = '\tptrdiff_t offset = copyio_recovery_offset(get_saved_state_pc(state));'
FIX_NEW = '\tptrdiff_t offset = copyio_recovery_offset(VM_KERNEL_STRIP_PTR(get_saved_state_pc(state)));'
if 'VM_KERNEL_STRIP_PTR(get_saved_state_pc(state)));' in src and 'copyio_recovery_offset(VM_KERNEL_STRIP_PTR' in src:
    report.append('  fix    already applied')
elif FIX_OLD in src:
    src = src.replace(FIX_OLD, FIX_NEW, 1)
    report.append('  fix    PC unslid before copyio lookup')
else:
    report.append('  fix    MISS anchor')

# paint the recovery jump target
JT_ANCHOR = '\tthread->machine.recover_esr = esr;'
if 'nabu_mark_num ("JT"' in src:
    report.append('  skip   JT present')
elif JT_ANCHOR in src:
    src = src.replace(JT_ANCHOR,
        '\tnabu_mark_num ("JT", (unsigned long)recover->cre_recovery, 2140);\n'
        '\tnabu_mark_num ("RJ", (unsigned long)recover, 2220);\n'
        + JT_ANCHOR, 1)
    report.append('  insert JT/RJ')
else:
    report.append('  MISS   recover_esr anchor')

# paint the facts at the unconditional panic
PANIC_ANCHOR = '\tpanic_with_thread_kernel_state("Kernel data abort.", state);'
if 'nabu_mark_num ("R2"' in src:
    report.append('  skip   R2 present')
elif PANIC_ANCHOR in src:
    src = src.replace(PANIC_ANCHOR,
        '\tnabu_mark_num ("R2", (unsigned long)recover, 2300);\n'
        '\tnabu_mark_num ("FC", (unsigned long)fault_code, 2380);\n'
        + PANIC_ANCHOR, 1)
    report.append('  insert R2/FC')
else:
    report.append('  MISS   panic anchor')

io.open(SRC, 'w', encoding='utf-8', newline='').write(src)

print('\n'.join(report))
