import os
from gerber_writer import DataLayer, Path, Circle, set_generation_software
from datetime import datetime
from intersect import merge_overlapping_segments, check_net_intersections_by_layer, process_intersections, split_segments

def generate_gerber(segments, socket_locations, layer_mappings, trace_width, via_diameter, board_info, intersection_clearance=1.0, output_dir="./generated"):
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

    # Set software identification
    set_generation_software('Devices-Lab', 'MakeDevice', '0.1')
    
    default_layers = {
        'F_Cu.gtl': 'Copper,L1,Top,Signal',
        'In1_Cu.g2': 'Copper,L2,Inner,Signal',
        'In2_Cu.g3': 'Copper,L3,Inner,Signal',
        'B_Cu.gbl': 'Copper,L4,Bottom,Signal'
    }
    
    layers = {}
    for filename, attributes in default_layers.items():
        layers[filename] = DataLayer(attributes, negative=False) 
        
    all_vias = []
    for positions in socket_locations.values():
        for x, y in positions:
            all_vias.append((x, y))
        
    # Perform modifications to the segments to avoid intersections
    merge_overlapping_segments(segments)
    intersections = check_net_intersections_by_layer(segments, layer_mappings)
    intersection_segments = process_intersections(intersections, intersection_clearance)
    split_segments(segments, intersection_segments)
    
    # Add inner traces and vias
    print(intersection_segments)
    

    for net_type, paths in segments.items():
        # Check if the net type is in the layer mappings
        if net_type in layer_mappings:
            filename, attributes = layer_mappings[net_type]
            layer = layers[filename]
            for start, end in paths:
                # Turn the segment into a path to the Gerber layer
                path = Path()
                path.moveto(start)
                path.lineto(end)
                layer.add_traces_path(path, trace_width, 'Conductor')
        else:
            print(f"🔴 Net '{net_type}' not found in layer mappings")

    # Add vias to all layers for each socket location across all net types
    for x, y in all_vias:
        via_pad = Circle(via_diameter, 'ViaPad', negative=False)  # Via specifications
        for layer in layers.values():
            layer.add_pad(via_pad, (x, y), 0)

    # Save Gerber file for each layer
    for filename, layer in layers.items():
        file_path = os.path.join(output_dir, board_info["name"] + "-" + filename)
        with open(file_path, 'w') as file:
            file.write(layer.dumps_gerber())
    
    generate_board_outline(board_info)

def generate_excellon(socket_locations, drill_size, board_name, output_dir="./generated"):
    """
    Generates an Excellon drill file for plated through holes (PTH).
    Parameters:
        socket_locations (dict): Dictionary with net names as keys and lists of tuples (x, y) as drill locations.
        drill_size (float): Diameter of the drill holes in mm.
        output_dir (str): Directory to store the generated drill file. Defaults to "./output".
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
    for positions in socket_locations.values():
        for x, y in positions:
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
