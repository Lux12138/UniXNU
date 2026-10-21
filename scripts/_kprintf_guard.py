import io

p = r'C:\Users\Administrator\Documents\UniXNU\scripts\build-xnu-4k-baseline.sh'
s = io.open(p, encoding='utf-8', newline='').read()

# 1) the flag lives with the other nabu globals
anchor_g = "unsigned long long g_hits;"
add_g = """/* Set once the framebuffer console is really usable. Every early kprintf before
 * that point faults, and it has killed the boot three separate times now (VERBOSE
 * startup logging, mig_init's diagnostics, and the panic path itself). */
int nabu_console_up;
unsigned long long g_hits;"""
if anchor_g in s and 'int nabu_console_up;' not in s:
    s = s.replace(anchor_g, add_g, 1)

# 2) raise it as soon as vcattach finishes wiring the screen
old_rebind = """    if 'nabu_mark_rebind' not in vc:"""
new_rebind = """    vc = vc.replace('\\t}\\n\\n', '\\t}\\n\\n', 1)
    if 'nabu_console_up = 1;' not in vc:
        _m = re.search(r'^vcattach\\(void\\)\\n\\{\\n', vc, re.M)
        if _m:
            _i = _m.end(); _d = 1
            while _i < len(vc) and _d > 0:
                if vc[_i] == '{':
                    _d += 1
                elif vc[_i] == '}':
                    _d -= 1
                _i += 1
            _close = _i - 1
            vc = vc[:_close] + '\\tnabu_console_up = 1;\\n' + vc[_close:]
    if 'nabu_mark_rebind' not in vc:"""
if old_rebind in s and 'nabu_console_up = 1;' not in s:
    s = s.replace(old_rebind, new_rebind, 1)

# 3) gate kprintf on it (printf.c is a new injected file, argv[6])
anchor_kop = """io.open(kop,'w',encoding='utf-8',newline='').write(ko)"""
add_kop = """io.open(kop,'w',encoding='utf-8',newline='').write(ko)

prc=sys.argv[6]
pr=io.open(prc,encoding='utf-8').read()
if 'nabu_console_up' not in pr:
    pr = 'extern int nabu_console_up;\\n' + pr
    # guard the two entry points
    pr = pr.replace('kprintf(const char *fmt, ...)\\n{',
                    'kprintf(const char *fmt, ...)\\n{\\n\\tif (!nabu_console_up) { return 0; }', 1)
    pr = pr.replace('vkprintf(const char *fmt, va_list ap)\\n{',
                    'vkprintf(const char *fmt, va_list ap)\\n{\\n\\tif (!nabu_console_up) { return 0; }', 1)
    print('  printf.c: kprintf gated on the console flag')
io.open(prc,'w',encoding='utf-8',newline='').write(pr)"""
if anchor_kop in s and 'printf.c: kprintf gated' not in s:
    s = s.replace(anchor_kop, add_kop, 1)

# 4) pass printf.c through both helpers
s = s.replace(".cache/xnu-work/osfmk/kern/ipc_kobject.c <<'MKU'",
              ".cache/xnu-work/osfmk/kern/ipc_kobject.c .cache/xnu-work/osfmk/kern/printf.c <<'MKU'", 1)
s = s.replace(".cache/xnu-work/osfmk/kern/ipc_kobject.c <<'MKP'",
              ".cache/xnu-work/osfmk/kern/ipc_kobject.c .cache/xnu-work/osfmk/kern/printf.c <<'MKP'", 1)

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('kprintf guard wired (NOT yet built)')
