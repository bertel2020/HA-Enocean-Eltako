#!/usr/bin/env python3
"""Two-part holder for a SwitchBot Outdoor Meter behind a Berker S1 frame.

Part 1 (base plate): screwed to the wall, sits inside the hollow frame, collar stands in the window.
Part 2 (front piece): the user's wall-mount tray (SwitchBotMount.3mf, meter clips in from the front), two snap arms go through the window and
hook into the collar. The frame is clamped between plate and front piece.

Axes: X width, Y height, Z away from the wall (Z=0 is the wall). All values in mm.
Items marked ASSUMED are not measured. Axis-aligned boxes only, no ramps or fillets.
"""
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

# --- frame (measured by the user) ---
WINDOW = 56.0
BORDER = 14.0
FRAME_D = 10.0          # depth of the frame
# --- frame (ASSUMED) ---
FRONT_T = 2.5           # thickness of the frame front face
INNER = 78.0            # free inner width of the frame hollow


# --- fit ---
CLEAR = 0.2

# --- base plate ---
PLATE = 70.0            # must be < INNER
PLATE_T = 4.0
RING_T = 2.0
SCREW_X = 20.5          # screw hole centre offset from the middle
HOLE = 4.5

# --- snap ---
ARM_W = 10.0
ARM_T = 1.5
CATCH = 0.7             # block protrusion on the collar
BARB = 1.4

assert PLATE < INNER

MOUNT_3MF = Path(__file__).with_name("SwitchBotMount.3mf")   # the user's wall mount (U-shaped tray)


def load_3mf_triangles(path):
    """Return [(p0, p1, p2), ...] of the first mesh object in a 3MF (no transforms applied)."""
    with zipfile.ZipFile(path) as z:
        name = next(n for n in z.namelist() if n.startswith("3D/Objects/") and n.endswith(".model"))
        root = ET.fromstring(z.read(name))
    ns = {"m": root.tag.split("}")[0][1:]}
    verts = [(float(v.get("x")), float(v.get("y")), float(v.get("z"))) for v in root.iterfind(".//m:vertex", ns)]
    return [tuple(verts[int(t.get(k))] for k in ("v1", "v2", "v3")) for t in root.iterfind(".//m:triangle", ns)]


class Mesh:
    def __init__(self):
        self.boxes = []
        self.tris = []

    def box(self, x0, x1, y0, y1, z0, z1):
        assert x1 > x0 and y1 > y0 and z1 > z0, (x0, x1, y0, y1, z0, z1)
        self.boxes.append((x0, x1, y0, y1, z0, z1))

    def mirror_xy(self, x0, x1, y0, y1, z0, z1, mx=True, my=True):
        for sx in ((1, -1) if mx else (1,)):
            for sy in ((1, -1) if my else (1,)):
                xa, xb = sorted((sx * x0, sx * x1))
                ya, yb = sorted((sy * y0, sy * y1))
                self.box(xa, xb, ya, yb, z0, z1)

    def write(self, path, name):
        with open(path, "w") as fh:
            fh.write(f"solid {name}\n")
            for x0, x1, y0, y1, a, c in self.boxes:
                faces = [
                    ((x0,y0,a),(x0,y1,a),(x1,y1,a),(x1,y0,a),(0,0,-1)),
                    ((x0,y0,c),(x1,y0,c),(x1,y1,c),(x0,y1,c),(0,0,1)),
                    ((x0,y0,a),(x1,y0,a),(x1,y0,c),(x0,y0,c),(0,-1,0)),
                    ((x0,y1,a),(x0,y1,c),(x1,y1,c),(x1,y1,a),(0,1,0)),
                    ((x0,y0,a),(x0,y0,c),(x0,y1,c),(x0,y1,a),(-1,0,0)),
                    ((x1,y0,a),(x1,y1,a),(x1,y1,c),(x1,y0,c),(1,0,0)),
                ]
                for p0, p1, p2, p3, n in faces:
                    for tri in ((p0, p1, p2), (p0, p2, p3)):
                        fh.write(f" facet normal {n[0]} {n[1]} {n[2]}\n  outer loop\n")
                        for p in tri:
                            fh.write(f"   vertex {p[0]:.3f} {p[1]:.3f} {p[2]:.3f}\n")
                        fh.write("  endloop\n endfacet\n")
            for p0, p1, p2 in self.tris:
                ux, uy, uz = (p1[i] - p0[i] for i in range(3))
                vx, vy, vz = (p2[i] - p0[i] for i in range(3))
                n = (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)
                ln = sum(c * c for c in n) ** 0.5 or 1.0
                fh.write(f" facet normal {n[0]/ln:.5f} {n[1]/ln:.5f} {n[2]/ln:.5f}\n  outer loop\n")
                for p in (p0, p1, p2):
                    fh.write(f"   vertex {p[0]:.4f} {p[1]:.4f} {p[2]:.4f}\n")
                fh.write("  endloop\n endfacet\n")
            fh.write(f"endsolid {name}\n")

    def size(self):
        xs = [v for b in self.boxes for v in b[0:2]] + [p[0] for t in self.tris for p in t]
        ys = [v for b in self.boxes for v in b[2:4]] + [p[1] for t in self.tris for p in t]
        zs = [v for b in self.boxes for v in b[4:6]] + [p[2] for t in self.tris for p in t]
        return max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)


def base_plate():
    m = Mesh()
    p = PLATE / 2
    hx0, hx1 = SCREW_X - HOLE / 2, SCREW_X + HOLE / 2
    h = HOLE / 2
    m.box(-hx0, hx0, -p, p, 0, PLATE_T)                 # centre strip
    m.mirror_xy(hx1, p, -p, p, 0, PLATE_T, my=False)    # outer strips
    m.mirror_xy(hx0, hx1, h, p, 0, PLATE_T, my=False)   # above the holes
    m.mirror_xy(hx0, hx1, -p, -h, 0, PLATE_T, my=False) # below the holes
    # collar ring in the window, up to the front of the frame
    ro = WINDOW / 2 - CLEAR
    ri = ro - RING_T
    z1 = FRAME_D
    m.box(-ro, ro, ri, ro, PLATE_T, z1)
    m.box(-ro, ro, -ro, -ri, PLATE_T, z1)
    m.box(-ro, -ri, -ri, ri, PLATE_T, z1)
    m.box(ri, ro, -ri, ri, PLATE_T, z1)
    # catch blocks under which the barbs hook (top and bottom)
    m.mirror_xy(-6, 6, ri - CATCH, ri, PLATE_T + BARB + 0.0, PLATE_T + BARB + 1.2, mx=False)
    return m


def front_piece():
    """The user's tray (base at the back, open at the front) with its back face on the frame front,
    plus two snap arms through the window."""
    m = Mesh()
    tris = load_3mf_triangles(MOUNT_3MF)
    zmin = min(p[2] for t in tris for p in t)
    dz = FRAME_D - zmin                      # base rear face rests on the frame front (Z = FRAME_D)
    m.tris = [tuple((p[0], p[1], p[2] + dz) for p in t) for t in tris]
    # close the two countersunk screw holes of the original wall mount (unused here)
    base_t = 2.6
    for sy in (1, -1):
        m.box(-4.0, 4.0, sy * 18.0 - 4.0, sy * 18.0 + 4.0, FRAME_D, FRAME_D + base_t)
    ri = WINDOW / 2 - CLEAR - RING_T
    out = ri - 1.6                           # outer face of the arm
    zb = PLATE_T
    for sy in (1, -1):
        ya, yb = sorted((sy * (out - ARM_T), sy * out))
        m.box(-ARM_W / 2, ARM_W / 2, ya, yb, zb, FRAME_D + 1.0)
        ya, yb = sorted((sy * out, sy * (out + BARB)))
        m.box(-ARM_W / 2, ARM_W / 2, ya, yb, zb, zb + BARB)
    return m


if __name__ == "__main__":
    for name, mesh in (("base_plate", base_plate()), ("front_piece", front_piece())):
        path = f"{name}.stl"
        mesh.write(path, name)
        print(path, "%.1f x %.1f x %.1f mm" % mesh.size(), f"({len(mesh.boxes)} boxes, {len(mesh.tris)} tris)")
