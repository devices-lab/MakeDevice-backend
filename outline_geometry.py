"""
Geometry helpers for custom board outlines that arrive from the frontend
project JSON. Mirrors `src/state/outlineGeometry.ts` in the frontend so the
generated Edge_Cuts gerber matches what the user drew in the 3D editor.

Outline node format (from pcbOptions.outline):
    {
        "x":           number, mm, board-local, y-up, centred at (0, 0)
        "y":           number
        "r":           optional fillet radius applied at this corner (mm).
                       0/absent = sharp.
        "bulgeAfter":  optional signed DXF-style bulge for the edge from
                       this node to the next (= tan(includedAngle / 4)).
                       Positive bulges LEFT of the directed edge (CCW).
                       0/absent = straight.
    }
"""

from dataclasses import dataclass
import math
from typing import List, Optional, Tuple

EPS = 1e-6


@dataclass(frozen=True)
class Vec2:
    x: float
    y: float

    def as_tuple(self) -> Tuple[float, float]:
        return (self.x, self.y)


@dataclass(frozen=True)
class Arc:
    center: Vec2
    radius: float
    start_angle: float  # radians
    end_angle: float    # radians
    ccw: bool           # True when sweep goes CCW from start to end


@dataclass(frozen=True)
class Fillet:
    entry: Vec2
    exit: Vec2
    center: Vec2
    radius: float
    start_angle: float
    end_angle: float
    ccw: bool


def arc_from_bulge(a: Vec2, b: Vec2, bulge: float) -> Optional[Arc]:
    if not bulge or abs(bulge) < 1e-9:
        return None
    dx = b.x - a.x
    dy = b.y - a.y
    chord = math.hypot(dx, dy)
    if chord < EPS:
        return None

    radius = (chord * (1 + bulge * bulge)) / (4 * abs(bulge))
    apothem = radius - (abs(bulge) * chord) / 2

    mid_x = (a.x + b.x) / 2
    mid_y = (a.y + b.y) / 2
    nx = -dy / chord
    ny = dx / chord
    sign = 1 if bulge > 0 else -1
    cx = mid_x + nx * apothem * sign
    cy = mid_y + ny * apothem * sign

    start_angle = math.atan2(a.y - cy, a.x - cx)
    end_angle = math.atan2(b.y - cy, b.x - cx)

    return Arc(Vec2(cx, cy), radius, start_angle, end_angle, ccw=bulge > 0)


def fillet_at_corner(p: Vec2, c: Vec2, n: Vec2, requested_radius: float) -> Optional[Fillet]:
    if not requested_radius or requested_radius <= EPS:
        return None
    v1x, v1y = p.x - c.x, p.y - c.y
    v2x, v2y = n.x - c.x, n.y - c.y
    len1 = math.hypot(v1x, v1y)
    len2 = math.hypot(v2x, v2y)
    if len1 < EPS or len2 < EPS:
        return None
    u1x, u1y = v1x / len1, v1y / len1
    u2x, u2y = v2x / len2, v2y / len2
    cos_theta = max(-1.0, min(1.0, u1x * u2x + u1y * u2y))
    half_angle = math.acos(cos_theta) / 2
    if half_angle < EPS or abs(math.pi - 2 * half_angle) < EPS:
        return None
    tan_half = math.tan(half_angle)
    max_dist_along_edge = min(len1, len2) / 2
    dist_along_edge = min(requested_radius / tan_half, max_dist_along_edge)
    radius = dist_along_edge * tan_half

    entry = Vec2(c.x + u1x * dist_along_edge, c.y + u1y * dist_along_edge)
    exit_ = Vec2(c.x + u2x * dist_along_edge, c.y + u2y * dist_along_edge)

    bx, by = u1x + u2x, u1y + u2y
    b_len = math.hypot(bx, by)
    if b_len < EPS:
        return None
    dist_to_center = radius / math.sin(half_angle)
    center = Vec2(c.x + (bx / b_len) * dist_to_center, c.y + (by / b_len) * dist_to_center)

    start_angle = math.atan2(entry.y - center.y, entry.x - center.x)
    end_angle = math.atan2(exit_.y - center.y, exit_.x - center.x)
    cross = u1x * u2y - u1y * u2x
    ccw = cross < 0

    return Fillet(entry, exit_, center, radius, start_angle, end_angle, ccw)


@dataclass(frozen=True)
class OutlineNode:
    x: float
    y: float
    r: float = 0.0
    bulge_after: float = 0.0


def parse_outline(raw: list, offset_x: float = 0.0, offset_y: float = 0.0) -> List[OutlineNode]:
    """
    Convert the frontend's raw outline list into normalised OutlineNode
    objects, converting the frontend y-up coordinates into the backend's
    y-inverted Gerber frame and applying an absolute coordinate offset (the
    gerber origin may differ from the project's centred origin).
    """
    out: List[OutlineNode] = []
    for v in raw:
        if not isinstance(v, dict):
            continue
        try:
            x = float(v.get("x"))
            y = float(v.get("y"))
        except (TypeError, ValueError):
            continue
        r_raw = v.get("r", 0)
        b_raw = v.get("bulgeAfter", 0)
        try:
            r = max(0.0, float(r_raw)) if r_raw is not None else 0.0
        except (TypeError, ValueError):
            r = 0.0
        try:
            b = float(b_raw) if b_raw is not None else 0.0
        except (TypeError, ValueError):
            b = 0.0
        # Module positions are inverted at the backend boundary, while routed
        # copper/vias supplied by frontend routers already arrive in that
        # frame. Mirror only the custom board outline here so Edge_Cuts lines
        # up with the otherwise-correct board contents. Mirroring reverses
        # DXF bulge handedness, so arc edges need the sign flipped too.
        out.append(OutlineNode(x + offset_x, offset_y - y, r, -b))
    return out


def build_outline_path_segments(nodes: List[OutlineNode]):
    """
    Walk the outline and yield drawing instructions ready to feed into
    gerber_writer.Path. Each yielded tuple is one of:

        ("move",   (x, y))
        ("line",   (x, y))
        ("arc",    (end_x, end_y), (center_x, center_y), direction)
                   direction = '+' for CCW, '-' for CW

    The first instruction is always a "move".
    """
    n = len(nodes)
    if n < 3:
        return

    fillets: List[Optional[Fillet]] = []
    for i in range(n):
        prev_n = nodes[(i - 1) % n]
        cur = nodes[i]
        nxt = nodes[(i + 1) % n]
        fillets.append(fillet_at_corner(
            Vec2(prev_n.x, prev_n.y),
            Vec2(cur.x, cur.y),
            Vec2(nxt.x, nxt.y),
            cur.r,
        ))

    first_fillet = fillets[0]
    start = first_fillet.entry if first_fillet else Vec2(nodes[0].x, nodes[0].y)
    yield ("move", start.as_tuple())

    for i in range(n):
        cur = nodes[i]
        nxt = nodes[(i + 1) % n]
        fillet = fillets[i]
        if fillet:
            yield (
                "arc",
                fillet.exit.as_tuple(),
                fillet.center.as_tuple(),
                "+" if fillet.ccw else "-",
            )

        edge_from = fillet.exit if fillet else Vec2(cur.x, cur.y)
        end_fillet = fillets[(i + 1) % n]
        edge_to = end_fillet.entry if end_fillet else Vec2(nxt.x, nxt.y)

        arc = arc_from_bulge(edge_from, edge_to, cur.bulge_after)
        if arc:
            yield (
                "arc",
                (edge_to.x, edge_to.y),
                arc.center.as_tuple(),
                "+" if arc.ccw else "-",
            )
        else:
            yield ("line", edge_to.as_tuple())
