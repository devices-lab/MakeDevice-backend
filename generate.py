import os
from gerber_writer import DataLayer, Path, Circle, set_generation_software
from datetime import datetime

def generate(segments, socket_locations, board_info, configuration, output_dir="./generated"):
    """
    Converts line segments into separate Gerber files for each net type and adds vias on all layers for each socket location.
    Parameters:
        segments (dict): Dictionary with net names as keys and lists of line segments,
                         where each segment is a tuple of start and end coordinate tuples.
        socket_locations (dict): Dictionary with net names as keys and lists of tuples (x, y) as socket locations.
        trace_width (float): Width of the traces in mm.
        via_diameter (float): Diameter of the vias in mm.
        output_dir (str): Directory to store the generated Gerber files. Defaults to "./output".
        intersection_distance (float): Distance of the via placement from the intersection point. Defaults to 1.0 mm.
    Returns:
        None
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Extract configurations from the passed JSON object
    layer_mapping = configuration['layer_mapping']
    connectors = configuration['connectors']
    
    gerber_options = configuration['gerber_options']
    trace_width = gerber_options['trace_width']
    via_annular_ring_diameter = gerber_options['via_annular_ring_diameter']
    via_drilled_hole_diameter = gerber_options['via_drilled_hole_diameter']
    rounded_corner_radius = gerber_options['rounded_corner_radius']

    
    # Set software identification
    set_generation_software(board_info['generation_software']['vendor'], 
                            board_info['generation_software']['application'], 
                            board_info['generation_software']['version'])
    
    # Set up the Gerber layers
    layers = {}
    for filename, details in layer_mapping.items():
        layers[filename] = DataLayer(details["attributes"], negative=False)
    
    # Reverse map layer_mappings to specify which net is on which layer
    net_to_layer_mapping = {}
    for filename, details in layer_mapping.items():
        for net in details["nets"]:
            net_to_layer_mapping[net] = filename
                        
    # Extract the via locations from the socket locations
    via_locations = set()
    for positions in socket_locations.values():
        for x, y in positions:
            via_locations.add((x, y))
    
    # Handle "TUNNELS" net separately to add vias only at overlap points
    if "TUNNELS" in segments:
        # Collect all points from nets other than "TUNNELS"
        net_points = set()
        for net, net_segments in segments.items():
            if net == "TUNNELS":
                continue
            for start, end in net_segments:
                net_points.add(start)
                net_points.add(end)

        # Check overlaps for each TUNNEL segment
        for start, end in segments["TUNNELS"]:
            if start in net_points:
                via_locations.add(start)
            if end in net_points:
                via_locations.add(end)
    
    plotted_nets = set()

    for filename, details in layer_mapping.items():
        for net in details["nets"]:
            if net not in segments:
                print(f"🔴 Net '{net}' from layer_mappings not found in segments returned from the router")
                continue
            if net in plotted_nets:
                print(f"🔴 Net '{net}' has already been plotted on a layer and will be skipped")
                continue
            for start, end in segments[net]:
                # Turn the segment into a path to the Gerber layer
                path = Path()
                path.moveto(start)
                path.lineto(end)
                layers[filename].add_traces_path(path, trace_width, 'Conductor')
            plotted_nets.add(net) # Mark the net as plotted to avoid duplicates

    # Add vias to all layers for each socket location across all net types
    for x, y in via_locations:
        via_pad = Circle(via_annular_ring_diameter, 'ViaPad', negative=False)  # Via specifications
        for layer in layers.values():
            layer.add_pad(via_pad, (x, y), 0)

    # Save Gerber file for each layer
    for filename, layer in layers.items():
        file_path = os.path.join(output_dir, board_info["name"] + "-" + filename)
        with open(file_path, 'w') as file:
            file.write(layer.dumps_gerber())
    
    generate_excellon(via_locations, drill_size=via_drilled_hole_diameter, board_name=board_info['name'])
    generate_board_outline(board_info, rounded_corner_radius, connectors)

def generate_excellon(via_locations, drill_size, board_name, output_dir="./generated"):
    """
    Generates an Excellon drill file for plated through holes (PTH).
    Parameters:
        socket_locations (dict): Dictionary with net names as keys and lists of tuples (x, y) as drill locations.
        drill_size (float): Diameter of the drill holes in mm.
        output_dir (str): Directory to store the generated drill file. Defaults to "./generated".
    Returns:
        None
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Drill file content
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
    content = [
        "M48",
        f"; DRILL file {{MakeDevice v0.1}} date {timestamp}",
        "; FORMAT={-:-/ absolute / metric / decimal}",
        f"; #@! TF.CreationDate,{timestamp}",
        "; #@! TF.GenerationSoftware,Kicad,Pcbnew,8.0.2-1",
        "; #@! TF.FileFunction,Plated,1,4,PTH",
        "FMAT,2",
        "METRIC",
        "; #@! TA.AperFunction,Plated,PTH,ViaDrill",
        f"T1C{drill_size:.3f}",
        "%",
        "G90",
        "G05",
        "T1"
    ]

    # Adding drill locations from socket_locations
    for x, y in via_locations:
        content.append(f"X{x:.2f}Y{y:.2f}")
    
    content.append("M30")  # End of program

    # Save drill file
    file_path = os.path.join(output_dir, board_name + "-" + "PTH.drl")
    with open(file_path, 'w') as file:
        file.write('\n'.join(content))


import os
from gerber_writer import DataLayer, Path

def generate_board_outline(board, rounding_radius, connectors, output_dir="./output"):
    """
    Generates a Gerber file for the board outline with rounded corners.
    
    The arc centers are inset from the board corners by the rounding_radius,
    so that the arcs replace the sharp corners and bulge outward.
    
    Parameters:
        board (dict): Contains board info with keys 'name', 'size', and 'origin'.
        output_dir (str): Directory to store the generated Gerber file.
        rounding_radius (float): Radius (in mm) for the rounded corners.
    """
    # Ensure the output directory exists.
    os.makedirs(output_dir, exist_ok=True)

    # Extract board parameters.
    board_name = board['name']
    size_x = board['size']['x']
    size_y = board['size']['y']
    origin_x = board['origin']['x']
    origin_y = board['origin']['y']
    
    # Get connector information
    left_connector = connectors['left']
    right_connector = connectors['right']
    connector_width = 16 # Width of the connector in mm

    # Calculate the board boundaries.
    xmin = origin_x - size_x / 2
    xmax = origin_x + size_x / 2
    ymin = origin_y - size_y / 2
    ymax = origin_y + size_y / 2

    # Ensure the rounding radius does not exceed half the board dimensions
    rounding_radius = min(rounding_radius, size_x / 2, size_y / 2)

    # Create the DataLayer and Path for the board outline
    outline_layer = DataLayer("Outline,EdgeCuts", negative=False)
    path = Path()

    # Start on the bottom edge, offset from the left by rounding_radius
    path.moveto((xmin + rounding_radius, ymin))
    
    # Bottom edge
    path.lineto((xmax - rounding_radius, ymin))
    # Bottom-right corner
    if rounding_radius > 0:
        path.arcto((xmax, ymin + rounding_radius), (xmax - rounding_radius, ymin + rounding_radius), '+')
    
    # Right edge
    if right_connector:
        path.lineto((xmax, origin_y - connector_width / 2))
        path.moveto((xmax, origin_y + connector_width / 2))
    path.lineto((xmax, ymax - rounding_radius))
    # Top-right corner
    if rounding_radius > 0:
        path.arcto((xmax - rounding_radius, ymax), (xmax - rounding_radius, ymax - rounding_radius), '+')
    
    # Top edge
    path.lineto((xmin + rounding_radius, ymax))
    # Top-left corner
    if rounding_radius > 0:
        path.arcto((xmin, ymax - rounding_radius), (xmin + rounding_radius, ymax - rounding_radius), '+')
    
    # Left edge
    if left_connector: 
        path.lineto((xmin, origin_y + connector_width / 2))
        path.moveto((xmin, origin_y - connector_width / 2))
    path.lineto((xmin, ymin + rounding_radius))
    # Bottom-left corner
    if rounding_radius > 0:
        path.arcto((xmin + rounding_radius, ymin), (xmin + rounding_radius, ymin + rounding_radius), '+')
    
    # Add the constructed path to the layer with a trace width of 0.15 mm
    outline_layer.add_traces_path(path, 0.15, 'Outline')

    # Write the Gerber file
    file_path = os.path.join(output_dir, f"{board_name}-Edge_Cuts.gm1")
    with open(file_path, 'w') as file:
        file.write(outline_layer.dumps_gerber())
