from gerbonara.graphic_objects import Line
from gerbonara.apertures import CircleAperture

def extract_socket_locations(gerber, sockets_diameter_mapping):
    """
    Extracts the locations of socket connections from a Gerber file.

    Parameters:
        gerber (GerberFile): The Gerber file object.
        sockets_diameter_mapping (dict): A dictionary mapping net names to their assigned diameters. 
            Example format: {"JD_PWR": 0.11, "JD_GND": 0.12, "JD_DATA": 0.13} 

    Returns:
        dict: A dictionary containing net names as keys and a list of socket locations as values.
            Each socket location is represented as a tuple of (x, y) coordinates.
    """

    # Dictionary to map diameters to net names for easier lookup
    diameter_to_net = {value: key for key, value in sockets_diameter_mapping.items()}

    # Dictionary to store net names and their locations
    socket_locations = {}

    # Iterate over all objects in the Gerber file
    for obj in gerber.objects:
        if hasattr(obj, 'aperture') and isinstance(obj.aperture, CircleAperture):
            diameter = obj.aperture.diameter
            if diameter in diameter_to_net:
                net_name = diameter_to_net[diameter]
                if isinstance(obj, Line): # Gerber Sockets are represented as lines
                    location = (obj.x1, obj.y1)
                    if net_name not in socket_locations:
                        socket_locations[net_name] = []
                    socket_locations[net_name].append(location)

    return socket_locations