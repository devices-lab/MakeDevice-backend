"""
Read-only parity extractor used by the frontend bus_router migration harness.

Loads a project.MakeDevice file, runs the same routing pipeline as run.py
(merge GerberSockets, build Board, BusRouter left then right) and dumps a
canonical JSON snapshot of the routing state to stdout.

Output schema (stable, kept in sync with frontend benchmarking/runFrontend.ts):

  {
    "config": {
      "width": float, "height": float, "resolution": float,
      "trackWidth": float, "busWidth": float, "busSpacing": float,
      "edgeClearance": float, "roundedCornerRadius": float,
      "moduleMargin": float,
      "allowDiagonalTraces": bool, "allowOverlap": bool,
      "algorithm": str
    },
    "issues": [str, ...],
    "errorMessage": str | null,
    "left": {
        "tracksLayer": str, "busesLayer": str,
        "totalBusesWidth": float,
        "busSegments": { net: { "x": float, "yMin": float, "yMax": float } },
        "pathsByNet":  { net: [ [[col, row, layer], ...], ... ] },
        "viasByNet":   { net: [[col, row], ...] }
    },
    "right": { same shape },
    "metrics": {
        "connectedSocketsCount": int,
        "totalSockets": int,
        "viaCount": int,
        "copperLengthMm": float
    }
  }

Run from inside the backend venv:
    source venv/bin/activate
    python extract_router_state.py path/to/project.MakeDevice path/to/out.json
"""

import json
import math
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Force the matplotlib visualiser OFF — we want headless runs only.
os.environ["MAKEDEVICE_DEBUG_VISUAL"] = "0"

import thread_context
from loader import Loader
from board import Board
from gerbersockets import Sockets, Zones
from process import merge_layers
from bus_router import BusRouter


def _segment_y_extents(seg):
    yMin = min(seg.start.y, seg.end.y)
    yMax = max(seg.start.y, seg.end.y)
    return yMin, yMax


def _bus_segments_dump(bus_segments):
    out = {}
    for net, seg in bus_segments.items():
        yMin, yMax = _segment_y_extents(seg)
        out[net] = {"x": seg.start.x, "yMin": yMin, "yMax": yMax}
    return out


def _paths_dump(paths_indices):
    return {net: [list(map(list, p)) for p in paths] for net, paths in paths_indices.items()}


def _vias_dump(vias_indices):
    return {net: [list(v) for v in vias] for net, vias in vias_indices.items()}


def _copper_length_mm(paths_indices, resolution):
    total = 0.0
    for paths in paths_indices.values():
        for path in paths:
            for i in range(1, len(path)):
                dx = (path[i][0] - path[i - 1][0]) * resolution
                dy = (path[i][1] - path[i - 1][1]) * resolution
                total += math.hypot(dx, dy)
    return total


def _via_count(vias_indices):
    return sum(len(v) for v in vias_indices.values())


def _make_router_state(router):
    return {
        "tracksLayer": router.tracks_layer.name,
        "busesLayer": router.buses_layer.name,
        "totalBusesWidth": router.board.total_buses_width,
        "busSegments": _bus_segments_dump(router.bus_segments),
        "pathsByNet": _paths_dump(router.paths_indices),
        "viasByNet": _vias_dump(router.vias_indices),
    }


def _modules_dump(modules):
    return [
        {
            "name": m.name,
            "version": m.version,
            "moduleId": m.module_id,
            "rotation": m.rotation,
            # NB: backend Module.__init__ inverts y at construction; this is the
            # POST-inversion value. The frontend engine expects post-inversion
            # too, so just pass it through unchanged.
            "position": {"x": m.position.x, "y": m.position.y},
        }
        for m in modules
    ]


def _sockets_dump(sockets):
    return {net: [list(p) for p in pos] for net, pos in sockets.socket_locations.items()}


def _zones_dump(zones):
    return [[list(corner) for corner in z] for z in zones.zone_rectangles]


def _layers_dump(board):
    return [
        {
            "name": layer.name,
            "fill": bool(layer.fill),
            "attributes": layer.attributes or "",
            "nets": list(layer.nets),
        }
        for layer in board.layers
    ]


def _empty_side(tracks, buses):
    return {
        "tracksLayer": tracks,
        "busesLayer": buses,
        "totalBusesWidth": 0.0,
        "busSegments": {},
        "pathsByNet": {},
        "viasByNet": {},
    }


class _Silencer:
    """Redirect Python sys.stdout/sys.stderr AND OS fds 1/2 to /dev/null."""

    def __enter__(self):
        self._devnull = open(os.devnull, "w")
        self._saved_stdout = sys.stdout
        self._saved_stderr = sys.stderr
        sys.stdout = self._devnull
        sys.stderr = self._devnull
        self._saved_fd1 = os.dup(1)
        self._saved_fd2 = os.dup(2)
        os.dup2(self._devnull.fileno(), 1)
        os.dup2(self._devnull.fileno(), 2)
        return self

    def __exit__(self, *_):
        sys.stdout = self._saved_stdout
        sys.stderr = self._saved_stderr
        os.dup2(self._saved_fd1, 1)
        os.dup2(self._saved_fd2, 2)
        os.close(self._saved_fd1)
        os.close(self._saved_fd2)
        self._devnull.close()


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("usage: extract_router_state.py <project.MakeDevice> <out.json>\n")
        return 2

    project_path = Path(argv[1]).resolve()
    out_path = Path(argv[2]).resolve()
    if not project_path.is_file():
        sys.stderr.write(f"not a file: {project_path}\n")
        return 2

    # Stage a fresh job folder so the backend's ensure_directories logic and
    # any error.txt writes do not pollute the caller's tree.
    work_dir = Path(tempfile.mkdtemp(prefix="extract_router_"))
    silencer = _Silencer()
    silencer.__enter__()
    try:
        output_dir = work_dir / "output"
        output_dir.mkdir()
        staged = output_dir / "project.MakeDevice"
        shutil.copy(project_path, staged)

        thread_context.job_id = "extract"
        thread_context.job_folder = work_dir

        # Stub keepalive so any incidental check passes.
        (work_dir / "keepalive_time").write_text("ok")

        loader = Loader(staged)
        loader.run_from_server = False  # disable progress.txt / keepalive abort
        board = Board(loader)
        thread_context.board = board

        gerbersockets_layer = merge_layers(
            board.modules, loader.gerbersockets_layer_name, board.name
        )

        result = {
            "config": {
                "width": board.width,
                "height": board.height,
                "resolution": board.resolution,
                "trackWidth": loader.track_width,
                "busWidth": loader.bus_width,
                "busSpacing": loader.bus_spacing,
                "edgeClearance": loader.edge_clearance,
                "roundedCornerRadius": loader.rounded_corner_radius,
                "moduleMargin": loader.module_margin,
                "allowDiagonalTraces": loader.allow_diagonal_traces,
                "allowOverlap": loader.allow_overlap,
                "algorithm": loader.algorithm,
            },
            "issues": [],
            "errorMessage": None,
            "left": _empty_side("F_Cu.gtl", "B_Cu.gbl"),
            "right": _empty_side("B_Cu.gbl", "F_Cu.gtl"),
        }

        if gerbersockets_layer is None:
            result["errorMessage"] = "ROUTING_LAYER_MISSING_GERBERSOCKETS"
            out_path.write_text(json.dumps(result))
            return 0

        sockets = Sockets(loader, gerbersockets_layer)
        if sockets.get_socket_count() == 0:
            result["errorMessage"] = "ROUTING_NO_SOCKETS_FOUND"
            out_path.write_text(json.dumps(result))
            return 0
        board.add_sockets(sockets)

        zones = Zones(loader, gerbersockets_layer)
        if zones.get_zone_count() == 0:
            result["errorMessage"] = "PLACEMENT_NO_KEEP_OUT_ZONES"
            out_path.write_text(json.dumps(result))
            return 0

        # Snapshot RAW module zones BEFORE board.add_zones() inserts corner
        # zones. The frontend engine inserts its own corner zones, so feeding
        # post-corner zones would double-add them.
        raw_zones_dump = _zones_dump(zones)

        board.add_zones(zones)

        for warning in board.position_warnings:
            result["issues"].append(warning)

        # Snapshot the inputs the frontend engine needs to be fed identically.
        result["inputs"] = {
            "modules": _modules_dump(board.modules),
            "layers": _layers_dump(board),
            "sockets": _sockets_dump(board.sockets),
            "zones": raw_zones_dump,
        }

        top_layer = board.get_layer("F_Cu.gtl")
        bottom_layer = board.get_layer("B_Cu.gbl")
        if not top_layer or not bottom_layer:
            result["errorMessage"] = "ROUTING_LAYERS_MISSING_TOP_OR_BOTTOM"
            out_path.write_text(json.dumps(result))
            return 0

        left_router = BusRouter(board, tracks_layer=top_layer, buses_layer=bottom_layer, side="left")
        left_router.route()
        # error.txt is the backend's failure channel for the router.
        error_file = work_dir / "error.txt"
        if error_file.exists():
            result["errorMessage"] = error_file.read_text().strip()
            result["issues"].append(result["errorMessage"])
            result["left"] = _make_router_state(left_router)
            out_path.write_text(json.dumps(result))
            return 0
        result["left"] = _make_router_state(left_router)

        right_router = BusRouter(board, tracks_layer=bottom_layer, buses_layer=top_layer, side="right")
        right_router.route()
        if error_file.exists():
            result["errorMessage"] = error_file.read_text().strip()
            result["issues"].append(result["errorMessage"])
        result["right"] = _make_router_state(right_router)

        all_paths = {}
        for n, ps in left_router.paths_indices.items():
            all_paths.setdefault(n, []).extend(ps)
        for n, ps in right_router.paths_indices.items():
            all_paths.setdefault(n, []).extend(ps)
        all_vias = {}
        for n, vs in left_router.vias_indices.items():
            all_vias.setdefault(n, []).extend(vs)
        for n, vs in right_router.vias_indices.items():
            all_vias.setdefault(n, []).extend(vs)

        result["metrics"] = {
            "connectedSocketsCount": board.connected_sockets_count,
            "totalSockets": sockets.get_socket_count(),
            "viaCount": _via_count(all_vias),
            "copperLengthMm": _copper_length_mm(all_paths, board.resolution),
        }

        out_path.write_text(json.dumps(result))
        return 0
    finally:
        silencer.__exit__(None, None, None)
        shutil.rmtree(work_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
