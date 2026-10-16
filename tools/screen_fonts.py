#!/usr/bin/env python3
"""Builds the site's web fonts from the bitmap fonts our products draw their screens with.

    python3 tools/screen_fonts.py <NANO-FX-DR/src/ui>

Writes fonts/nano-screen-18.ttf and -18-bold (Terminus 10x18, the FX-DR2 glass's text face),
fonts/nano-screen-14.ttf and -14-bold (Terminus 8x14), fonts/nano-big.ttf (the 5x7 face the
big numbers are drawn in, on a 6x8 cell), and fonts/OFL.txt.

Every lit pixel becomes a square of the outline, so at a font size of one cell height in CSS
pixels (18px, 14px, 8px, or a whole multiple) each font pixel is one CSS pixel, or a whole
block of them, and the text is as crisp as on the glass. The outlines are the pixels' union:
one contour per connected shape, no overlaps.

Terminus Font is (c) Dimitar Toshkov Zhekov, under the SIL Open Font License 1.1 with the
Reserved Font Name "Terminus Font"; these are modified versions, so they go by another name.
"""
import re, struct, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
OUT = HERE / "fonts"

# --- the bitmaps --------------------------------------------------------------------------------

def terminus(path, w, h):
    """{code: rows of 0/1}; each row an 8- or 16-bit word, MSB = leftmost pixel."""
    bits = 8 if w <= 8 else 16
    out = {}
    for body, code in re.findall(r"\{([^{}]*)\}\s*,?\s*/\*\s*0x([0-9a-fA-F]{2})", Path(path).read_text()):
        rows = [int(v, 16) for v in re.findall(r"0x[0-9a-fA-F]+", body)]
        assert len(rows) == h, (path, code)
        out[int(code, 16)] = [[(r >> (bits - 1 - x)) & 1 for x in range(w)] for r in rows]
    assert len(out) == 95, path
    return out

def five_by_seven(canvas_cpp):
    """The 5x7 table in Canvas.cpp: 5 column bytes per glyph, bit 0 = top row. On a 6x8 cell."""
    src = Path(canvas_cpp).read_text()
    block = src[src.index("kFont5x7"):]
    block = block[:block.index("};")]
    glyphs = re.findall(r"\{(0x[^{}]*)\}", block)
    assert len(glyphs) == 95
    out = {}
    for i, body in enumerate(glyphs):
        cols = [int(v, 16) for v in re.findall(r"0x[0-9a-fA-F]+", body)]
        out[0x20 + i] = [[(cols[x] >> y) & 1 if x < 5 else 0 for x in range(6)] for y in range(8)]
    return out

def extras(g, w, h, base):
    """A few characters the pages use that the ASCII tables lack, drawn from what is there."""
    def blank(): return [[0] * w for _ in range(h)]
    dot = g[ord(".")]
    ys = [y for y in range(h) if any(dot[y])]
    # middle dot: the full stop, raised to the middle of the x-height
    top_x = next(y for y in range(h) if any(g[ord("x")][y]))
    centre = (top_x + base - 1) // 2
    shift = centre - (ys[0] + ys[-1]) // 2
    middot = blank()
    for y in ys:
        if 0 <= y + shift < h: middot[y + shift] = dot[y][:]
    # ellipsis: three full stops in one cell, as far apart as the cell allows
    xs = [x for x in range(w) if any(dot[y][x] for y in ys)]
    dw = xs[-1] - xs[0] + 1
    ell = blank()
    for i in range(3):
        x0 = round(i * (w - dw) / 2)
        for y in ys:
            for k in range(dw): ell[y][x0 + k] = dot[y][xs[0] + k]
    # right arrow: the minus sign's stroke with a head
    minus = g[ord("-")]
    my = [y for y in range(h) if any(minus[y])]
    mx = [x for x in range(w) if any(minus[y][x] for y in my)]
    arrow = blank()
    x0, x1 = (1, w - 2) if w > 6 else (mx[0], mx[-1])
    for y in my:
        for x in range(x0, x1 + 1): arrow[y][x] = 1
    head = max(1, (x1 - x0) // 2 - (1 if w > 8 else 0))
    for k in range(1, head + 1):
        for y in (my[0] - k, my[-1] + k):
            if 0 <= y < h: arrow[y][x1 - k] = 1
    back = [row[::-1] for row in arrow]            # left arrow: the right one, mirrored
    shift = min(x for row in arrow for x, v in enumerate(row) if v) - min(x for row in back for x, v in enumerate(row) if v)
    back = [[row[x - shift] if 0 <= x - shift < w else 0 for x in range(w)] for row in back]
    return {0x00B7: middot, 0x2026: ell, 0x2190: back, 0x2192: arrow}

# --- outlines -----------------------------------------------------------------------------------

def contours(bm, base, unit):
    """The union of the lit pixels as clockwise (y-up) contours, in font units."""
    edges = set()
    for y, row in enumerate(bm):
        for x, on in enumerate(row):
            if not on: continue
            j = base - y - 1                      # font row of the pixel's bottom edge
            for e in (((x, j), (x, j + 1)), ((x, j + 1), (x + 1, j + 1)),
                      ((x + 1, j + 1), (x + 1, j)), ((x + 1, j), (x, j))):
                rev = (e[1], e[0])
                if rev in edges: edges.remove(rev)
                else: edges.add(e)
    out_of = {}
    for a, b in edges: out_of.setdefault(a, []).append(b)
    loops = []
    while out_of:
        start = next(iter(out_of))
        loop, cur, prev_dir = [start], start, None
        while True:
            nxt = out_of[cur]
            if len(nxt) > 1 and prev_dir:         # pixels touching at a corner: hug this one
                def turn(b):
                    d = (b[0] - cur[0], b[1] - cur[1])
                    cross = prev_dir[0] * d[1] - prev_dir[1] * d[0]
                    return 0 if cross < 0 else (1 if cross == 0 else 2)   # right, straight, left
                nxt.sort(key=turn)
            b = nxt.pop(0)
            if not nxt: del out_of[cur]
            prev_dir = (b[0] - cur[0], b[1] - cur[1])
            cur = b
            if cur == start: break
            loop.append(cur)
        pts = []                                   # drop the points in the middle of a straight run
        n = len(loop)
        for i in range(n):
            a, p, c = loop[i - 1], loop[i], loop[(i + 1) % n]
            if (p[0] - a[0]) * (c[1] - p[1]) - (p[1] - a[1]) * (c[0] - p[0]) != 0:
                pts.append((p[0] * unit, p[1] * unit))
        loops.append(pts)
    return loops

def glyf_entry(loops):
    if not loops: return b"", (0, 0, 0, 0), 0
    pts = [p for l in loops for p in l]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    bbox = (min(xs), min(ys), max(xs), max(ys))
    ends, k = [], -1
    for l in loops:
        k += len(l); ends.append(k)
    data = struct.pack(">hhhhh", len(loops), *bbox)
    data += struct.pack(f">{len(ends)}H", *ends) + struct.pack(">H", 0)
    data += bytes([0x01] * len(pts))               # on-curve, 16-bit deltas
    px = py = 0
    for x, _ in pts: data += struct.pack(">h", x - px); px = x
    for _, y in pts: data += struct.pack(">h", y - py); py = y
    return data, bbox, len(pts)

# --- the font file ------------------------------------------------------------------------------

def checksum(b):
    b += b"\0" * (-len(b) % 4)
    return sum(struct.unpack(f">{len(b) // 4}I", b)) & 0xFFFFFFFF

def name_table(names):
    recs, strings = [], b""
    for nid, s in sorted(names.items()):
        e = s.encode("utf-16-be")
        recs.append(struct.pack(">HHHHHH", 3, 1, 0x409, nid, len(e), len(strings)))
        strings += e
    return struct.pack(">HHH", 0, len(recs), 6 + 12 * len(recs)) + b"".join(recs) + strings

def cmap_table(codes):                             # codes: sorted [(codepoint, glyph id)]
    segs = []
    for c, g in codes:
        if segs and c == segs[-1][1] + 1 and g - c == segs[-1][2]: segs[-1][1] = c
        else: segs.append([c, c, g - c])
    segs.append([0xFFFF, 0xFFFF, 1])
    n = len(segs)
    sr = 2 * (1 << (n.bit_length() - 1))
    sub = struct.pack(">HHHHHHH", 4, 16 + 8 * n, 0, 2 * n, sr, (sr // 2).bit_length() - 1, 2 * n - sr)
    sub += struct.pack(f">{n}H", *[s[1] for s in segs]) + b"\0\0"
    sub += struct.pack(f">{n}H", *[s[0] for s in segs])
    sub += struct.pack(f">{n}H", *[s[2] & 0xFFFF for s in segs])
    sub += struct.pack(f">{n}H", *([0] * n))
    return struct.pack(">HHHHI", 0, 1, 3, 1, 12) + sub

def build(glyphs, w, h, base, unit, family, style, out):
    bold = style == "Bold"
    upm, adv = h * unit, w * unit
    codes = sorted(glyphs)
    order = [None] + codes                          # glyph 0 = .notdef, empty
    glyf, loca, hmtx = b"", [], b""
    bboxes, max_pts, max_cont = [], 0, 0
    for c in order:
        loops = contours(glyphs[c], base, unit) if c is not None else []
        data, bbox, npts = glyf_entry(loops)
        loca.append(len(glyf))
        glyf += data + b"\0" * (-len(data) % 4)
        hmtx += struct.pack(">Hh", adv, bbox[0])
        if data: bboxes.append(bbox)
        max_pts, max_cont = max(max_pts, npts), max(max_cont, len(loops))
    loca.append(len(glyf))
    xmin = min(b[0] for b in bboxes); ymin = min(b[1] for b in bboxes)
    xmax = max(b[2] for b in bboxes); ymax = max(b[3] for b in bboxes)
    asc, desc = base * unit, (h - base) * unit
    cap = sum(1 for r in glyphs[ord("H")] if any(r)) * unit
    xh = sum(1 for r in glyphs[ord("x")] if any(r)) * unit
    n = len(order)
    t = {}
    t["head"] = struct.pack(">IIIIHHqqhhhhHHhhh", 0x00010000, 0x00010000, 0, 0x5F0F3CF5, 0x000B, upm,
                            0, 0, xmin, ymin, xmax, ymax, 1 if bold else 0, 8, 2, 1, 0)
    t["hhea"] = struct.pack(">IhhhHhhhhhhhhhhhH", 0x00010000, asc, -desc, 0, adv, xmin, adv - xmax, xmax,
                            1, 0, 0, 0, 0, 0, 0, 0, n)
    t["maxp"] = struct.pack(">IHHHHHHHHHHHHHH", 0x00010000, n, max_pts, max_cont, 0, 0, 2, 0, 0, 0, 0, 0, 0, 0, 0)
    t["hmtx"] = hmtx
    t["loca"] = struct.pack(f">{len(loca)}I", *loca)
    t["glyf"] = glyf
    t["cmap"] = cmap_table([(c, i + 1) for i, c in enumerate(codes)])
    t["OS/2"] = struct.pack(">HhHHHhhhhhhhhhhh10BIIII4sHHHhhhHHIIhhHHH",
        4, adv, 700 if bold else 400, 5, 0,
        upm // 2, upm // 2, 0, upm // 8, upm // 2, upm // 2, 0, upm // 3, unit, xh // 2, 0x0800,
        2, 0, 6 if bold else 5, 9, 0, 0, 0, 0, 0, 0,
        1, 0, 0, 0, b"NANO", (0x20 if bold else 0x40) | 0x80, min(codes), min(max(codes), 0xFFFF),
        asc, -desc, 0, asc, desc, 1, 0, xh, cap, 0, 0x20, 1)
    full = f"{family} {style}" if style != "Regular" else family
    t["name"] = name_table({
        0: "Copyright (c) 2010-2020 Dimitar Toshkov Zhekov (Terminus Font). Modified by NANO Industries, 2026.",
        1: family, 2: style, 3: f"NANO Industries: {full}: 2026", 4: full, 5: "Version 1.000",
        6: full.replace(" ", "-"),
        13: "This Font Software is licensed under the SIL Open Font License, Version 1.1.",
        14: "https://openfontlicense.org"})
    t["post"] = struct.pack(">IIhhIIIII", 0x00030000, 0, -unit, unit, 1, 0, 0, 0, 0)
    tags = sorted(t)
    nt = len(tags)
    sr = 16 * (1 << (nt.bit_length() - 1))
    head = struct.pack(">IHHHH", 0x00010000, nt, sr, (sr // 16).bit_length() - 1, nt * 16 - sr)
    off = 12 + 16 * nt
    dirs, body = b"", b""
    for tag in tags:
        data = t[tag]
        dirs += struct.pack(">4sIII", tag.encode(), checksum(data), off + len(body), len(data))
        body += data + b"\0" * (-len(data) % 4)
    font = bytearray(head + dirs + body)
    # checkSumAdjustment: the head table's third word
    pos = 12 + 16 * nt + sum(len(t[x]) + (-len(t[x]) % 4) for x in tags[:tags.index("head")]) + 8
    struct.pack_into(">I", font, pos, (0xB1B0AFBA - checksum(bytes(font))) & 0xFFFFFFFF)
    out.write_bytes(font)
    return len(font)

def main():
    ui = Path(sys.argv[1] if len(sys.argv) > 1 else "../DAISY-Dev/NANO-FX-DR/src/ui")
    OUT.mkdir(exist_ok=True)
    jobs = [
        ("font_10x18.h", 10, 18, 15, 100, "NANO Screen", "Regular", "nano-screen-18.ttf"),
        ("font_10x18_bold.h", 10, 18, 15, 100, "NANO Screen", "Bold", "nano-screen-18-bold.ttf"),
        ("font_8x14.h", 8, 14, 12, 128, "NANO Screen Small", "Regular", "nano-screen-14.ttf"),
        ("font_8x14_bold.h", 8, 14, 12, 128, "NANO Screen Small", "Bold", "nano-screen-14-bold.ttf"),
    ]
    for src, w, h, base, unit, fam, style, name in jobs:
        g = terminus(ui / "fonts" / src, w, h)
        g.update(extras(g, w, h, base))
        print(f"{name}: {build(g, w, h, base, unit, fam, style, OUT / name)} B")
    g = five_by_seven(ui / "Canvas.cpp")
    g.update(extras(g, 6, 8, 7))
    print(f"nano-big.ttf: {build(g, 6, 8, 7, 200, 'NANO Big', 'Regular', OUT / 'nano-big.ttf')} B")
    lic = Path("/Users/jorge/Documents/Rack2/plugins-mac-arm64/Befaco/res/fonts/OFL.txt").read_text()
    body = lic[lic.index("-----"):]
    (OUT / "OFL.txt").write_text(
        "NANO Screen and NANO Screen Small are modified versions of Terminus Font,\n"
        "Copyright (c) 2010-2020 Dimitar Toshkov Zhekov, with Reserved Font Name \"Terminus Font\".\n"
        "Modified by NANO Industries, 2026: converted from the bitmaps our products' screens use.\n\n"
        "This Font Software is licensed under the SIL Open Font License, Version 1.1.\n"
        "This license is copied below, and is also available with a FAQ at:\n"
        "https://openfontlicense.org\n\n\n" + body)

if __name__ == "__main__":
    main()
