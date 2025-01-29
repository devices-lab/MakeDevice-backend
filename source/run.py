import json
from extract import extract_socket_locations, extract_keep_out_zones
from process import merge_layers, merge_stacks, clear_directories, compress_directory
from route import create_grid, route_sockets
from generate import generate
import warnings

def run(file_number):
    
    # Load the JSON configuration from a file (data_#.json)
    try:
        with open(f"../test_data/data_{file_number}.json", 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"🔴 File data_{file_number}.json not found.")
        return
    except json.JSONDecodeError:
        print(f"🔴 File data_{file_number}.json is not a valid JSON.")
        return

    # Board details
    board_info = data['board_info']
    board_name = board_info['name']
    board_size = board_info['size']
    
    # Configurations
    configuration = data['configuration']
    resolution = configuration['resolution']
    gs_layer_name = configuration['gs_layer_name']
    sockets_diameter_mapping = configuration['socket_diameter_mapping']
    keep_out_zone_aperture_diameter = configuration['keep_out_zone_aperture_diameter']
    keep_out_zone_margin = configuration['keep_out_zone_margin']

    # Modules and positioning
    modules = data['modules']
    
    # Clear out ./output and ./generated directories
    clear_directories()
    print("🟢 Cleared out /output and /generated directories")
    
    # Merge the GerberSockets layers from all individual modules
    sockets_layer = merge_layers(modules, gs_layer_name, board_name)
    print("🟢 Merged", gs_layer_name, "layers")

    # Get the locations of the sockets
    socket_locations = extract_socket_locations(sockets_layer, sockets_diameter_mapping, resolution)
    print("🟢 Socket locations identified")

    # Get the keep out zones 
    keep_out_zones = extract_keep_out_zones(sockets_layer, keep_out_zone_aperture_diameter, keep_out_zone_margin, resolution)
    print("🟢 Keep out zones identified")

    # Create a grid
    grid = create_grid(board_size, keep_out_zones, resolution)
    print("🟢 Grid created")

    # Pass the grid along with the socket locations to the router
    segments = route_sockets(grid, socket_locations, configuration)
    print("🟢 Routing completed")

    # Generate Gerber and Excellon files
    generate(segments, socket_locations, board_info, configuration)
    print("🟢 Generated Gerber and Excellon files")

    # Merge the Gerber stacks, along with the new generated layers
    merge_stacks(modules, board_name)
    print("🟢 Merged all files in the board stack")
    
    # Compress the output directory
    compress_directory("output")
    print("🟢 Directory compressed")
    
    
with warnings.catch_warnings():
    warnings.simplefilter("ignore") 
    run(1)