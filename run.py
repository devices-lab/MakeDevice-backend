from process import merge_layers, clear_directories

from gerbersockets import Sockets, Zones
from loader import Loader
from board import Board

from bus_router import BusRouter
from generate import generate
from process import merge_stacks, compress_directory
from consolidate import consolidate_component_files
from upload import upload_jlc, upload_euro, upload_aisler

import warnings
import sys
import debug
import firmware


# Make sure to run `source venv/bin/activate` first!
def run(file_number: str, run_from_server: bool = False) -> dict:
    print("🟢 = OK")
    print("🟡 = WARNING")
    print("🔴 = ERROR")
    print("⚪️ = DEBUG")
    print("🔵 = INFO\n")

    loader = Loader(f"./data/data_{file_number}.json", run_from_server=run_from_server)
    print("🔵 Using", f"data_{file_number}.json")

    if loader.debug:
        print("⚪️ Running in debug mode")

    # Clear out ./output and ./generated directories
    clear_directories()
    print("🟢 Cleared out `/output` and `/generated` directories")

    board = Board(loader)

    # Merge the GerberSockets layers from all individual modules
    gerbersockets_layer = merge_layers(
        board.modules, loader.gerbersockets_layer_name, board.name
    )
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
    with open("firmware/firmware.json", "w") as json_file:
        json_file.write(json)
    print("🟢 Generated MCU programming firmware JSON file")

    # TODO: for now it will be hardcoded, but would be good to identify the track/buses layers programatically
    top_layer = board.get_layer("F_Cu.gtl")
    bottom_layer = board.get_layer("B_Cu.gbl")

    left_router = BusRouter(
        board, tracks_layer=top_layer, buses_layer=bottom_layer, side="left"
    )
    left_router.route()

    right_router = BusRouter(
        board, tracks_layer=bottom_layer, buses_layer=top_layer, side="right"
    )
    right_router.route()

    generate(board)
    merge_stacks(board.modules, board.name)
    consolidate_component_files(board.modules, board.name)
    compress_directory("output")

    # "PASS" and "FAIL" substrings are checked for by test.py]
    all = sockets.get_socket_count()
    connected = board.connected_sockets_count

    failed = False
    if (all - connected) == 0:
        print(f"✅ PASS: All {connected} GerberSockets routed successfully")
    else:
        failed = True
        print(
            f"❌ FAIL: GerberSockets routing incomplete for {all - connected} socket. {connected}/{all} completed"
        )

    if debug.do_video:
        debug.video(name=file_number)

    # Generate the firmware files for microbit/rp2040 brain to flash
    # all virtual modules
    firmware.run()

    # Upload the files to JLCPCB and Eurocircuits
    print("🟢 Uploading files to fabrication services")
    order_urls = {
        "jlc": upload_jlc(),
        "euro": upload_euro(),
        "aisler": upload_aisler(),
    }

    return {
        "failed": failed,
        "order_urls": order_urls,
    }


if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if len(sys.argv) > 1:
            if len(sys.argv) > 2:
                if sys.argv[2] == "video":
                    debug.do_video = True
            run(sys.argv[1])  # e.g 'python3 run.py 5-flip'
        else:
            run("5")
