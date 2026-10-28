"""Draw simple economics graphs as text for tutorial answers: python scripts/graph.py <preset> | --list
Straight lines only (PPC is an arc). Add a preset = one line in PRESETS."""
import env, sys

BS = chr(92)
SH = ':'  # shifted curves

def graph(lines, marks=(), hl=(), N=9, W=40, ylab="Price", xlab="Quantity", yl=None, note=""):
    g = [[' '] * W for _ in range(N + 1)]
    for lab, ch, a, s, *rr in lines:  # x = a + s*row (row 0 = top); optional (first, last) row
        r0, r1 = rr or (0, N - 1)
        for r in range(r0, r1 + 1):
            x = round(a + s * r)
            if 0 <= x < W:
                g[r + 1][x] = ch if g[r + 1][x] == ' ' else '+'
        for i, c in enumerate(lab):
            x = round(a + s * (r0 - 1)) + i
            if 0 <= x < W and g[r0][x] == ' ':
                g[r0][x] = c
    for r in hl:
        g[r + 1] = ['.' if c == ' ' else c for c in g[r + 1]]
    for r, x, t in marks:
        for i, c in enumerate(t):
            g[r + 1][x + i] = c
    out = [ylab] + [f"{(yl or {}).get(i - 1, ''):>4} |" + ''.join(row).rstrip() for i, row in enumerate(g)]
    out.append("     +" + '-' * W + " " + xlab)
    return '\n'.join(out) + ("\n" + note if note else "")

def ppc():
    H, Wd = 14, 42
    g = [[' '] * Wd for _ in range(H + 1)]
    for w, h, ch in [(40, 14, 'o'), (30, 10, '*'), (20, 7, 'i')]:
        for x in range(w + 1):
            y = round(h * (1 - (x / w) ** 2) ** .5)
            g[H - y][x] = g[H - y][x] if g[H - y][x] != ' ' else ch
        for y in range(h + 1):
            x = round(w * (1 - (y / h) ** 2) ** .5)
            g[H - y][x] = g[H - y][x] if g[H - y][x] != ' ' else ch
    return '\n'.join(["Beef"] + ["   |" + ''.join(r).rstrip() for r in g] + ["   +" + '-' * Wd + " Autos",
        "   * original   o technology / more resources (outward)   i fewer resources (inward)"])

PRESETS = {
 "ppc": ppc,
 "supply-shift": lambda: graph([("S1", '/', 22, -2), ("S", '/', 28, -2), ("S2", '/', 34, -2)], N=7, W=44, ylab="Price", xlab="Quantity",
     note="S1 = decrease in supply (left), S2 = increase in supply (right); price of the good unchanged"),
 "supply-move": lambda: graph([("S", '/', 22, -2)], marks=[(3, 16, '*'), (6, 10, '*')], hl=[3, 6], N=8, W=44, yl={3: 'P1', 6: 'P0'},
     note="Own price rises P0 -> P1: movement UP along S, quantity supplied Q0 -> Q1"),
 "market": lambda: graph([("D", BS, 0, 2.5), ("S", '/', 37, -3.7)], marks=[(6, 15, '* E')], hl=[2, 8], W=46, ylab="Price ($/kg)", xlab="Quantity (kg)",
     yl={0: '10', 2: '8', 4: '6', 6: '4', 8: '2'},
     note="E = equilibrium ($4, 60 kg). $8 line: surplus (S right of D). $2 line: shortage (D right of S)"),
 "d-up-s-down": lambda: graph([("D", BS, 2, 2), ("D1", SH, 12, 2), ("S", '/', 22, -2), ("S1", SH, 16, -2)],
     marks=[(5, 11, 'E0'), (1, 13, 'E1')], hl=[1, 5], N=9, yl={1: 'P1', 5: 'P0'},
     note="D right and S left (D shifts more): P rises, Q rises (E1 right of E0). Smaller D shift: Q falls."),
 "d-small-s-down": lambda: graph([("D", BS, 2, 2), ("D1", SH, 6, 2), ("S", '/', 26, -2), ("S1", SH, 18, -2)],
     marks=[(6, 13, 'E0'), (3, 11, 'E1')], hl=[3, 6], N=9, yl={3: 'P1', 6: 'P0'},
     note="S shifts left a lot, D right a little: P rises, Q falls (E1 left of E0)"),
 "d-down-s-up": lambda: graph([("D1", SH, -4, 2), ("D", BS, 6, 2), ("S", '/', 22, -2), ("S1", SH, 26, -2)],
     marks=[(4, 13, 'E0'), (8, 11, 'E1')], hl=[4, 8], N=10, yl={4: 'P0', 8: 'P1'},
     note="D left and S right (D shifts more): P falls, Q falls (E1 left of E0). Smaller D shift: Q rises."),
 "adas-demand": lambda: graph([("AS", '/', 30, -3), ("AD", BS, 2, 2), ("AD1", SH, 8, 2)], marks=[(6, 12, 'E0'), (4, 16, 'E1')], hl=[4, 6], W=36,
     ylab="Price level", xlab="Real GDP", yl={4: 'P1', 6: 'P0'}, note="Demand-pull: AD shifts right, price level and output both rise"),
 "adas-cost": lambda: graph([("AS", '/', 34, -3), ("AS1", SH, 26, -3), ("AD", BS, 2, 2)], marks=[(6, 14, 'E0'), (5, 11, 'E1')], hl=[5, 6],
     ylab="Price level", xlab="Real GDP", yl={5: 'P1', 6: 'P0'}, note="Cost-push: AS shifts left, price level rises, output falls"),
}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in PRESETS:
        sys.exit("usage: graph.py <" + "|".join(PRESETS) + ">")
    print(PRESETS[sys.argv[1]]())
