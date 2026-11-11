#!/usr/bin/env python3
"""SwitchBot Outdoor Meter on the wall, in front of a Berker S1 frame.

Idea: no snap fit, no base plate. The existing wall-mount tray (SwitchBotMount.3mf, meter clips in
from the front) is screwed to the wall THROUGH the frame window with its two own screws. Two spacer
sleeves of frame depth sit between tray and wall. The tray overlaps the frame border at the top
and bottom and clamps the frame to the wall.

Parts:  front_piece.stl  the tray, moved so that its back face sits on the frame front
        spacer.stl       print twice, one per screw

Axes: X width, Y height, Z away from the wall (Z=0 is the wall). All values in mm.
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

# --- spacer ---
SPACER_OD = 8.0
SPACER_ID = 4.2         # for 3.5-4 mm screws
SEGMENTS = 48

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


def front_piece():
    tris = load_3mf_triangles(MOUNT_3MF)
    zmin = min(p[2] for t in tris for p in t)
    dz = FRAME_D - zmin                    # back face of the tray on the frame front (Z = FRAME_D)
    return [tuple((p[0], p[1], p[2] + dz) for p in t) for t in tris]


def spacer():
    ro, ri, h = SPACER_OD / 2, SPACER_ID / 2, FRAME_D
    tris = []
    for k in range(SEGMENTS):
        a0, a1 = 2 * math.pi * k / SEGMENTS, 2 * math.pi * (k + 1) / SEGMENTS
        c0, s0, c1, s1 = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        O0t, O1t = (ro*c0, ro*s0, h), (ro*c1, ro*s1, h)
        O0b, O1b = (ro*c0, ro*s0, 0), (ro*c1, ro*s1, 0)
        I0t, I1t = (ri*c0, ri*s0, h), (ri*c1, ri*s1, h)
        I0b, I1b = (ri*c0, ri*s0, 0), (ri*c1, ri*s1, 0)
        tris += [(O0t, O1t, I1t), (O0t, I1t, I0t)]          # top, normal +Z
        tris += [(O0b, I1b, O1b), (O0b, I0b, I1b)]          # bottom, normal -Z
        tris += [(O0b, O1b, O1t), (O0b, O1t, O0t)]          # outside
        tris += [(I0b, I1t, I1b), (I0b, I0t, I1t)]          # inside, facing the axis
    return tris


if __name__ == "__main__":
    for name, tris in (("front_piece", front_piece()), ("spacer", spacer())):
        write_stl(f"{name}.stl", name, tris)
        xs, ys, zs = zip(*[p for t in tris for p in t])
        print(f"{name}.stl: {max(xs)-min(xs):.1f} x {max(ys)-min(ys):.1f} x {max(zs)-min(zs):.1f} mm, "
              f"{len(tris)} tris, volume {volume(tris):.0f} mm3")
