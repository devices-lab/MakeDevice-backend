import os
from gerber_writer import DataLayer, Path, Circle, set_generation_software
from datetime import datetime
from intersect import merge_overlapping_segments, check_net_intersections_by_layer, process_intersections, split_segments

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
    gerber_options = configuration['gerber_options']
    trace_width = gerber_options['trace_width']
    via_annular_ring_diameter = gerber_options['via_annular_ring_diameter']
    via_drilled_hole_diameter = gerber_options['via_drilled_hole_diameter']
    intersection_clearance = gerber_options['intersection_clearance']
    
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
            
    print(net_to_layer_mapping)
            
    # Extract the via locations from the socket locations
    via_locations = []
    for positions in socket_locations.values():
        for x, y in positions:
            via_locations.append((x, y))
    
    
    # # Perform modifications to the segments to avoid intersections
    # merge_overlapping_segments(segments)
    # intersections = check_net_intersections_by_layer(segments, net_to_layer_mapping)
    # intersection_details = process_intersections(intersections, intersection_clearance)
    # split_segments(segments, intersection_details)
    
    # # Handle each intersection
    # for intersection in intersection_details:
    #     point1 = intersection['point1']
    #     point2 = intersection['point2']

    #     # Add the two new segments between point1 and point2
    #     new_segment = (point1, point2)
    #     if "EMPTY" not in segments:
    #         segments["EMPTY"] = []
    #     segments["EMPTY"].append(new_segment)

    #     # Add the two points as vias
    #     via_locations.append(point1)
    #     via_locations.append(point2)

    plotted_nets = set()

    for filename, details in layer_mapping.items():
        for net in details["nets"]:
            if net not in segments:
                print(f"🔴 Net '{net}' from layer_mappings not found in segments returned from the router, and will be ignored")
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
    generate_board_outline(board_info)

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


def generate_board_outline(board, output_dir="./output"):
    """
    Generates a Gerber file for the board outline based on the board size and origin.
    Parameters:
        board (dict): Dictionary containing board information with 'name', 'size', and 'origin'.
        output_dir (str): Directory to store the generated Gerber outline file. Defaults to "./generated".
    Returns:
        None
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Extract board parameters
    board_name = board['name']
    size_x = board['size']['x']
    size_y = board['size']['y']
    origin_x = board['origin']['x']
    origin_y = board['origin']['y']

    # Create a DataLayer for the board outline
    outline_layer = DataLayer("Outline,EdgeCuts", negative=False)

    # Create a rectangular path for the board outline based on the size and origin
    path = Path()
    path.moveto((origin_x - size_x/2, origin_y - size_y/2))
    path.lineto((origin_x + size_x/2, origin_y - size_y/2))
    path.lineto((origin_x + size_x/2, origin_y + size_y/2))
    path.lineto((origin_x - size_x/2, origin_y + size_y/2))
    path.lineto((origin_x - size_x/2, origin_y - size_y/2))

    # Add the outline path to the layer
    outline_layer.add_traces_path(path, width=0.15, function="Outline")  # 0.15 mm width is common for outline traces

    # Generate the filename for the outline Gerber file
    file_path = os.path.join(output_dir, f"{board_name}-Edge_Cuts.gm1")

    # Write the Gerber content to the file
    with open(file_path, 'w') as file:
        file.write(outline_layer.dumps_gerber())
