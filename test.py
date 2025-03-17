import json
from extract import extract_socket_locations, extract_keep_out_zones
from process import merge_layers, merge_stacks, clear_directories, compress_directory
from free_route import create_grid, route_sockets
from generate import generate_gerber
import warnings

from loader import Loader
from board import Board

from gerbonara import GerberFile


# New run function introducing classes
def run(file_number: int) -> None:
    """Process a PCB design from a JSON file"""
    try:
        # Load PCB data
        file_path = f"./test_data/data_{file_number}.json"
        loader = Loader(file_path)
        
        board = Board(loader)
        
        
        
        print(f"🟢 Loaded board: {board.name} ({board.size[0]}mm × {board.size[1]}mm)")
        print(f"🟢 Board has {len(board.modules)} modules")
        
        # Clear out directories
        clear_directories()
        print("🟢 Cleared out /output and /generated directories")
        
        # Merge the GerberSockets layers from all individual modules
        sockets_layer = merge_layers(
            loader.modules_data, 
            loader.gs_layer_name, 
            loader.board_name
        )
        print(f"🟢 Merged {loader.gs_layer_name} layers")

        # Get the locations of the sockets
        socket_locations = extract_socket_locations(
            sockets_layer,
            loader.socket_diameter_mapping,
            loader.resolution
        )
        print(f"🟢 Socket locations identified for nets: {', '.join(loader.socket_diameter_mapping.keys())}")

        # Get the keep out zones
        keep_out_zones = extract_keep_out_zones(
            sockets_layer,
            loader.keep_out_zone_settings['aperture_diameter'],
            loader.keep_out_zone_settings['margin'],
            loader.resolution
        )
        print(f"🟢 {len(keep_out_zones)} keep-out zones identified")

        # Create a grid for routing
        grid = create_grid(loader.board_size, keep_out_zones, loader.resolution)
        print(f"🟢 Grid created at {loader.resolution}mm resolution")

        # Route the connections
        segments = route_sockets(grid, socket_locations, loader.configuration)
        print(f"🟢 Routing completed using {loader.algorithm} algorithm")
        
        # Generate output files
        generate_gerber(
            segments, 
            socket_locations, 
            loader.data['board_info'], 
            loader.configuration
        )
        print(f"🟢 Generated Gerber and Excellon files with {loader.gerber_options['trace_width']}mm trace width")
        
        # Merge the stacks
        merge_stacks(loader.modules_data, loader.board_name)
        print("🟢 Merged all files in the board stack")
        
        # Compress output
        output_zip = compress_directory("output") 
        print(f"🟢 Directory compressed to {output_zip}")
        
    except (FileNotFoundError, ValueError) as e:
        print(f"🔴 Error: {e}")
    except Exception as e:
        print(f"🔴 Unexpected error: {str(e)}")
    
    
with warnings.catch_warnings():
    warnings.simplefilter("ignore") 
    run(1)