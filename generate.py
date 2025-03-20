import os
from gerber_writer import DataLayer, Path, Circle, set_generation_software
from datetime import datetime

from board import Board

def generate(board: Board, output_dir="./generated"):
    _generate_graphics(board, output_dir)
    _generate_drill(board, output_dir)
    _generate_outline(board, output_dir)
    
def _generate_graphics(board: Board, output_dir) -> None:
    """
    Takes traces and annular rings from the board object, and generates Gerber graphical objects.  
    
    Parameters:
        board: The PCB board with module, socket, zone and segment data
        output_dir: Directory to store the generated Gerber files
        
    Returns:
        None
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Set software identification
    set_generation_software(board.generation_software['vendor'], 
                            board.generation_software['application'], 
                            board.generation_software['version'])
    
    via_diameter = board.loader.fabrication_options['via_diameter']
    edge_clearance = board.loader.fabrication_options['edge_clearance']
    bus_clearance = board.bus_clearance
    o_x = board.origin['x']
    o_y = board.origin['y']
    
    # Process segments and annular rings for each layer
    for layer_name, layer in board.layers.items():
        
        # Get the corresponding gerber layer
        gerber = DataLayer(layer.attributes, negative=False)

        # Add fills if selected for the current layer
        if layer.fill:
            # First, create a path of the entire board outline, taking into consideration the bus_clearance
            bottom_left = ((o_x - board.width / 2) + bus_clearance, o_y - board.height / 2 + edge_clearance)
            top_left = ((o_x - board.width / 2) + bus_clearance, o_y + board.height / 2 - edge_clearance)
            top_right = (o_x + board.width / 2 - edge_clearance, o_y + board.height / 2 - edge_clearance)
            bottom_right = (o_x + board.width / 2 - edge_clearance, o_y - board.height / 2 + edge_clearance)

            outline = Path()
            outline.moveto(bottom_left)
            outline.lineto(top_left)
            outline.lineto(top_right)
            outline.lineto(bottom_right)
            outline.lineto(bottom_left)
            gerber.add_region(outline, "GND,Copper,Fill", negative=False)
            
            # # Now for each zone, add a cutout (negative region)
            zones = board._zones.get_data()
            for zone in zones:
                cutout = Path()
                cutout.moveto(zone[0])
                cutout.lineto(zone[1])
                cutout.lineto(zone[2])
                cutout.lineto(zone[3])
                cutout.lineto(zone[0])
                gerber.add_region(cutout, "GND,Copper,Fill", negative=True)
                
        # Add segments for the current layer
        for segment in layer.segments:
            # Get start and end points from the Segment object
            start_point = segment.start.as_tuple()
            end_point = segment.end.as_tuple()
            
            # Turn the segment into a path to the Gerber layer
            path = Path()
            path.moveto(start_point)
            path.lineto(end_point)
            gerber.add_traces_path(path, segment.width, 'Conductor')
            
        # Add annular rings to the current layer
        for annular_ring in layer.annular_rings:
            pad = Circle(via_diameter, 'ViaPad', negative=False)
            gerber.add_pad(pad, annular_ring.as_tuple(), 0)
        

        
        # Save Gerber file
        file_path = os.path.join(output_dir, board.name + "-" + layer_name)
        with open(file_path, 'w') as file:
            file.write(gerber.dumps_gerber())
    
def _generate_drill(board: Board, output_dir="./generated") -> None:
    """
    Generates an Excellon drill file for plated through holes (PTH).
    
    Parameters:
        board: The PCB board with module, socket, zone and segment data
        output_dir (str): Directory to store the generated drill file. Defaults to "./generated".
    
    Returns:
        None
    """
    
    via_hole_diameter = board.loader.fabrication_options['via_hole_diameter']    
    
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Drill file content
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S%z")
    content = [
        "M48",
        f"; DRILL file {board.name} date {timestamp}",
        "; FORMAT={-:-/ absolute / metric / decimal}",
        f"; #@! TF.CreationDate,{timestamp}",
        "; #@! TF.GenerationSoftware,Kicad,Pcbnew,8.0.2-1",
        "; #@! TF.FileFunction,Plated,1,4,PTH",
        "FMAT,2",
        "METRIC",
        "; #@! TA.AperFunction,Plated,PTH,ViaDrill",
        f"T1C{via_hole_diameter:.3f}",
        "%",
        "G90",
        "G05",
        "T1"
    ]

    # Adding drill locations from socket_locations
    for drill_hole in board._drill_holes:
        x, y = drill_hole.as_tuple()
        content.append(f"X{x:.2f}Y{y:.2f}")
    
    content.append("M30") # End of program

    # Save drill file
    file_path = os.path.join(output_dir, board.name + "-" + "PTH.drl")
    with open(file_path, 'w') as file:
        file.write('\n'.join(content))

def _generate_outline(board: Board, output_dir="./output"):
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

    # Extract board origins
    origin_x = board.origin['x']
    origin_y = board.origin['y']
    
    # Get the rounding radius
    rounding_radius = board.loader.fabrication_options['rounded_corner_radius']
    
    # Get connector information
    left_connector = board.loader.connectors['left']
    right_connector = board.loader.connectors['right']
    bottom_connector = board.loader.connectors['bottom']
    top_connector = board.loader.connectors['top']
    connector_width = 16 # Width of the connector in mm - hardcoded for now

    # Calculate the board boundaries.
    xmin = origin_x - board.width / 2
    xmax = origin_x + board.width / 2
    ymin = origin_y - board.height / 2
    ymax = origin_y + board.height / 2

    # Ensure the rounding radius does not exceed half the board dimensions
    rounding_radius = min(rounding_radius, board.width / 2, board.height / 2)

    # Create the DataLayer and Path for the board outline
    outline_layer = DataLayer("Outline,EdgeCuts", negative=False)
    path = Path()

    # Start on the bottom edge, offset from the left by rounding_radius
    path.moveto((xmin + rounding_radius, ymin))
    
    # Bottom edge
    if bottom_connector:
        path.lineto((origin_x - connector_width / 2, ymin))
        path.moveto((origin_x + connector_width / 2, ymin))
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
    if top_connector:
        path.lineto((origin_x + connector_width / 2, ymax))
        path.moveto((origin_x - connector_width / 2, ymax))
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
    file_path = os.path.join(output_dir, f"{board.name}-Edge_Cuts.gm1")
    with open(file_path, 'w') as file:
        file.write(outline_layer.dumps_gerber())
