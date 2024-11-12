import os
from gerber_writer import DataLayer, Path, Circle, set_generation_software
from datetime import datetime
from itertools import combinations


def generate_gerber(segments, socket_locations, layer_mappings, trace_width, via_diameter, board_info, collision_distance=1.0, output_dir="./generated"):
    """
    Converts line segments into separate Gerber files for each net type and adds vias on all layers for each socket location.
    Parameters:
        segments (dict): Dictionary with net names as keys and lists of line segments,
                         where each segment is a tuple of start and end coordinate tuples.
        socket_locations (dict): Dictionary with net names as keys and lists of tuples (x, y) as socket locations.
        trace_width (float): Width of the traces in mm.
        via_diameter (float): Diameter of the vias in mm.
        output_dir (str): Directory to store the generated Gerber files. Defaults to "./output".
    Returns:
        None
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Set software identification
    set_generation_software('Devices-Lab', 'MakeDevice', '0.1')
    
    # All layers that must be generated, regardless if they are mentioned in the layer_mappings
    all_layers = {
        'F_Cu.gtl': 'Copper,L1,Top,Signal',
        'In1_Cu.g2': 'Copper,L2,Inner,Signal',
        'In2_Cu.g3': 'Copper,L3,Inner,Signal',
        'B_Cu.gbl': 'Copper,L4,Bottom,Signal'
    }
    
    # Initialize all DataLayer instances and prepare to collect segment for each layer
    layers = {}
    layer_segments = {}  # {layer_filename: {net_type: [segments]}}

    for filename, layer_spec in all_layers.items():
        layers[filename] = DataLayer(layer_spec, negative=False)
        layer_segments[filename] = {}  # Initialize net segments for this layer

     # Add segments to the corresponding layer and collect them
    for net_type, paths in segments.items():
        if net_type in layer_mappings:
            filename, layer_spec = layer_mappings[net_type]
            layer = layers[filename]
            if net_type not in layer_segments[filename]:
                layer_segments[filename][net_type] = []
            for start, end in paths:
                path = Path()
                path.moveto(start)
                path.lineto(end)
                layer.add_traces_path(path, trace_width, 'Conductor')
                # Store the segment for intersection detection
                layer_segments[filename][net_type].append((start, end))
        else:
            print(f"🔴 Net '{net_type}' not found in layer mappings")

    # AI generated block
    # Detect intersections between nets on the same layer
    for filename, net_dict in layer_segments.items():
        nets = list(net_dict.keys())
        if len(nets) < 2:
            continue  # No other nets to compare with
        print(f"Checking for intersections on layer '{filename}'...")
        intersections_found = False
        reported_intersections = set()
        # Compare each pair of nets
        for net1, net2 in combinations(nets, 2):
            segments1 = net_dict[net1]
            segments2 = net_dict[net2]
            # Compare each pair of segments between the two nets
            for seg1 in segments1:
                for seg2 in segments2:
                    if segments_intersect(seg1, seg2):
                        intersection_point = compute_intersection_point(seg1, seg2)
                        if intersection_point:
                            # Round the intersection point to avoid floating-point precision issues
                            intersection_point_rounded = (round(intersection_point[0], 5), round(intersection_point[1], 5))
                            # Create a unique key for the intersection
                            intersection_key = (filename, net1, net2, intersection_point_rounded)
                            if intersection_key not in reported_intersections:
                                intersections_found = True
                                print(f"🟠 Intersection detected between nets '{net1}' and '{net2}' on layer '{filename}'")
                                print(f"   Intersection point at: {intersection_point_rounded}")
                                print(f"   Segments: {seg1} and {seg2}")
                                reported_intersections.add(intersection_key)
        if not intersections_found:
            print(f"✅ No intersections found on layer '{filename}'.")

    # Add vias to all layers for each socket location across all net types
    for positions in socket_locations.values():
        for x, y in positions:
            via_pad = Circle(via_diameter, 'ViaPad', negative=False)  # Via specifications
            for layer in layers.values():
                layer.add_pad(via_pad, (x, y), 0)

    # Save Gerber file for each layer
    for filename, layer in layers.items():
        file_path = os.path.join(output_dir, board_info["name"] + "-" + filename)
        with open(file_path, 'w') as file:
            file.write(layer.dumps_gerber())
    
    generate_board_outline(board_info)

# AI generated function
def segments_intersect(seg1, seg2):
    def ccw(A, B, C):
        # Check if the points are counter-clockwise
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

    (A, B), (C, D) = seg1, seg2
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

# AI generated function
def compute_intersection_point(seg1, seg2):
    (A, B), (C, D) = seg1, seg2
    # Line AB represented as a1x + b1y = c1
    a1 = B[1] - A[1]
    b1 = A[0] - B[0]
    c1 = a1 * A[0] + b1 * A[1]

    # Line CD represented as a2x + b2y = c2
    a2 = D[1] - C[1]
    b2 = C[0] - D[0]
    c2 = a2 * C[0] + b2 * C[1]

    determinant = a1 * b2 - a2 * b1
    if determinant == 0:
        # Lines are parallel; no intersection point
        return None
    else:
        x = (b2 * c1 - b1 * c2) / determinant
        y = (a1 * c2 - a2 * c1) / determinant
        return (x, y) 
 
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
