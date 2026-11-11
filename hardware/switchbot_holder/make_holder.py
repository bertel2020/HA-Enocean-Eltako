#!/usr/bin/env python3
"""SwitchBot Outdoor Meter on the wall, in front of a Berker S1 frame, screwed with the tray's own two
screw holes. The screws sit behind the meter and are not visible.

base_plate.stl   Closed mounting plate: 1.3 mm under the frame (the allowed thickness), screwed onto the
                 flush box with round holes (60 mm). Inside the window cut-out, where there is room, two
                 posts (y = +-18 mm, the screw positions of the tray) carry an M3 heat-set insert each.
front_piece.stl  The existing wall-mount tray (SwitchBotMount.3mf, meter clips in from the front), moved so
                 that its back face sits on the frame front, plus a thin cover plate on its back that
                 fills the whole window of the frame, 2 mm below the frame front (the frame is domed
                 and lower at the corners), so the cut-out is closed all around the meter. A 27.6 mm wide
                 web connects the plate to the tray across that 2 mm. The posts pass through holes in it.

Hardware: 2 x M3 heat-set insert (about 5.7 mm long, 4.6 mm outer, soldering iron at 200-220 C for PLA),
          2 x M3 x 8 button head screw (ISO 7380: head 5.7 mm wide, 1.65 mm high).
The tray's own holes (4.0 mm through, 7.2 mm counterbore only 1 mm deep) are filled and redrilled to
fit these screws: 3.4 mm through hole, 6.4 mm counterbore 1.8 mm deep, so the head sits flush.
Assembly: plate onto the box, frame over it, tray with 2 screws into the inserts, meter clips in.

Print: plate flat, tray with the back face on the bed.
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


# --- mounting plate ---
BOX_SPACING = 60.0      # flush box screws, standard
BOX_HOLE = 4.5          # round, for the usual 3.5 mm box screws
PLATE = 70.0            # must fit into the hollow of the frame (ASSUMED free inner width >= 78)
PLATE_T = 1.3           # allowed thickness under the frame (given)

# --- screws (tray holes are redrilled for M3 x 8 button head) ---
HOLE_Y = 18.0           # the tray's screw holes at y = +-18, x = 0
FLOOR_TOP = 13.0        # top of the tray floor in the assembled position (3.0 mm thick floor, back face at 10)
OLD_HOLE_R = 3.6        # largest radius of the original counterbore
SCREW_HOLE_R = 1.7      # 3.4 mm through hole
HEAD_HOLE_R = 3.2       # 6.4 mm counterbore
HEAD_DEPTH = 1.8

# --- cover plate in the window ---
COVER = 56.0            # edge length incl. clearance (given)
COVER_RECESS = 2.0      # front face of the plate lies this far below the frame front (domed frame)
COVER_T = 1.6
WEB_HALF_X = 13.6       # web between plate and tray, same width as the tray
POST_HOLE_R = 4.7       # holes for the posts in plate and web

# --- posts (plate) ---
POST_Y = HOLE_Y          # the tray's screw holes are at y = +-18, x = 0
POST_R = 4.5
POST_TOP = FRAME_D - 0.2        # posts pass through the cover plate; the tray rests on the frame, the screws pull it down
INSERT_D = 4.0          # hole for an M3 heat-set insert (4.6 mm outer, check your insert)
INSERT_DEPTH = 7.0      # insert 5.7 mm + reserve; an M3x8 tip ends 0.8 mm below the insert

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
    prof = [(0.0, PLATE_T - 0.5), (POST_R, PLATE_T - 0.5), (POST_R, POST_TOP), (INSERT_D / 2, POST_TOP),
            (INSERT_D / 2, POST_TOP - INSERT_DEPTH), (0.0, POST_TOP - INSERT_DEPTH), (0.0, PLATE_T - 0.5)]
    for sy in (1, -1):
        tris += lathe(prof, 0.0, sy * POST_Y)
    return tris


def front_piece():
    tris = load_3mf_triangles(MOUNT_3MF)
    zmin = min(p[2] for t in tris for p in t)
    dz = FRAME_D - zmin                      # back face of the tray on the frame front (Z = FRAME_D)
    tris = [tuple((p[0], p[1], p[2] + dz) for p in t) for t in tris]
    # fill the original holes with a washer-shaped solid that has the new hole shape
    zr, zt = FRAME_D, FLOOR_TOP
    prof = [(SCREW_HOLE_R, zr), (OLD_HOLE_R + 0.1, zr), (OLD_HOLE_R + 0.1, zt), (HEAD_HOLE_R, zt),
            (HEAD_HOLE_R, zt - HEAD_DEPTH), (SCREW_HOLE_R, zt - HEAD_DEPTH), (SCREW_HOLE_R, zr)]
    for sy in (1, -1):
        tris += lathe(prof, 0.0, sy * HOLE_Y)
    # cover plate filling the window, recessed, and the web to the tray; holes for the posts
    c, ph = COVER / 2, POST_HOLE_R + 0.5
    patches = [(-ph, ph, sy * HOLE_Y - ph, sy * HOLE_Y + ph) for sy in (1, -1)]
    zf = FRAME_D - COVER_RECESS                 # front face of the plate
    zr = zf - COVER_T
    zt = FRAME_D + 0.1
    tris += cut_rect((-c, c, -c, c), patches, zr, zf)
    tris += cut_rect((-WEB_HALF_X, WEB_HALF_X, -c, c), patches, zf, zt)
    for sy in (1, -1):
        tris += round_hole_patch(0.0, sy * HOLE_Y, POST_HOLE_R, ph, zr, zf)
        tris += round_hole_patch(0.0, sy * HOLE_Y, POST_HOLE_R, ph, zf, zt)
    return tris


if __name__ == "__main__":
    for name, tris in (("base_plate", base_plate()), ("front_piece", front_piece())):
        write_stl(f"{name}.stl", name, tris)
        xs, ys, zs = zip(*[p for t in tris for p in t])
        print(f"{name}.stl: {max(xs)-min(xs):.1f} x {max(ys)-min(ys):.1f} x {max(zs)-min(zs):.1f} mm, "
              f"{len(tris)} tris, volume {volume(tris):.0f} mm3")
