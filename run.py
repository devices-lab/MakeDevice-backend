from process import merge_layers
import os
import json
import re

from gerbersockets import Sockets, Zones
from loader import Loader
from board import Board

from bus_router import BusRouter
from generate import generate
from process import merge_stacks, compress_directory
from consolidate import consolidate_component_files

import firmware

from pathlib import Path
import thread_context


ALLOWED_ISSUE_PREFIXES = (
    "MODULE_TOO_CLOSE_TO_BOARD_EDGE",
    "MODULE_TOO_CLOSE_TO_OTHER_MODULE",
    "MODULE_OVERLAPPING_OTHER_MODULE",
    "MODULE_OVERHANGING_BOARD_EDGE",
    "ROUTING_STUCK_STATE_REVISIT_LIMIT",
    "ROUTING_JOB_ABANDONED_KEEPALIVE_EXPIRED",
    "ROUTING_JOB_ABANDONED_MAX_ROUTING_IMAGES",
    "ROUTING_SOCKET_TO_BUS_PATH_NOT_FOUND",
)


def _issues_file_path() -> Path:
    return Path(thread_context.job_folder) / "issues.json"


def _read_issue_payload() -> dict:
    payload = {"issues": []}
    issues_file = _issues_file_path()
    if not issues_file.exists():
        return payload

    try:
        with open(issues_file, "r") as file:
            content = json.load(file)
        if isinstance(content, dict):
            payload["issues"] = content.get("issues", []) if isinstance(content.get("issues", []), list) else []
    except Exception:
        pass

    return payload


def _append_issue(message: str) -> None:
    if not message:
        return

    if not message.startswith(ALLOWED_ISSUE_PREFIXES):
        return

    if ("moduleId=" not in message and
        "moduleIds=" not in message and
        "moduleIdsAll=" not in message):
        board = getattr(thread_context, "board", None)
        if board is not None and getattr(board, "modules", None):
            ids = _all_module_ids(board)
            short_ids = _all_module_ids_short(board)
            message = (
                f"{message} "
                f"moduleIdsAll=[{','.join(ids)}] "
                f"moduleIdsAllShort=[{','.join(short_ids)}]"
            )

    payload = _read_issue_payload()
    if message not in payload["issues"]:
        payload["issues"].append(message)

    with open(_issues_file_path(), "w") as file:
        json.dump(payload, file)


def _record_failure(message: str) -> None:
    if not message:
        return

    error_file = Path(thread_context.job_folder) / "error.txt"
    with open(error_file, "w") as file:
        file.write(message)

    _append_issue(message)


def _normalize_position_warning(warning: str) -> str:
    return warning.strip()


def _sync_position_warnings(board: Board) -> None:
    for warning in board.position_warnings:
        message = _normalize_position_warning(warning)
        _append_issue(message)


def _read_router_error() -> str:
    error_file = Path(thread_context.job_folder) / "error.txt"
    if not error_file.exists():
        return ""
    try:
        with open(error_file, "r") as file:
            return file.read().strip()
    except Exception:
        return ""


def _all_module_ids(board: Board) -> list[str]:
    module_ids: list[str] = []
    for module in board.modules:
        module_id = module.module_id if getattr(module, "module_id", None) else "unknown"
        module_ids.append(module_id)
    return module_ids


def _all_module_ids_short(board: Board) -> list[str]:
    return [module_id[:4] if module_id != "unknown" else "unkn" for module_id in _all_module_ids(board)]


def _issue_with_all_modules(code: str, board: Board, extra_fields: str = "") -> str:
    ids = _all_module_ids(board)
    short_ids = _all_module_ids_short(board)
    base = (
        f"{code} "
        f"moduleIdsAll=[{','.join(ids)}] "
        f"moduleIdsAllShort=[{','.join(short_ids)}]"
    )
    return f"{base} {extra_fields}".strip()

# Make sure to run `source venv/bin/activate` first!
def run(job_id: str, job_folder: Path) -> dict:
    
    # TODO: would be nice to have error reporting more centrally defined
    print("🟢 = OK")
    print("🟠 = WARNING")
    print("🔴 = ERROR")
    print("⚪️ = DEBUG")
    print("🔵 = INFO\n")

    # NOTE: job_id will always be a fresh job, no need to clear old files
    # Only allow calling run() from within a thread, with a job_id and job_folder

    # NOTE: Set thread context variables, instead of using global variables
    # DO NOT USE global variables in ANY code, since those are shared between all threads!
    thread_context.job_id = job_id
    thread_context.job_folder = Path(job_folder)

    # Initialize job-level user-facing issue tracking
    with open(_issues_file_path(), "w") as file:
        json.dump({"issues": []}, file)

    # TODO: Change the rest of the code to reflect these decisions
    if (not hasattr(thread_context, "job_folder")):
        raise RuntimeError("run() must be called from within a thread")
    if (job_id is None or job_folder is None):
        raise NotImplementedError("run() can't be called without job_id and job_folder parameters")

    # If a specific data file path is provided, use it
    project_file_path = thread_context.job_folder / "output/project.MakeDevice"
    loader = Loader(project_file_path)
    if os.environ.get("MAKEDEVICE_DEBUG_VISUAL", "0") == "1":
        loader.run_from_server = False
    
    print("🔵 Using", project_file_path.name)
    
    # TODO: Must somehow append the job_folder to every single file path used throughout the run
    
    board = Board(loader)
    thread_context.board = board

    # Merge the GerberSockets layers from all individual modules
    gerbersockets_layer = merge_layers(
        board.modules, loader.gerbersockets_layer_name, board.name
    )
    
    if gerbersockets_layer is None:
        print("🔴 No GerberSockets layer found in any module")
        _record_failure(_issue_with_all_modules("ROUTING_LAYER_MISSING_GERBERSOCKETS", board))
        return {"failed": True}
    
    print("🟢 Merged", loader.gerbersockets_layer_name, "layers")

    # Get the locations of the sockets
    sockets = Sockets(loader, gerbersockets_layer)
    if sockets.get_socket_count() == 0:
        print("🔴 No sockets found")
        _record_failure(_issue_with_all_modules("ROUTING_NO_SOCKETS_FOUND", board))
        return {"failed": True}
    else:
        board.add_sockets(sockets)
        print(
            "🟢 Found",
            sockets.get_socket_count(),
            "sockets and added them to the board",
        )

    # Get the keep out zones
    zones = Zones(loader, gerbersockets_layer)
    if zones.get_zone_count() == 0:
        print("🔴 No keep-out zones found, and added them to the board")
        _record_failure(_issue_with_all_modules("PLACEMENT_NO_KEEP_OUT_ZONES", board))
        return {"failed": True}
    else:
        board.add_zones(zones)
        _sync_position_warnings(board)
        print(
            "🟢 Found",
            zones.get_zone_count(),
            "keep-out zones and added them to the board",
        )

    # Get the module names and the net names of their sockets
    module_nets = board.get_module_nets()
    for module in module_nets:
        print(f"🔵 Module '{module.name}' has the following nets:")
        str_nets = [str(net) for net in module_nets[module]]
        if len(str_nets) == 0:
            print("    No nets")
        else:
            print(f"    {', '.join(str_nets)}")

    # Generate JSON containing module/net mappings needed for MCU programming
    programming_json = board.get_programming_json()
    with open(thread_context.job_folder / "firmware.json", "w") as json_file:
        json_file.write(programming_json)
    print("🟢 Generated MCU programming firmware JSON file")

    # TODO: for now it will be hardcoded, but would be good to identify the track/buses layers programatically
    top_layer = board.get_layer("F_Cu.gtl")
    bottom_layer = board.get_layer("B_Cu.gbl")

    if top_layer and bottom_layer is not None:
        left_router = BusRouter(
            board, tracks_layer=top_layer, buses_layer=bottom_layer, side="left"
        )
        left_router.route()
        left_route_error = _read_router_error()
        if left_route_error:
            _append_issue(left_route_error)
            return {"failed": True}

        right_router = BusRouter(
            board, tracks_layer=bottom_layer, buses_layer=top_layer, side="right"
        )
        right_router.route()
        right_route_error = _read_router_error()
        if right_route_error:
            _append_issue(right_route_error)
            return {"failed": True}

        _sync_position_warnings(board)

        # Save final front.svg / back.svg
        # Saving routing SVGs is disabled to save disk space.
        # try:
        #     from debug import save_front_back_svgs
        #     routing_imgs_folder = Path(thread_context.job_folder) / "routing_imgs"
        #     save_front_back_svgs(board, routing_imgs_folder, router_list=[left_router, right_router])
        # except Exception as e:
        #     print(f"🔴 Error saving final SVGs: {e}")
    else:   
        print("🔴 Could not find both top and bottom layers for routing")
        _record_failure(_issue_with_all_modules("ROUTING_LAYERS_MISSING_TOP_OR_BOTTOM", board))
        return {"failed": True}

    generate(board)
    merge_stacks(board.modules, board.name)
    consolidate_component_files(board.modules, board.name)

    # Count only sockets that were assigned to modules (ignore unassigned sockets)
    module_nets = board.get_module_nets()
    all = sum(len(module_nets[module]) for module in module_nets)
    connected = board.connected_sockets_count

    if (all - connected) == 0:
        print(f"🟢 All {connected} GerberSockets routed successfully")
    else:
        failed_count = all - connected
        print(f"🔴 GerberSockets routing incomplete for {failed_count} socket. {connected}/{all} completed")
        _record_failure(
            _issue_with_all_modules(
                "ROUTING_UNCONNECTED_SOCKETS",
                board,
                f"failedSockets={failed_count} connectedSockets={connected} totalSockets={all}",
            )
        )
        return {"failed": True}

    # Generate the firmware files for microbit/RP2040 module to flash all Jacdac-based SMT32 virtual modules
    try:
        firmware.run()
        print("🟢 Generated firmware files")
        compress_directory(thread_context.job_folder / "output")
    except BaseException as e:
        print("🔴 Failed to generate firmware files:", e)
        _append_issue(_issue_with_all_modules("FIRMWARE_GENERATION_FAILED", board, f"error={str(e)}"))
        compress_directory(thread_context.job_folder / "output")

    # Write to a text fail indicating zip ready
    with open(thread_context.job_folder / "zip_ready.txt", 'w') as file:
        file.write("ready")

    print("🟢 Finished job ID: ", thread_context.job_id)

    return {
        "failed": False
    }
