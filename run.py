from process import merge_layers, merge_stacks, clear_directories, compress_directory
from generate import generate

from gerbersockets import Sockets, Zones
from loader import Loader
from board import Board
from busrouter import BusRouter as Router

import warnings

def run(file_number: int):
    
    loader = Loader(f"./test_data/data_{file_number}.json")
    if loader.debug:
        print("⚪️ Running in debug mode")

    # Clear out ./output and ./generated directories
    clear_directories()
    print("🟢 Cleared out `/output` and `/generated` directories")
    
    # Merge the GerberSockets layers from all individual modules
    gerbersockets_layer = merge_layers(loader.modules, loader.gerbersockets_layer_name, loader.name)
    print("🟢 Merged", loader.gerbersockets_layer_name, "layers")

    # Get the locations of the sockets
    sockets = Sockets(loader, gerbersockets_layer)
    if sockets.get_socket_count() == 0:
        print("🔴 No sockets found")
        return
    
    # Get the keep out zones 
    zones = Zones(loader, gerbersockets_layer)
    if zones.get_zone_count() == 0:
        print("🔴 No keep-out zones found")
        return

    board = Board(loader, sockets, zones)
        
    router = Router(board)
    
    router.route()

    generate(board)
    merge_stacks(board.modules, board.name)
    compress_directory("output")
    
with warnings.catch_warnings():
    warnings.simplefilter("ignore") 
    run(5)
