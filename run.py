from process import merge_layers, merge_stacks, clear_directories, compress_directory
from generate import generate_gerber

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
    
    print(f"Sockets: {sockets.get_socket_locations()}")
    
    # Get the keep out zones 
    zones = Zones(loader, gerbersockets_layer)
    if zones.get_zone_count() == 0:
        print("🔴 No keep-out zones found")
        return
    
    print(f"Zones: {zones.get_zone_rectangles()}")
    
    if loader.debug:
        sockets.save_to_file(f"./{loader.name}_sockets.json")
        sockets.plot_extracted_sockets(f"GerberSockets-sockets.gbr")
        
        zones.save_to_file(f"./{loader.name}_zones.json")
        zones.plot_extracted_zones(f"GerberSockets-zones.gbr")

        print("⚪️ Saved sockets and zones to files")
        
    print("🟢 Extracted sockets and keep-out zones")

    board = Board(loader, sockets, zones)
    
    router = Router(board)
    result = router.route()
    
    
    print(Board.get_layers(board))

    generate_gerber(board, result)
    merge_stacks(board.modules, board.name)
    compress_directory("output")
    
with warnings.catch_warnings():
    warnings.simplefilter("ignore") 
    run(5)
