from process import merge_layers, clear_directories

from gerbersockets import Sockets, Zones
from loader import Loader
from board import Board

from bus_router import BusRouter
from generate import generate
from process import merge_stacks, compress_directory
from consolidate import consolidate_component_files

import warnings
import sys
import debug

def run(file_number: str, run_from_server: bool = False) -> bool:
    print("🟢 = OK")
    print("🟡 = WARNING")
    print("🔴 = ERROR")
    print("⚪️ = DEBUG")
    print("🔵 = INFO\n")
    
    loader = Loader(f"./test_data/data_{file_number}.json", run_from_server=run_from_server)
    print("🔵 Using", f"data_{file_number}.json")
    
    if loader.debug:
        print("⚪️ Running in debug mode")

    # Clear out ./output and ./generated directories
    clear_directories()
    print("🟢 Cleared out `/output` and `/generated` directories")
    
    board = Board(loader)
    
    # Merge the GerberSockets layers from all individual modules
    gerbersockets_layer = merge_layers(board.modules, loader.gerbersockets_layer_name, board.name)
    print("🟢 Merged", loader.gerbersockets_layer_name, "layers")

    # Get the locations of the sockets
    sockets = Sockets(loader, gerbersockets_layer)
    if sockets.get_socket_count() == 0:
        print("🔴 No sockets found")
        return True
    else: 
        board.add_sockets(sockets)
        print("🟢 Found", sockets.get_socket_count(), "sockets and added them to the board")
    
    
    # Get the keep out zones 
    zones = Zones(loader, gerbersockets_layer)
    if zones.get_zone_count() == 0:
        print("🔴 No keep-out zones found, and added them to the board")
        return True
    else:
        board.add_zones(zones)
        print("🟢 Found", zones.get_zone_count(), "keep-out zones and added them to the board")
            
    # TODO: for now it will be hardcoded, but would be good to identify the track/buses layers programatically
    top_layer = board.get_layer("F_Cu.gtl")
    bottom_layer = board.get_layer("B_Cu.gbl")
    
    left_router = BusRouter(board, tracks_layer=top_layer, buses_layer=bottom_layer, side="left")
    left_router.route()
    
    right_router = BusRouter(board, tracks_layer=bottom_layer, buses_layer=top_layer, side="right")
    right_router.route()    

    generate(board)
    merge_stacks(board.modules, board.name)
    consolidate_component_files(board.modules, board.name)
    compress_directory("output")
    
    # "PASS" and "FAIL" substrings are checked for by test.py]
    all = sockets.get_socket_count()
    connected = board.connected_sockets_count
    
    failed = False
    if ((all - connected) == 0):
        print(f"✅ PASS: All {connected} GerberSockets routed successfully")
    else:
        failed = True
        print(f"❌ FAIL: GerberSockets routing incomplete for {all - connected} socket. {connected}/{all} completed")

    if debug.do_video:
        debug.video(name=file_number)

    return failed

if __name__ == "__main__":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore") 
        if (len(sys.argv) > 1):
            if (len(sys.argv) > 2):
                if (sys.argv[2] == "video"):
                    debug.do_video = True
            run(sys.argv[1]) # e.g 'python3 run.py 5-flip'
        else:
            run("5")
