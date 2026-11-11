#!/usr/bin/env python3
"""SwitchBot Outdoor Meter on the wall, in front of a Berker S1 frame: magnets and locating pins,
no screws, nothing that flexes (PLA is brittle), any number of cycles.

base_plate.stl   Closed mounting plate: 1.3 mm under the frame (the allowed thickness), screwed onto the
                 flush box with round holes (60 mm). Inside the window cut-out, where there is room, four
                 posts stand on it. Each post has a socket (locating) with a magnet pocket at the bottom.
front_piece.stl  The existing wall-mount tray (SwitchBotMount.3mf, meter clips in from the front) with
                 four spigots on its back. A spigot enters the socket of its post (carries the weight,
                 fixes the position) and a magnet pair pulls the tray onto the frame.

Magnets: 8 discs 6 x 2 mm (N35 or stronger), two per post/spigot pair, glued in with matching polarity
(mark them before gluing). Four pairs hold roughly 3-4 kg; use only two pairs for a lighter pull.

Print: plate flat. Tray with the back face on the bed (spigot pockets open to the bed, no supports).
Axes: X width, Y height (up), Z away from the wall (Z=0 is the wall / rear face of the plate).
All values in mm. Re-generate with:  python3 -I make_holder.py
"""
import math
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# --- frame (measured) ---
WINDOW = 56.0
FRAME_D = 10.0          # depth of the frame; the tray's back face sits at this height

# --- tray (measured from SwitchBotMount.3mf) ---
HOLE_Y = 18.0           # its two (unused) screw holes at y = +-18, closed again

# --- mounting plate ---
BOX_SPACING = 60.0      # flush box screws, standard
BOX_HOLE = 4.5          # round, for the usual 3.5 mm box screws
PLATE = 70.0            # must fit into the hollow of the frame (ASSUMED free inner width >= 78)
PLATE_T = 1.3           # allowed thickness under the frame (given)

# --- posts (plate) and spigots (tray) ---
POST_X, POST_Y = 8.2, 16.0      # centres (+-, +-), inside the window cut-out
POST_R = 5.4
POST_TOP = 8.4
SOCKET_R = 4.2          # socket for the spigot (spigot r 4.0 + 0.2 clearance)
SOCKET_FLOOR = 5.4
MAGNET_D, MAGNET_H = 6.0, 2.0
POCKET_R = MAGNET_D / 2 + 0.075 # pocket for a glued-in magnet
SPIGOT_R = 4.0
SPIGOT_Z0 = 6.2         # rear end of the spigot; tray back face is at FRAME_D
SPIGOT_TOP = FRAME_D + 0.5      # overlaps into the tray base

MOUNT_3MF = Path(__file__).with_name("SwitchBotMount.3mf")


def load_3mf_triangles(path):
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.startswith("3D/Objects/") and n.endswith(".model"))
        root = ET.fromstring(z.read(name))
    ns = {"m": root.tag.split("}")[0][1:]}
    verts = [(float(v.get("x")), float(v.get("y")), float(v.get("z"))) for v in root.iterfind(".//m:vertex", ns)]
    return [tuple(verts[int(t.get(k))] for k in ("v1", "v2", "v3")) for t in root.iterfind(".//m:triangle", ns)]


def write_stl(path, name, tris):
    with open(path, "w") as fh:
        fh.write(f"solid {name}\n")
        for p0, p1, p2 in tris:
            u = [p1[i] - p0[i] for i in range(3)]
            v = [p2[i] - p0[i] for i in range(3)]
            n = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
            ln = math.sqrt(sum(c*c for c in n)) or 1.0
            fh.write(f" facet normal {n[0]/ln:.5f} {n[1]/ln:.5f} {n[2]/ln:.5f}\n  outer loop\n")
            for p in (p0, p1, p2):
                fh.write(f"   vertex {p[0]:.4f} {p[1]:.4f} {p[2]:.4f}\n")
            fh.write("  endloop\n endfacet\n")
        fh.write(f"endsolid {name}\n")


def volume(tris):
    return sum(sum(a[i]*(b[(i+1)%3]*c[(i+2)%3]-b[(i+2)%3]*c[(i+1)%3]) for i in range(3)) / 3
               for a, b, c in tris) / 2


def box_tris(x0, x1, y0, y1, z0, z1):
    f = [((x0,y0,z0),(x0,y1,z0),(x1,y1,z0),(x1,y0,z0)),
         ((x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)),
         ((x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1)),
         ((x0,y1,z0),(x0,y1,z1),(x1,y1,z1),(x1,y1,z0)),
         ((x0,y0,z0),(x0,y0,z1),(x0,y1,z1),(x0,y1,z0)),
         ((x1,y0,z0),(x1,y1,z0),(x1,y1,z1),(x1,y0,z1))]
    return [t for a, b, c, d in f for t in ((a, b, c), (a, c, d))]


def cut_rect(outer, cutouts, z0, z1):
    """Rectangle (x0, x1, y0, y1) minus rectangular cutouts, as boxes from grid cells."""
    xs = sorted({outer[0], outer[1], *[min(max(v, outer[0]), outer[1]) for h in cutouts for v in h[0:2]]})
    ys = sorted({outer[2], outer[3], *[min(max(v, outer[2]), outer[3]) for h in cutouts for v in h[2:4]]})
    tris = []
    for xa, xb in zip(xs, xs[1:]):
        for ya, yb in zip(ys, ys[1:]):
            cx, cy = (xa + xb) / 2, (ya + yb) / 2
            if xb - xa > 1e-6 and yb - ya > 1e-6 and not any(h[0] < cx < h[1] and h[2] < cy < h[3] for h in cutouts):
                tris += box_tris(xa, xb, ya, yb, z0, z1)
    return tris


def lathe(profile, cx, cy, n=32):
    """Solid of revolution around the vertical axis at (cx, cy). profile = [(r, z), ...] from the
    bottom centre (r=0) up to the top centre (r=0), counter-clockwise seen from the side (outside on +r)."""
    tris = []
    for k in range(n):
        a0, a1 = 2 * math.pi * k / n, 2 * math.pi * (k + 1) / n
        for (r0, z0), (r1, z1) in zip(profile, profile[1:]):
            p00 = (cx + r0 * math.cos(a0), cy + r0 * math.sin(a0), z0)
            p01 = (cx + r0 * math.cos(a1), cy + r0 * math.sin(a1), z0)
            p10 = (cx + r1 * math.cos(a0), cy + r1 * math.sin(a0), z1)
            p11 = (cx + r1 * math.cos(a1), cy + r1 * math.sin(a1), z1)
            if r0 > 0:
                tris.append((p00, p01, p11))
            if r1 > 0:
                tris.append((p00, p11, p10))
    return tris if volume(tris) > 0 else [(a, c, b) for a, b, c in tris]


def round_hole_patch(cx, cy, r, half, z0, z1, n=16):
    """Square patch (edge 2*half) with a round hole of radius r, as a ring-shaped mesh."""
    inner, outer = [], []
    for k in range(n):
        a = 2 * math.pi * k / n
        c, s = math.cos(a), math.sin(a)
        t = half / max(abs(c), abs(s))
        inner.append((cx + r * c, cy + r * s))
        outer.append((cx + t * c, cy + t * s))
    tris = []
    for k in range(n):
        k2 = (k + 1) % n
        i0, i1, o0, o1 = inner[k], inner[k2], outer[k], outer[k2]
        for z, up in ((z1, True), (z0, False)):
            quad = [(i0[0], i0[1], z), (o0[0], o0[1], z), (o1[0], o1[1], z), (i1[0], i1[1], z)]
            if not up:
                quad.reverse()
            tris += [(quad[0], quad[1], quad[2]), (quad[0], quad[2], quad[3])]
        # hole wall (normal towards the axis)
        a, b = (i0[0], i0[1]), (i1[0], i1[1])
        tris += [((a[0], a[1], z0), (b[0], b[1], z1), (b[0], b[1], z0)),
                 ((a[0], a[1], z0), (a[0], a[1], z1), (b[0], b[1], z1))]
        # patch edge (outward)
        a, b = o0, o1
        tris += [((a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1)),
                 ((a[0], a[1], z0), (b[0], b[1], z1), (a[0], a[1], z1))]
    return tris


def base_plate():
    half, sp, ph = PLATE / 2, BOX_SPACING / 2, 4.0
    centres = [(sp, 0), (-sp, 0), (0, sp), (0, -sp)]
    patches = [(cx - ph, cx + ph, cy - ph, cy + ph) for cx, cy in centres]
    tris = cut_rect((-half, half, -half, half), patches, 0.0, PLATE_T)
    for cx, cy in centres:
        tris += round_hole_patch(cx, cy, BOX_HOLE / 2, ph, 0.0, PLATE_T)
    prof = [(0.0, PLATE_T - 0.5), (POST_R, PLATE_T - 0.5), (POST_R, POST_TOP), (SOCKET_R, POST_TOP),
            (SOCKET_R, SOCKET_FLOOR), (POCKET_R, SOCKET_FLOOR), (POCKET_R, SOCKET_FLOOR - MAGNET_H - 0.2),
            (0.0, SOCKET_FLOOR - MAGNET_H - 0.2), (0.0, PLATE_T - 0.5)]
    for sx in (1, -1):
        for sy in (1, -1):
            tris += lathe(prof, sx * POST_X, sy * POST_Y)
    return tris


def spigot(cx, cy):
    prof = [(0.0, SPIGOT_TOP), (SPIGOT_R, SPIGOT_TOP), (SPIGOT_R, SPIGOT_Z0), (POCKET_R, SPIGOT_Z0),
            (POCKET_R, SPIGOT_Z0 + MAGNET_H + 0.2), (0.0, SPIGOT_Z0 + MAGNET_H + 0.2), (0.0, SPIGOT_TOP)]
    return lathe(prof, cx, cy)


def front_piece():
    tris = load_3mf_triangles(MOUNT_3MF)
    zmin = min(p[2] for t in tris for p in t)
    dz = FRAME_D - zmin
    tris = [tuple((p[0], p[1], p[2] + dz) for p in t) for t in tris]
    for sy in (1, -1):                                   # close the unused screw holes
        tris += box_tris(-4.0, 4.0, sy * HOLE_Y - 4.0, sy * HOLE_Y + 4.0, FRAME_D, FRAME_D + 2.3)
    for sx in (1, -1):
        for sy in (1, -1):
            tris += spigot(sx * POST_X, sy * POST_Y)
    return tris


if __name__ == "__main__":
    for name, tris in (("base_plate", base_plate()), ("front_piece", front_piece())):
        write_stl(f"{name}.stl", name, tris)
        xs, ys, zs = zip(*[p for t in tris for p in t])
        print(f"{name}.stl: {max(xs)-min(xs):.1f} x {max(ys)-min(ys):.1f} x {max(zs)-min(zs):.1f} mm, "
              f"{len(tris)} tris, volume {volume(tris):.0f} mm3")
