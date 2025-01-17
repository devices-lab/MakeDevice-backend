import json
from extract import extract_socket_locations, extract_keep_out_zones
from process import merge_layers, merge_stacks, clear_directories, compress_directory
from route import create_grid, route_sockets
from generate import generate

def run(file_number):
    
    # Load the JSON configuration from a file (data_#.json)
    try:
        with open(f"test_data/data_{file_number}.json", 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: File data_{file_number}.json not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: File data_{file_number}.json is not a valid JSON.")
        return

    # Board details
    board = data['board']
    board_name = board['name']
    
    # Preferences and configurations
    configuration = data['configuration']
    algorithm = configuration['algorithm']
    diagonals = configuration['diagonals']
    resolution = configuration['resolution']
    gs_layer_name = configuration['gs_layer_name']
    socket_diameters = configuration['socket_diameters']
    layer_mappings = configuration['layer_mappings']
    gerber_options = configuration['gerber_options']
    
    # Modules and positioning
    modules = data['modules']
    
    # Clear out ./output and ./generated directories
    clear_directories()
    print("🟢 Cleared out /output and /generated directories")
    
    # Merge the Jacdac Bus layers
    sockets_layer = merge_layers(modules, gs_layer_name, board_name)
    print("🟢 Merged", gs_layer_name, "layers")

    # Get the locations of the sockets
    socket_locations = extract_socket_locations(sockets_layer, socket_diameters, resolution=resolution)
    print("🟢 Socket locations identified")

    # Get the keep out zones 
    keep_out_zones = extract_keep_out_zones(sockets_layer, resolution=resolution)
    print("🟢 Keep out zones identified")

    # Create a grid
    grid = create_grid(board["size"], keep_out_zones, resolution=resolution)
    print("🟢 Grid created")

    # Pass the grid along with the socket locations to the router
    segments = route_sockets(grid, socket_locations, resolution=resolution, algorithm=algorithm, diagonals=diagonals)
    print("🟢 Routing completed")

    # Generate Gerber and Excellon files
    generate(segments, socket_locations, layer_mappings, gerber_options, board_info=board)
    print("🟢 Generated Gerber and Excellon files")

    # Merge the Gerber stacks, along with the new generated layers
    merge_stacks(modules, board_name)
    print("🟢 Merged all files in the board stack")
    
    # Compress the output directory
    compress_directory("output")
    print("🟢 Directory compressed")
    
run(2)