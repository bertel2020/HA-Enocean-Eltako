#!/usr/bin/env python3
"""SwitchBot Outdoor Meter on the wall, in front of a Berker S1 frame, mounted without visible screws.

Mounting ring (base_plate.stl): flat 1.3 mm ring under the frame (the allowed thickness there), screwed
onto the flush box with the usual 60 mm screws. Inside the window cut-out the frame leaves room up to
its front face, so four small receptacle blocks (two at the top, two at the bottom edge of the opening)
stand up there, each with a rectangular catch window.

Front piece (front_piece.stl): the existing wall-mount tray (SwitchBotMount.3mf, meter clips in from the
front) with four matching snap arms on its back. Each arm has a lead-in ramp and a hook face that
locks in the window of its block. The tray rests on the top and bottom border of the frame and clamps it.

Axes: X width, Y height, Z away from the wall (Z=0 is the wall / rear face of the ring).
All values in mm. Re-generate with:  python3 -I make_holder.py
"""
import math
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# --- frame (measured) ---
WINDOW = 56.0
BORDER = 14.0
FRAME_D = 10.0          # depth of the frame = spacer length

# --- tray (measured from SwitchBotMount.3mf) ---
HOLE_Y = 18.0           # screw holes at y = +-18 (36 mm apart)

# --- flush box (standard 60 mm screw spacing, check yours) ---
BOX_SPACING = 60.0
BOX_HOLE = 4.5          # holes at (+-30, 0) and (0, +-30), so the ring fits either way round
PLATE = 70.0            # must fit into the hollow of the frame (ASSUMED free inner width 78)
PLATE_T = 1.3           # allowed thickness under the frame (given)
OPEN = 26.0             # half width of the square opening of the ring (box access)

# --- receptacle blocks (inside the window cut-out) ---
BLOCK_Y0, BLOCK_Y1 = 26.0, 27.8   # wall of the block, outer face stays 0.2 short of the window edge
BLOCK_X0, BLOCK_X1 = 5.4, 15.0    # block x range, mirrored to both sides
BLOCK_TOP = FRAME_D - 0.3         # stays below the frame front
WIN_X0, WIN_X1 = 6.6, 13.8        # catch window, x
WIN_Z0, WIN_Z1 = 1.5, 3.3         # catch window, z (upper edge catches the hook)

# --- snap arms (four) ---
ARM_X0, ARM_X1 = 7.4, 13.0     # inside the tray width (27.6)
ARM_T = 1.5
ARM_OUT = 25.8          # outer face of the arm (0.2 inside the block wall)
BARB = 1.0              # protrusion into the window
ARM_TIP = 1.6           # lowest point of the arm, above the ring

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
    f = [((x0,y0,z0),(x0,y1,z0),(x1,y1,z0),(x1,y0,z0)),      # bottom
         ((x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)),      # top
         ((x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1)),      # -Y
         ((x0,y1,z0),(x0,y1,z1),(x1,y1,z1),(x1,y1,z0)),      # +Y
         ((x0,y0,z0),(x0,y0,z1),(x0,y1,z1),(x0,y1,z0)),      # -X
         ((x1,y0,z0),(x1,y1,z0),(x1,y1,z1),(x1,y0,z1))]      # +X
    return [t for a, b, c, d in f for t in ((a, b, c), (a, c, d))]


def base_plate():
    """1.3 mm mounting ring with square opening and four box screw holes, plus four receptacle blocks."""
    half, sp = PLATE / 2, BOX_SPACING / 2
    def sq(cx, cy, d):
        return (cx - d / 2, cx + d / 2, cy - d / 2, cy + d / 2)
    holes = [sq(sp, 0, BOX_HOLE), sq(-sp, 0, BOX_HOLE), sq(0, sp, BOX_HOLE), sq(0, -sp, BOX_HOLE),
             (-OPEN, OPEN, -OPEN, OPEN)]
    xs = sorted({-half, half, *[v for h in holes for v in h[0:2]]})
    ys = sorted({-half, half, *[v for h in holes for v in h[2:4]]})
    tris = []
    for xa, xb in zip(xs, xs[1:]):
        for ya, yb in zip(ys, ys[1:]):
            cx, cy = (xa + xb) / 2, (ya + yb) / 2
            if not any(h[0] < cx < h[1] and h[2] < cy < h[3] for h in holes):
                tris += box_tris(xa, xb, ya, yb, 0.0, PLATE_T)
    for sy in (1, -1):
        for sx in (1, -1):
            def b(xa, xb, z0, z1):
                x0, x1 = sorted((sx * xa, sx * xb))
                y0, y1 = sorted((sy * BLOCK_Y0, sy * BLOCK_Y1))
                return box_tris(x0, x1, y0, y1, z0, z1)
            tris += b(BLOCK_X0, BLOCK_X1, 0.0, WIN_Z0)                       # below the window
            tris += b(BLOCK_X0, BLOCK_X1, WIN_Z1, BLOCK_TOP)                 # above the window
            tris += b(BLOCK_X0, WIN_X0, WIN_Z0, WIN_Z1)                      # jambs
            tris += b(WIN_X1, BLOCK_X1, WIN_Z0, WIN_Z1)
    return tris


def prism(profile, x0, x1):
    """Extrude a convex (y, z) polygon along X; returns triangles with outward normals."""
    def p(x, yz):
        return (x, yz[0], yz[1])
    tris = []
    n = len(profile)
    for k in range(n):
        a, b = profile[k], profile[(k + 1) % n]
        q = (p(x0, a), p(x1, a), p(x1, b), p(x0, b))
        tris += [(q[0], q[1], q[2]), (q[0], q[2], q[3])]
    for k in range(1, n - 1):
        tris.append((p(x0, profile[0]), p(x0, profile[k + 1]), p(x0, profile[k])))
        tris.append((p(x1, profile[0]), p(x1, profile[k]), p(x1, profile[k + 1])))
    return tris if volume(tris) > 0 else [(a, c, b) for a, b, c in tris]


def front_piece():
    tris = load_3mf_triangles(MOUNT_3MF)
    zmin = min(p[2] for t in tris for p in t)
    dz = FRAME_D - zmin                    # back face of the tray on the frame front (Z = FRAME_D)
    tris = [tuple((p[0], p[1], p[2] + dz) for p in t) for t in tris]
    # close the two countersunk screw holes of the original wall mount (not used here)
    for sy in (1, -1):
        tris += box_tris(-4.0, 4.0, sy * HOLE_Y - 4.0, sy * HOLE_Y + 4.0, FRAME_D, FRAME_D + 2.3)
    # four snap arms with lead-in ramp and hook face
    for sy in (1, -1):
        for sx in (1, -1):
            x0, x1 = sorted((sx * ARM_X0, sx * ARM_X1))
            ya, yb = sorted((sy * (ARM_OUT - ARM_T), sy * ARM_OUT))
            tris += box_tris(x0, x1, ya, yb, ARM_TIP, FRAME_D + 1.0)
            prof = [(ARM_OUT, ARM_TIP), (ARM_OUT + BARB, WIN_Z0 + 1.4), (ARM_OUT + BARB, WIN_Z1), (ARM_OUT, WIN_Z1)]
            prof = [(sy * y, z) for y, z in prof]
            tris += prism(prof, x0, x1)
    return tris


if __name__ == "__main__":
    for name, tris in (("base_plate", base_plate()), ("front_piece", front_piece())):
        write_stl(f"{name}.stl", name, tris)
        xs, ys, zs = zip(*[p for t in tris for p in t])
        print(f"{name}.stl: {max(xs)-min(xs):.1f} x {max(ys)-min(ys):.1f} x {max(zs)-min(zs):.1f} mm, "
              f"{len(tris)} tris, volume {volume(tris):.0f} mm3")
