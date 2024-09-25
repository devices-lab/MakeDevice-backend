from gerber_writer import DataLayer, Path, Circle, set_generation_software
import os
from datetime import datetime

def generate_gerber(segments, socket_locations, trace_width, via_diameter, output_dir="./generated"):
    """
    Converts line segments into separate Gerber files for each net type and adds vias on all layers for each socket location.
    
    Args:
        segments (dict): Dictionary with net names as keys and lists of line segments,
                         where each segment is a tuple of start and end coordinate tuples.
        socket_locations (dict): Dictionary with net names as keys and lists of tuples (x, y) as socket locations.
        trace_width (float): Width of the traces in mm.
        via_diameter (float): Diameter of the vias in mm.
        output_dir (str): Directory to store the generated Gerber files. Defaults to "./output".
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Set software identification
    set_generation_software('Devices-Lab', 'MakeDevice', '0.1')
    
    # Define the layer mappings based on net type
    layer_mappings = {
        'JD_PWR': ('F_Cu.gtl', 'Copper,L1,Top,Signal'),
        'JD_DATA': ('In1_Cu.g2', 'Copper,L2,Inner,Signal'),
        'PROG': ('In2_Cu.g3', 'Copper,L3,Inner,Signal'),
        'JD_GND': ('B_Cu.gbl', 'Copper,L4,Bottom,Signal')
    }
    
    # Initialize DataLayer instances for each net type based on the mapping
    layers = {}
    for net_type, (filename, layer_spec) in layer_mappings.items():
        layers[net_type] = DataLayer(layer_spec, negative=False)

    # Add segments to the corresponding layer
    for net_type, paths in segments.items():
        if net_type in layers:
            layer = layers[net_type]
            for start, end in paths:
                path = Path()
                path.moveto(start)
                path.lineto(end)
                layer.add_traces_path(path, trace_width, 'Conductor')

    # Add vias to all layers for each socket location across all net types
    for positions in socket_locations.values():
        for x, y in positions:
            via_pad = Circle(via_diameter, 'ViaPad', negative=False)  # Via specifications
            for layer in layers.values():
                layer.add_pad(via_pad, (x, y), 0)

    # Write Gerber files for each layer
    for net_type, layer in layers.items():
        filename, _ = layer_mappings[net_type]
        file_path = os.path.join(output_dir, filename)
        with open(file_path, 'w') as file:
            file.write(layer.dumps_gerber())
        
def generate_excellon(socket_locations, drill_size, output_dir="./generated"):
    """
    Generates an Excellon drill file for plated through holes (PTH).
    
    Args:
        socket_locations (dict): Dictionary with net names as keys and lists of tuples (x, y) as drill locations.
        drill_size (float): Diameter of the drill holes in mm.
        output_dir (str): Directory to store the generated drill file. Defaults to "./output".
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # File path
    file_path = os.path.join(output_dir, "PTH.drl")
    
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

    # Write the file
    with open(file_path, 'w') as file:
        file.write('\n'.join(content))
