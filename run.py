import json
import sys
from extract import extract_socket_locations, extract_keep_out_zones
from process import merge_layers, merge_stacks, clear_directories, compress_directory
from route import create_grid, route_sockets
from generate import generate


# Coordinate rounding is done to up to the nearest resolution value.
# Increasing the resolution will allow for precise routing, at the cost of 
# increased computation time for the pathfinding algorithm.
# 
# Ideal resolution is to be determined on the basis of the minimum grid size
# used in the PCB design tool.
# If the all object on the PCB are spaced on a 0.1mm grid, the resolution 
# should be set to 0.1.
GRID_RESOLUTION = 1

# The socket layer name must match that of the layer name given in the Gerber files via
#  the PCB design tool like KiCad
# The Gerber Socket layer must end with "socket_layer_name.gbr"
socket_layer_name = "GerberSockets.gbr"

# The following are the socket radii for the Jacdac Gerber Sockets, as described 
# in the design guidelines for the Jacdac virtual components 
jacdac_socket_nets = {
    "JD_PWR": 0.11,
    "JD_GND": 0.12,
    "JD_DATA": 0.13
}

# Define the layer mappings based on net type
layer_mappings = {
    'JD_PWR': ('F_Cu.gtl', 'Copper,L1,Top,Signal'),
    'JD_DATA': ('F_Cu.gtl', 'Copper,L1,Top,Signal'),
    'EMPTY': ('In1_Cu.g2', 'Copper,L2,Inner,Signal'),
    'PROG': ('In2_Cu.g3', 'Copper,L3,Inner,Signal'),
    'JD_GND': ('B_Cu.gbl', 'Copper,L4,Bottom,Signal'),
}



def run(test_data):
    
    # Load the JSON configuration from a file (data.json)
    try:
        with open(f"test_data/data_{test_data}.json", 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        print(f"Error: File data_{test_data}.json not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: File data_{test_data}.json is not a valid JSON.")
        return

    # Extract board details and modules
    board = data['board']
    board_name = board['name']
    modules = data['modules']

    # Clear out ./output and ./generated directories
    clear_directories()
    print("🟢 Cleared out /output and /generated directories")
    
    # Merge the Jacdac Bus layers
    sockets_layer = merge_layers(modules, socket_layer_name, board_name)
    print("🟢 Merged", socket_layer_name, "layers")

    # Get the locations of the sockets
    socket_locations = extract_socket_locations(sockets_layer, jacdac_socket_nets)
    print("🟢 Socket locations identified")

    # Get the keep out zones 
    keep_out_zones = extract_keep_out_zones(sockets_layer)
    print("🟢 Keep out zones identified")

    # Create a grid
    grid = create_grid(board["size"], keep_out_zones, resolution=GRID_RESOLUTION)
    print("🟢 Grid created")

    # Pass the grid along with the socket locations to the router
    segments = route_sockets(grid, socket_locations, resolution=GRID_RESOLUTION, algorithm="breadth_first")
    print("🟢 Routing completed")

    # Generate Gerber and Excellon files
    generate(segments, socket_locations, layer_mappings, trace_width=0.254, via_diameter=0.6, board_info=board)
    print("🟢 Generated Gerber and Excellon files")

    # Merge the Gerber stacks, along with the new generated layers
    merge_stacks(modules, board_name)
    print("🟢 Merged all files in the board stack")
    
    # Compress the output directory
    compress_directory("output")
    print("🟢 Directory compressed")
    
def debug():
    print("Debugging...")

run(3)