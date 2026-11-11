#!/usr/bin/env python3
"""SwitchBot Outdoor Meter on the wall, in front of a Berker S1 frame, screwed with two M3 screws that
sit behind the meter and are not visible.

base_plate.stl   Closed mounting plate: 1.3 mm under the frame (the allowed thickness), screwed onto the
                 flush box with round holes (60 mm). Inside the window cut-out, where there is room, two
                 posts (y = +-18 mm) carry an M3 heat-set insert each.
front_piece.stl  Tray for the meter, own design (the first tray had 1.0 mm walls that flex when the meter
                 is clipped in and break in PLA). Walls are 2.4 mm, nothing flexes: the meter slides in
                 from the open top under two side lips and rests on the bottom wall. Underneath: a cover
                 plate that fills the whole window of the frame, 2 mm below the frame front (the frame
                 is domed and lower at the corners), and a web that connects plate and tray. The posts
                 pass through holes in plate and web.

Hardware: 2 x M3 heat-set insert (about 5.7 mm long, 4.6 mm outer, soldering iron at 200-220 C for PLA),
          2 x M3 x 8 button head screw (ISO 7380: head 5.7 mm wide, 1.65 mm high), through the tray floor
          (3.4 mm hole, 6.4 mm counterbore 1.8 mm deep, the head sits flush).
Assembly: plate onto the box, frame over it, tray with 2 screws into the inserts, meter slides in from the top.

Print: plate flat, tray with the cover plate on the bed (pocket walls stand up, 2.4 mm thick).
Axes: X width, Y height (up), Z away from the wall (Z=0 is the wall / rear face of the plate).
All values in mm. Re-generate with:  python3 -I make_holder.py
"""
import math

# --- frame (measured) ---
WINDOW = 56.0
FRAME_D = 10.0          # depth of the frame; the tray's back face sits at this height


# --- mounting plate ---
BOX_SPACING = 60.0      # flush box screws, standard
BOX_HOLE = 4.5          # round, for the usual 3.5 mm box screws
PLATE = 70.0            # must fit into the hollow of the frame (ASSUMED free inner width >= 78)
PLATE_T = 1.3           # allowed thickness under the frame (given)

# --- meter (measured) and tray ---
METER_W, METER_H, METER_D = 27.5, 66.0, 20.0
FIT = 0.4               # total clearance
TRAY_WALL = 2.4
LIP = 1.2               # lips over the front edge of the meter
FLOOR_T = 3.0           # tray floor (screws go through it)

# --- screws ---
HOLE_Y = 18.0           # screw positions y = +-18, x = 0
SCREW_HOLE_R = 1.7      # 3.4 mm through hole for M3
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
    tris = []
    x_in = (METER_W + FIT) / 2
    y_in = (METER_H + FIT) / 2
    xo, yo = x_in + TRAY_WALL, y_in + TRAY_WALL
    zf = FRAME_D + FLOOR_T                       # top of the floor
    z_lip = zf + METER_D + FIT                   # underside of the lips
    z_top = z_lip + LIP
    ph = 4.0
    patches = [(-ph, ph, sy * HOLE_Y - ph, sy * HOLE_Y + ph) for sy in (1, -1)]
    # floor with stepped screw holes: 3.4 mm through, 6.4 mm counterbore on top
    zc = zf - HEAD_DEPTH
    tris += cut_rect((-xo, xo, -yo, yo), patches, FRAME_D, zc)
    tris += cut_rect((-xo, xo, -yo, yo), patches, zc, zf)
    for sy in (1, -1):
        tris += round_hole_patch(0.0, sy * HOLE_Y, SCREW_HOLE_R, ph, FRAME_D, zc)
        tris += round_hole_patch(0.0, sy * HOLE_Y, HEAD_HOLE_R, ph, zc, zf)
    # walls: both sides full length, bottom end closed, top end open (the meter slides in from the top)
    for sx in (1, -1):
        xa, xb = sorted((sx * x_in, sx * xo))
        tris += box_tris(xa, xb, -yo, yo, zf - 0.1, z_top)
        xa, xb = sorted((sx * (x_in - LIP), sx * x_in))
        tris += box_tris(xa, xb, -yo, yo, z_lip, z_top)
    tris += box_tris(-xo, xo, -yo, -y_in, zf - 0.1, z_top)
    tris += box_tris(-x_in, x_in, -y_in, -y_in + LIP, z_lip, z_top)
    # cover plate filling the window, recessed, and the web to the tray; holes for the posts
    c, ph = COVER / 2, POST_HOLE_R + 0.5
    patches = [(-ph, ph, sy * HOLE_Y - ph, sy * HOLE_Y + ph) for sy in (1, -1)]
    zf2 = FRAME_D - COVER_RECESS                 # front face of the plate
    zr = zf2 - COVER_T
    zt = FRAME_D + 0.1
    tris += cut_rect((-c, c, -c, c), patches, zr, zf2)
    tris += cut_rect((-WEB_HALF_X, WEB_HALF_X, -c, c), patches, zf2, zt)
    for sy in (1, -1):
        tris += round_hole_patch(0.0, sy * HOLE_Y, POST_HOLE_R, ph, zr, zf2)
        tris += round_hole_patch(0.0, sy * HOLE_Y, POST_HOLE_R, ph, zf2, zt)
    return tris


if __name__ == "__main__":
    for name, tris in (("base_plate", base_plate()), ("front_piece", front_piece())):
        write_stl(f"{name}.stl", name, tris)
        xs, ys, zs = zip(*[p for t in tris for p in t])
        print(f"{name}.stl: {max(xs)-min(xs):.1f} x {max(ys)-min(ys):.1f} x {max(zs)-min(zs):.1f} mm, "
              f"{len(tris)} tris, volume {volume(tris):.0f} mm3")
