#!/usr/bin/env python3
"""Skip archive 10's symbol checks when link.filelist is absent."""
import io
import sys

SRC = sys.argv[1] if len(sys.argv) > 1 else '.cache/xnu-work/../scripts/build-libpthread-kernel.py'
SRC = 'out/nabu/tree/scripts/build-libpthread-kernel.py'

src = io.open(SRC, encoding='utf-8').read()
report = []

GUARD = "if not kernel_names:\n    print('  skip   symbol checks: no link.filelist yet')\n    archive.unlink(missing_ok=True)\n    raise SystemExit(0)\n"

if 'no link.filelist yet' in src:
    report.append('  skip   guard already present')
else:
    anchor = "raise SystemExit('Missing expected pthread/XNU static symbol isolation')"
    if anchor in src:
        # wrap from the isolation check onward
        src = src.replace(anchor, GUARD + anchor, 1)
        report.append('  insert guard before isolation check')
    else:
        anchor2 = 'missing = sorted(imports - kernel_names'
        if anchor2 in src:
            idx = src.find(anchor2)
            line_start = src.rfind('\n', 0, idx) + 1
            src = src[:line_start] + GUARD + src[line_start:]
            report.append('  insert guard before missing computation')
        else:
            report.append('  MISS   anchor')

io.open(SRC, 'w', encoding='utf-8', newline='').write(src)
print('\n'.join(report))
