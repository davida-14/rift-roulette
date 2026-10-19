"""Draw the app icon (a gold die on hextech navy) as a 256px PNG, no dependencies."""
import struct, sys, zlib

N = 256
NAVY, GOLD, DARK = (11, 17, 24, 255), (200, 166, 90, 255), (18, 27, 37, 255)
px = [[(0, 0, 0, 0)] * N for _ in range(N)]

def rrect(x0, y0, x1, y1, r, c):
    for y in range(y0, y1):
        for x in range(x0, x1):
            dx = max(x0 + r - x, 0, x - (x1 - 1 - r)); dy = max(y0 + r - y, 0, y - (y1 - 1 - r))
            if dx * dx + dy * dy <= r * r:
                px[y][x] = c

def dot(cx, cy, r, c):
    for y in range(cy - r, cy + r + 1):
        for x in range(cx - r, cx + r + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                px[y][x] = c

rrect(0, 0, N, N, 44, NAVY)
rrect(40, 40, 216, 216, 30, GOLD)
rrect(52, 52, 204, 204, 22, DARK)
for cx, cy in [(88, 88), (168, 88), (128, 128), (88, 168), (168, 168)]:
    dot(cx, cy, 15, GOLD)

raw = b"".join(b"\0" + bytes(v for p in row for v in p) for row in px)
def chunk(t, d): return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", N, N, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
open(sys.argv[1], "wb").write(png)
