from process import merge_layers, merge_stacks, clear_directories, compress_directory
from constrained_route import create_grid
from generate import generate

from gerbersockets import Sockets, Zones
from loader import Loader
from board import Board

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
    
    if loader.debug:
        sockets.save_to_file(f"./{loader.name}_sockets.json")
        sockets.plot_extracted_sockets(f"GerberSockets-sockets.gbr")
        
        zones.save_to_file(f"./{loader.name}_zones.json")
        zones.plot_extracted_zones(f"GerberSockets-zones.gbr")

        print("⚪️ Saved sockets and zones to files")
        
    print("🟢 Extracted sockets and keep-out zones")

    # Create a PCB
    board = Board(loader, sockets, zones)
    
    
    print(board.generation_software)
    
    
    
    # grid = create_grid(zones, loader)
    # print("🟢 Grid created") 

    # # Pass the grid along with the socket locations to the router
    # segments = route_sockets(grid, socket_locations, configuration)
    # print("🟢 Routing completed")
    
    # # Generate Gerber and Excellon files
    # generate(segments, socket_locations, board., configuration)
    # print("🟢 Generated Gerber and Excellon files")

    # # Merge the Gerber stacks, along with the new generated layers
    # merge_stacks(modules, board_name)
    # print("🟢 Merged all files in the board stack")
    
    # Compress the output directory
    compress_directory("output")
    print("🟢 Directory compressed")
    
    
with warnings.catch_warnings():
    warnings.simplefilter("ignore") 
    run(5)
