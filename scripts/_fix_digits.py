import io, re

p = r'C:\Users\Administrator\Documents\UniXNU\scripts\build-xnu-4k-baseline.sh'
s = io.open(p, encoding='utf-8', newline='').read()

old = """static void draw_number(unsigned int x0, unsigned int y0, int value, unsigned int s)
{
  if (value < 0) { value = 0; }
  if (value > 99) { value = 99; }
  if (value >= 10) { draw_digit(x0, y0, value / 10, s); }
  draw_digit(x0 + 4 * s, y0, value % 10, s);
}"""
new = """static void draw_number(unsigned int x0, unsigned int y0, int value, unsigned int s)
{
  /* Clear the whole two-digit cell first: without this a smaller value leaves the
   * previous tens digit behind and "4" reads as "54". */
  fill(x0, y0, 7 * s, 5 * s, 0xFF000000);
  if (value < 0) { value = 0; }
  if (value > 99) { value = 99; }
  if (value >= 10) { draw_digit(x0, y0, value / 10, s); }
  draw_digit(x0 + 4 * s, y0, value % 10, s);
}"""
assert old in s, 'draw_number not found'
s = s.replace(old, new, 1)

# bigger digits, and move them clear of the block strip (which is 232px tall)
s = s.replace('  draw_number(32, 120, max_hit(), 16);', '  draw_number(32, 132, max_hit(), 20);', 1)
s = s.replace('  draw_number(32, 120, n, 16);', '  draw_number(32, 132, n, 20);', 1)
# strip background must cover the taller digits
s = s.replace('  fill(0, 0, g_w, 232, 0xFF000000);', '  fill(0, 0, g_w, 260, 0xFF000000);', 1)

io.open(p, 'w', encoding='utf-8', newline='').write(s)
print('draw_number now clears its cell; digits enlarged')
