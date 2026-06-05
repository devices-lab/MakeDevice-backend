"""
Artifact-only run path.

The backend's `run()` (run.py) does board setup → routing → artifact generation.
With frontend routers, the routing has already happened in the browser. This
module accepts a route (segments + vias in world coords) supplied by the
frontend, injects it onto the board, and runs the same artifact generation
pipeline (gerber, drill, BOM/CPL, firmware, zip) — skipping the BusRouter.

Same job-folder convention as run.py, so /routingProgress and /pcbArtifact
serve this path unchanged.
"""

import json
from pathlib import Path

from process import merge_layers, merge_stacks, compress_directory
from gerbersockets import Sockets, Zones
from loader import Loader
from board import Board
from objects import Point, Segment
from generate import generate
from consolidate import consolidate_component_files
import firmware
import thread_context


def run_from_route(job_id: str, job_folder: Path, route_data: dict) -> None:
    thread_context.job_id = job_id
    thread_context.job_folder = Path(job_folder)

    with open(thread_context.job_folder / "issues.json", "w") as f:
        json.dump({"issues": []}, f)

    project_file_path = thread_context.job_folder / "output/project.MakeDevice"
    loader = Loader(project_file_path)
    print("🔵 Using", project_file_path.name)

    board = Board(loader)
    thread_context.board = board

    # Merge per-module GerberSockets layers so socket/zone info matches the
    # frontend's view — firmware.json needs this and so does the GerberSockets
    # output in the zip.
    gerbersockets_layer = merge_layers(
        board.modules, loader.gerbersockets_layer_name, board.name
    )
    if gerbersockets_layer is not None:
        sockets = Sockets(loader, gerbersockets_layer)
        if sockets.get_socket_count() > 0:
            board.add_sockets(sockets)
        zones = Zones(loader, gerbersockets_layer)
        if zones.get_zone_count() > 0:
            board.add_zones(zones)

    try:
        programming_json = board.get_programming_json()
        with open(thread_context.job_folder / "firmware.json", "w") as f:
            f.write(programming_json)
        print("🟢 Generated firmware JSON")
    except Exception as e:
        print(f"🟠 Could not generate firmware JSON: {e}")

    _apply_route(board, route_data)

    try:
        generate(board)
        merge_stacks(board.modules, board.name)
        consolidate_component_files(board.modules, board.name)
    except Exception as e:
        error_file = thread_context.job_folder / "error.txt"
        with open(error_file, "w") as f:
            f.write(f"ARTIFACT_GENERATION_FAILED error={e}")
        print(f"🔴 Artifact generation failed: {e}")

    try:
        firmware.run()
        print("🟢 Generated firmware files")
    except BaseException as e:
        print("🔴 Failed to generate firmware files:", e)

    compress_directory(thread_context.job_folder / "output")

    with open(thread_context.job_folder / "zip_ready.txt", "w") as f:
        f.write("ready")

    print("🟢 Finished artifact-only job ID:", thread_context.job_id)


def _apply_route(board: Board, route_data: dict) -> None:
    segments = route_data.get("segments") or []
    vias = route_data.get("vias") or []

    added = 0
    skipped = 0
    for seg in segments:
        layer_name = seg.get("layer")
        layer = board.get_layer(layer_name)
        if layer is None:
            skipped += 1
            continue
        start = Point(float(seg["startX"]), float(seg["startY"]))
        end = Point(float(seg["endX"]), float(seg["endY"]))
        width = float(seg.get("width") or board.loader.track_width)
        net = seg.get("net")
        layer.add_segment(Segment(start, end, layer=layer_name, width=width, net=net))
        added += 1
    msg = f"🟢 Added {added} frontend segments to board layers"
    if skipped:
        msg += f" (skipped {skipped} with unknown layer)"
    print(msg)

    for via in vias:
        point = Point(float(via["x"]), float(via["y"]))
        for layer in board.layers:
            layer.add_annular_ring(point)
        board.add_drill_hole(point)
    print(f"🟢 Added {len(vias)} frontend vias")

    if "totalBusesWidth" in route_data:
        try:
            board.total_buses_width = float(route_data["totalBusesWidth"])
        except (TypeError, ValueError):
            pass
    if "connectedSocketsCount" in route_data:
        try:
            board.connected_sockets_count = int(route_data["connectedSocketsCount"])
        except (TypeError, ValueError):
            pass
