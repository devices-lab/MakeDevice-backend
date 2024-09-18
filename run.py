from gerbonara.rs274x import GerberFile
from extract import extract_socket_locations, extract_keep_out_zones
from process import merge_gerber_layers
from route import create_grid, route_sockets
from debug import show_plot

assigned_nets = {
    "JD_PWR": 0.11,
    "JD_GND": 0.12,
    "JD_DATA": 0.13
}

socket_layer_name = "Jacdac_Bus"
module_details = "data.json"
PCB_dimensions = (100, 100)

# Merge the Jacdac Bus layers
gerber_sockets = merge_gerber_layers(module_details, socket_layer_name)
print("✅ Merged", socket_layer_name, "layers")

# Get the locations of the sockets
socket_locations = extract_socket_locations(gerber_sockets, assigned_nets)
print("✅ Socket locations identified")
# Get the keep out zones 
keep_out_zones = extract_keep_out_zones(gerber_sockets)
print("✅ Keep out zones identified")
# Create a grid
grid = create_grid(PCB_dimensions, keep_out_zones)
print("✅ Grid created")

# Pass the grid along with the socket locations to the router
routes = route_sockets(grid, socket_locations)
print("✅ Routing completed")

# Display on the graph
print("✅ Graph displayed")
show_plot(grid, socket_locations, routes)
