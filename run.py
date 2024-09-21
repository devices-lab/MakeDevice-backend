from gerbonara.rs274x import GerberFile
from extract import extract_socket_locations, extract_keep_out_zones
from process import merge_gerber_layers
from route import create_grid, route_sockets
from debug import show_grid_and_routes

# Coordinate rounding is done to up to the nearest resolution value.
# Increasing the resolution will allow for precise routing, at the cost of 
# increased computation time for the pathfinding algorithm.
# 
# Ideal resolution is to be determined on the basis of the minimum grid size
# used in the PCB design tool.
# If the all object on the PCB are spaced on a 0.1mm grid, the resolution 
# should be set to 0.1.
GRID_RESOLUTION = 0.1

# The following are the socket radii for the Jacdac Gerber Sockets, as described 
# in the design guidelines for the Jacdac virtual components 
jacdac_socket_nets = {
    "JD_PWR": 0.11,
    "JD_GND": 0.12,
    "JD_DATA": 0.13
}

# The socket layer name must match that of the layer name given in the Gerber files via
#  the PCB design tool like KiCad
# The Gerber Socket layer must end with "socket_layer_name.gbr"
socket_layer_name = "Jacdac_Bus"

# The following need to be passed on from MakeDevice
module_details = "data.json"
PCB_dimensions = (100, 100)


# # Merge the Jacdac Bus layers
gerber_sockets = merge_gerber_layers(module_details, socket_layer_name)
print("✅ Merged", socket_layer_name, "layers")

# # Get the locations of the sockets
socket_locations = extract_socket_locations(gerber_sockets, jacdac_socket_nets)
print("✅ Socket locations identified")

# Get the keep out zones 
keep_out_zones = extract_keep_out_zones(gerber_sockets)
print("✅ Keep out zones identified")

# Create a grid
grid = create_grid(PCB_dimensions, keep_out_zones, resolution=GRID_RESOLUTION)
print("✅ Grid created")

# Pass the grid along with the socket locations to the router
routes = route_sockets(grid, socket_locations, resolution=GRID_RESOLUTION, algorithm="breadth_first")
print("✅ Routing completed")

# Display on the graph
print("✅ Graph displayed")
show_grid_and_routes(grid, socket_locations, routes, resolution=GRID_RESOLUTION)