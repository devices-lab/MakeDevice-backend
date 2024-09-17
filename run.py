from gerbonara.rs274x import GerberFile
from extract import extract_socket_locations
from process import merge_gerber_layers

assigned_nets = {
    "JD_PWR": 0.11,
    "JD_GND": 0.12,
    "JD_DATA": 0.13
}

socket_layer_name = "Jacdac_Bus"
module_details = "data.json"

# Merge the Jacdac Bus layers
gerber_sockets = merge_gerber_layers(module_details, socket_layer_name)

# Get the locations of the sockets
socket_locations = extract_socket_locations(gerber_sockets, assigned_nets)

# Create a new Gerber files with all the routing


# Merge them with the other already merged layers


# Return the final set of Gerber files
