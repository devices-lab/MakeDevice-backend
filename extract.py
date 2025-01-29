from gerbonara.graphic_objects import Line
from gerbonara.apertures import CircleAperture
from debug import plot_debug_gerber

def round_to_resolution(value, resolution):
    """Rounds a value to the nearest multiple of the resolution."""
    return round(value / resolution) * resolution

def extract_socket_locations(gerber, sockets_diameter_mapping, resolution):
    """
    Extracts the locations of the Gerber Sockets from a Gerber file.

    Paramaters:
        gerber (GerberFile): The Gerber file object from gerbonara. 
        sockets_diameter_mapping (dict): A dictionary mapping net names to their assigned diameters. 
            Example format: {"JD_PWR": 0.11, "JD_GND": 0.12, "JD_DATA": 0.13} 
        resolution (float): The resolution of the grid, for scaling the socket and segment coordinates.


    Returns:
        socket_locations (dict): A dictionary containing net names as keys and a list of socket locations as values.
            Each socket location is represented as a tuple of (x, y) coordinates.
    """

    diameter_to_net = {value: key for key, value in sockets_diameter_mapping.items()}
    socket_locations = {}

    if not gerber.objects:
        print("No objects found in a GerberSocket file.")
    
    for obj in gerber.objects:
        if hasattr(obj, 'aperture') and isinstance(obj.aperture, CircleAperture):
            diameter = obj.aperture.diameter
            if diameter in diameter_to_net:
                net_name = diameter_to_net[diameter]
                if isinstance(obj, Line):  # Assuming lines are used to represent sockets
                    location = (
                        round_to_resolution(obj.x1, resolution),
                        round_to_resolution(obj.y1, resolution)
                    )
                    socket_locations.setdefault(net_name, []).append(location)
    
    return socket_locations

def extract_keep_out_zones(gerber, keep_out_zone_aperture_diameter, keep_out_zone_margin, resolution, debug=False):
    """
    Extracts and returns a list of rectangles representing the keep-out zones from the given Gerber object.
    
    Parameters:
        gerber (GerberFile): The Gerber file object from gerbonara.
        resolution (float): The resolution of the grid, for scaling the socket and segment coordinates.
        aperture_diameter (float): The diameter (in mm) of the aperture used to trace out the keep-out zones. Defaults to 0.1.
        margin (int): The margin to add to the keep-out zones. Defaults to 1mm.
        debug (bool): If True, the function will draw the keep-out zones on a separate Gerber file. Defaults to False.
    
    Returns:
        rectangles (tuple list): A list of tuples representing the rectangles of the keep-out zones. 
        Each tuple contains four points in the order (top_left, top_right, bottom_right, bottom_left).
    """
    lines = [obj for obj in gerber.objects if isinstance(obj, Line) and 
             isinstance(obj.aperture, CircleAperture) and 
             abs(obj.aperture.diameter - keep_out_zone_aperture_diameter) < 0.0001]

    rectangles = []
    used_indices = set()

    def find_continuation(current_index):
        current_line = lines[current_index]
        x2, y2 = current_line.x2, current_line.y2
        for index, line in enumerate(lines):
            if index not in used_indices and index != current_index:
                # Check connection
                if (line.x1 == x2 and line.y1 == y2) or (line.x2 == x2 and line.y2 == y2):
                    return index
        return None

    for index, line in enumerate(lines):
        if index in used_indices:
            continue
        current_index = index
        rectangle_indices = [current_index]

        for _ in range(3):
            next_index = find_continuation(current_index)
            if next_index is not None:
                rectangle_indices.append(next_index)
                current_index = next_index
            else:
                break

        if len(rectangle_indices) == 4:
            rectangle_lines = [lines[i] for i in rectangle_indices]
            if rectangle_lines[0].x1 == rectangle_lines[-1].x2 and rectangle_lines[0].y1 == rectangle_lines[-1].y2:
                points = set((line.x1, line.y1) for line in rectangle_lines) | set((line.x2, line.y2) for line in rectangle_lines)
                if len(points) == 4:
                    rounded_points = {
                        (round_to_resolution(p[0], resolution), round_to_resolution(p[1], resolution))
                        for p in points
                    }
                    sorted_points = sorted(rounded_points, key=lambda p: (p[0], p[1]))  # Sort primarily by x, secondarily by y
                    bottom_left = sorted_points[0][0] - keep_out_zone_margin, sorted_points[0][1] - keep_out_zone_margin
                    top_left = sorted_points[1][0] - keep_out_zone_margin, sorted_points[1][1] + keep_out_zone_margin
                    top_right = sorted_points[3][0] + keep_out_zone_margin, sorted_points[3][1] + keep_out_zone_margin
                    bottom_right = sorted_points[2][0] + keep_out_zone_margin, sorted_points[2][1] - keep_out_zone_margin
                    
                    rectangles.append((bottom_left, top_left, top_right, bottom_right))
                    used_indices.update(rectangle_indices)

            if debug:
                plot_debug_gerber(rectangles, output_file="debug_margin.gbr")
        
    return rectangles

#     *
#      \
#   \
#   |\
# \ | \ (__)
# \\|| \(oo)
#  \||\ \\/
#   ~~ \||
#    \\ ||
#     \\||
#      \||
#       ~~
#         \\_
#          \_
# Cow skiing a Black Diamond at Aspen