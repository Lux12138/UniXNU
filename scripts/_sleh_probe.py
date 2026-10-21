import io

p = r'C:\Users\Administrator\Documents\UniXNU\scripts\build-xnu-4k-baseline.sh'
s = io.open(p, encoding='utf-8', newline='').read()

# wire sleh.c as argv[7]
s = s.replace(".cache/xnu-work/osfmk/kern/printf.c <<'MKU'",
              ".cache/xnu-work/osfmk/kern/printf.c .cache/xnu-work/osfmk/arm64/sleh.c <<'MKU'", 1)
s = s.replace(".cache/xnu-work/osfmk/kern/printf.c <<'MKP'",
              ".cache/xnu-work/osfmk/kern/printf.c .cache/xnu-work/osfmk/arm64/sleh.c <<'MKP'", 1)

anchor = """io.open(prc,'w',encoding='utf-8',newline='').write(pr)"""
add = """io.open(prc,'w',encoding='utf-8',newline='').write(pr)

# Every synchronous exception lands in sleh_synchronous with the syndrome and the
# faulting address in hand. Publish them instead of guessing: EC names the class
# (0x25 data abort from the same EL, 0x21 instruction abort, ...), and FAR is where.
slc=sys.argv[7]
sl=io.open(slc,encoding='utf-8').read()
if 'nabu_mark_quad' not in sl:
    sl=add_include(sl, '#include <pexpert/pexpert.h>')
    sl=ins_body_start(sl,
                      r'^sleh_synchronous\\(arm_context_t \\*context, uint32_t esr, vm_offset_t far[^\\n]*\\n\\{\\n',
                      ['nabu_mark_quad((int)((esr >> 26) & 0x3F), (int)(esr & 0x3F),',
                       '               (int)(far & 0xFF), (int)((far >> 8) & 0xFF));'],
                      'sleh_synchronous')
    print('  sleh.c: exception syndrome readout wired')
io.open(slc,'w',encoding='utf-8',newline='').write(sl)"""
assert anchor in s, 'prc anchor not found'
s = s.replace(anchor, add, 1)

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('sleh probe wired (NOT built)')
