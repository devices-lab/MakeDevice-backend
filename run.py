from process import merge_layers

from gerbersockets import Sockets, Zones
from loader import Loader
from board import Board

from bus_router import BusRouter
from generate import generate
from process import merge_stacks, compress_directory
from consolidate import consolidate_component_files

import warnings
import firmware

from pathlib import Path
from thread_context import thread_context

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
    # !!!!!!!================DO NOT USE global variables in ANY code, since those are shared between all threads=================!!!!!!
    thread_context.job_id = job_id
    thread_context.job_folder = Path(job_folder)
    thread_context.frame_index = 0

    # TODO: Change the rest of the code to reflect these decisions
    if (not hasattr(thread_context, "job_folder")):
        raise RuntimeError("run() must be called from within a thread")
    if (job_id is None or job_folder is None):
        raise NotImplementedError("run() can't be called without job_id and job_folder parameters")

    # If a specific data file path is provided, use it
    project_file_path = thread_context.job_folder / "output/project.MakeDevice"
    loader = Loader(project_file_path)
    
    print("🔵 Using", project_file_path.name)
    
    # TODO: Must somehow append the job_folder to every single file path used throughout the run
    
    board = Board(loader)

    # Merge the GerberSockets layers from all individual modules
    gerbersockets_layer = merge_layers(
        board.modules, loader.gerbersockets_layer_name, board.name
    )
    
    if gerbersockets_layer is None:
        print("🔴 No GerberSockets layer found in any module")
        return {"failed": True}
    
    print("🟢 Merged", loader.gerbersockets_layer_name, "layers")

    # Get the locations of the sockets
    sockets = Sockets(loader, gerbersockets_layer)
    if sockets.get_socket_count() == 0:
        print("🔴 No sockets found")
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
        return {"failed": True}
    else:
        board.add_zones(zones)
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
    json = board.get_programming_json()
    with open(thread_context.job_folder / "firmware.json", "w") as json_file:
        json_file.write(json)
    print("🟢 Generated MCU programming firmware JSON file")

    # TODO: for now it will be hardcoded, but would be good to identify the track/buses layers programatically
    top_layer = board.get_layer("F_Cu.gtl")
    bottom_layer = board.get_layer("B_Cu.gbl")

    if top_layer and bottom_layer is not None:
        left_router = BusRouter(
            board, tracks_layer=top_layer, buses_layer=bottom_layer, side="left"
        )
        left_router.route()

        right_router = BusRouter(
            board, tracks_layer=bottom_layer, buses_layer=top_layer, side="right"
        )
        right_router.route()
    else:   
        print("🔴 Could not find both top and bottom layers for routing")
        return {"failed": True}

    # Suppress warnings from Gerbonara during generation
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        generate(board)
        merge_stacks(board.modules, board.name)
        consolidate_component_files(board.modules, board.name)

    all = sockets.get_socket_count()
    connected = board.connected_sockets_count

    if (all - connected) == 0:
        print(f"🟢 All {connected} GerberSockets routed successfully")
    else:
        print(f"🔴 GerberSockets routing incomplete for {all - connected} socket. {connected}/{all} completed")
        return {"failed": True}

    # Generate the firmware files for microbit/RP2040 module to flash all Jacdac-based SMT32 virtual modules
    try:
        firmware.run()
        print("🟢 Generated firmware files")
        compress_directory(thread_context.job_folder / "output")
    except Exception as e:
        print("🔴 Failed to generate firmware files:", e)
        compress_directory(thread_context.job_folder / "output")

    print("🟢 Finished job ID: ", thread_context.job_id)

    return {
        "failed": False
    }
