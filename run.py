import json
from extract import extract_socket_locations, extract_keep_out_zones
from process import merge_gerber_layers, merge_gerber_stacks, clear_directories
from route import create_grid, route_sockets
from debug import show_grid_segments_sockets, show_grid_routes_sockets
from generate import generate_gerber, generate_excellon

# Coordinate rounding is done to up to the nearest resolution value.
# Increasing the resolution will allow for precise routing, at the cost of 
# increased computation time for the pathfinding algorithm.
# 
# Ideal resolution is to be determined on the basis of the minimum grid size
# used in the PCB design tool.
# If the all object on the PCB are spaced on a 0.1mm grid, the resolution 
# should be set to 0.1.
GRID_RESOLUTION = 1

# Prefix for all generated and merged Gerber files
BOARD_NAME = "MakeDevice"

# The socket layer name must match that of the layer name given in the Gerber files via
#  the PCB design tool like KiCad
# The Gerber Socket layer must end with "socket_layer_name.gbr"
socket_layer_name = "Jacdac_Bus.gbr"

# The following are the socket radii for the Jacdac Gerber Sockets, as described 
# in the design guidelines for the Jacdac virtual components 
jacdac_socket_nets = {
    "JD_PWR": 0.11,
    "JD_GND": 0.12,
    "JD_DATA": 0.13
}

# Load the JSON configuration from a file (data.json)
with open("data.json", 'r') as file:
    data = json.load(file)

# Extract board details and modules
board = data['board']
modules = data['modules']

print("board", board)
print("modules", modules)
PCB_dimensions = (100, 100)

def run():
    # Clear out ./output and ./generated directories
    clear_directories()
    print("✅ Cleared out directories")
    
    # Merge the Jacdac Bus layers
    sockets_layer = merge_gerber_layers(modules, socket_layer_name)
    print("✅ Merged", socket_layer_name, "layers")

    # Get the locations of the sockets
    socket_locations = extract_socket_locations(sockets_layer, jacdac_socket_nets)
    print("✅ Socket locations identified")

    # Get the keep out zones 
    keep_out_zones = extract_keep_out_zones(sockets_layer)
    print("✅ Keep out zones identified")

    # Create a grid
    grid = create_grid(PCB_dimensions, keep_out_zones, resolution=GRID_RESOLUTION)
    print("✅ Grid created")

    # Pass the grid along with the socket locations to the router
    segments = route_sockets(grid, socket_locations, resolution=GRID_RESOLUTION, algorithm="breadth_first")
    print("✅ Routing completed")

    # Generate Gerber files
    generate_gerber(segments, socket_locations, trace_width=0.254, via_diameter=0.6, board_name=BOARD_NAME)
    print("✅ Generated Gerber files")

    # Generate Excellon files
    generate_excellon(socket_locations, drill_size=0.3, board_name=BOARD_NAME)
    print("✅ Generated Excellon files")

    # Merge the Gerber stacks, along with the new generated layers
    merge_gerber_stacks(modules, BOARD_NAME)
    print("✅ Merged all files in the board stack")
    
def debug():
    clear_directories()
    
# Select mode
run()