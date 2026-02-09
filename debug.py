import os
import sys
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from gerber_writer import DataLayer, Path
from pathlib import Path as PathLib
from typing import Dict, List, Tuple, Union
from matplotlib.colors import ListedColormap

from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.collections import LineCollection
from matplotlib.patches import Circle as MplCircle

matplotlib.use('Agg')  # Use a non-interactive backend for matplotlib (since server-side image generation. No UI)

# ── Layer colour / style helpers ────────────────────────────────────────────
LAYER_COLORS = {
    "F_Cu.gtl": "#E53E3E",   # red  – front copper
    "B_Cu.gbl": "#3182CE",   # blue – back copper
}
LAYER_ALPHA = 0.5
DEFAULT_COLOR = "#2D3748"

def _layer_color(layer_name: str) -> str:
    return LAYER_COLORS.get(layer_name, DEFAULT_COLOR)


def generate_test_grid(dimensions):
    width, height = dimensions
    grid = np.zeros((width, height), dtype=int)
    return grid

def print_full_array(array):
    # Temporarily set NumPy print options to display the entire array
    with np.printoptions(threshold=np.inf):
        print(array)

def show_grid(grid, points=None, title="Grid display"):
    plt.figure(figsize=(7, 7))  # Set the figure size
    # Calculate the correct extents to align the grid cells with the axes
    plt.imshow(grid, cmap='gray')  # Display the grid
    plt.title(title)  # Add title to the plot
    
    if points:
        for set_of_points in points:
            ys, xs = zip(*points)
            plt.scatter(xs, ys, color='red', s=100, label='Points', alpha=0.6, edgecolors='white')
    plt.grid(True)
    plt.legend()
    plt.show()


# ── Layer-separated SVG rendering ──────────────────────────────────────────
def _render_layer_svg(board, layer_name: str, router_list=None):
    """
    Render a single layer of the board to an SVG Figure.

    Draws:
      • Segments (traces + buses) that belong to this layer
      • Annular rings (vias) on this layer
      • Sockets whose nets are assigned to this layer

    Parameters:
        board:        Board instance (has .layers, .sockets, .width, .height, etc.)
        layer_name:   e.g. "F_Cu.gtl" or "B_Cu.gbl"
        router_list:  Optional list of BusRouter instances whose paths_indices 
                      should also be drawn (for in-progress routing before 
                      segments have been finalised onto the board layers).

    Returns:
        matplotlib.figure.Figure ready to be saved.
    """
    layer = board.get_layer(layer_name)
    if not layer:
        return None

    color = _layer_color(layer_name)
    alpha = LAYER_ALPHA

    # Size the figure proportionally to the board so the SVG has
    # the correct aspect ratio and no dead space.
    scale_factor = 100  # pixels-per-mm  (at dpi=100 this gives 1 inch per mm)
    fig_w = board.width * scale_factor / 100   # inches
    fig_h = board.height * scale_factor / 100  # inches
    # Clamp to a reasonable range
    fig_w = max(4, min(fig_w, 16))
    fig_h = max(4, min(fig_h, 16))

    fig = Figure(figsize=(fig_w, fig_h), dpi=100)
    FigureCanvas(fig)
    ax = fig.add_subplot(111)
    fig.patch.set_facecolor('none')
    ax.axis("off")

    # ── 1. Draw finalised segments on this layer (traces + buses) ──
    seg_lines = []
    for seg in layer.segments:
        try:
            seg_lines.append([(seg.start.x, seg.start.y), (seg.end.x, seg.end.y)])
        except Exception:
            continue
    if seg_lines:
        lc = LineCollection(seg_lines, colors=[color], linewidths=1, alpha=alpha)
        ax.add_collection(lc)

    # ── 2. Draw in-progress route indices from routers (not yet on the layer) ──
    if router_list:
        for router in router_list:
            # Only draw routes whose nets belong to *this* layer
            for net_name, paths in router.paths_indices.items():
                net_layer = board.get_layer_for_net(net_name)
                # The trace belongs to the router's tracks_layer
                trace_layer_name = router.tracks_layer.name
                if trace_layer_name != layer_name:
                    continue
                for path in paths:
                    if len(path) < 2:
                        continue
                    points = [router._indices_to_point(x, y).as_tuple() for x, y, _ in path]
                    lc = LineCollection([points], colors=[color], linewidths=1, alpha=alpha)
                    ax.add_collection(lc)

            # Draw buses that live on this layer
            if router.buses_layer and router.buses_layer.name == layer_name:
                for seg in router.buses_layer.segments:
                    try:
                        bl = [(seg.start.x, seg.start.y), (seg.end.x, seg.end.y)]
                        blc = LineCollection([bl], colors=[color], linewidths=1.5, alpha=alpha)
                        ax.add_collection(blc)
                    except Exception:
                        continue

            # Draw vias from router indices (before they are converted)
            for net_name, vias in router.vias_indices.items():
                for vx, vy in vias:
                    pt = router._indices_to_point(vx, vy)
                    ax.add_patch(MplCircle((pt.x, pt.y), radius=0.15, color=color, alpha=alpha, linewidth=0))

    # ── 3. Draw annular rings (vias) already committed to the layer ──
    via_radius = getattr(board.loader, "via_diameter", 0.3) / 2
    for ring in layer.annular_rings:
        ax.add_patch(MplCircle((ring.x, ring.y), radius=via_radius, color=color, alpha=alpha, linewidth=0))

    # ── 4. Draw sockets for this layer ──
    if board.sockets:
        try:
            sockets = board.sockets.get_socket_positions_for_nets(layer.nets)
            for _, positions in sockets.items():
                if not positions:
                    continue
                xs = [p[0] for p in positions]
                ys = [p[1] for p in positions]
                ax.scatter(xs, ys, s=6, c="#111111", alpha=0.7, zorder=6)
        except Exception:
            pass

    # ── 5. Axes limits ──
    padding = max(board.width, board.height) * 0.05
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-board.width / 2 - padding, board.width / 2 + padding)
    ax.set_ylim(-board.height / 2 - padding, board.height / 2 + padding)
    fig.tight_layout(pad=0)

    return fig


def save_layer_svg(board, layer_name: str, output_path, router_list=None) -> None:
    """
    Save a layer-separated SVG to disk.

    Parameters:
        board:        Board instance.
        layer_name:   e.g. "F_Cu.gtl" or "B_Cu.gbl"
        output_path:  File path for SVG output.
        router_list:  Optional list of BusRouter instances (for in-progress routes).
    """
    fig = _render_layer_svg(board, layer_name, router_list=router_list)
    if fig is None:
        return
    os.makedirs(PathLib(output_path).parent, exist_ok=True)
    fig.savefig(output_path, transparent=True, format='svg')
    fig.clear()


def save_front_back_svgs(board, output_folder, router_list=None) -> None:
    """
    Convenience: save both front.svg and back.svg for a board.

    Parameters:
        board:         Board instance.
        output_folder: Folder to write front.svg / back.svg into.
        router_list:   Optional list of BusRouter instances (in-progress routes).
    """
    output_folder = PathLib(output_folder)
    os.makedirs(output_folder, exist_ok=True)
    save_layer_svg(board, "F_Cu.gtl", output_folder / "front.svg", router_list=router_list)
    save_layer_svg(board, "B_Cu.gbl", output_folder / "back.svg", router_list=router_list)


def show_segments_sockets(segments, socket_locations):
    """
    Displays the line segments and socket locations.

    Args:
        socket_locations (dict): Dictionary with net names as keys and lists of tuples (x, y) as socket locations.
        segments (dict): Dictionary with net names as keys and lists of line segments, where each segment is a tuple of start and end coordinate tuples.
    """
    plt.figure(figsize=(7, 7))

    # Define colors for different nets, ensure there's a default color if net not listed
    colors = {'JD_PWR': 'red', 'JD_GND': 'blue', 'JD_DATA': 'green', 'default': 'gray'}

    # Plot the socket locations
    for net_type, positions in socket_locations.items():
        xs, ys = zip(*positions)
        plt.scatter(xs, ys, color=colors.get(net_type, 'black'), s=100, label=net_type, alpha=0.6, edgecolors='white')

    # Plot the segments
    for net_type, paths in segments.items():
        for start, end in paths:
            start_x, start_y = start
            end_x, end_y = end
            plt.plot([start_x, end_x], [start_y, end_y], color=colors.get(net_type, 'black'), linewidth=2, alpha=0.75)

    plt.grid(True)  # Optional: Can be removed if a cleaner look is preferred
    plt.legend(title='Net Types')
    plt.gca().set_aspect('equal', adjustable='datalim')
    plt.gca().invert_yaxis()  # Invert y-axis to match traditional Cartesian coordinate system
    plt.show()
    
def show_grid_segments_sockets(grid, segments, socket_locations, resolution):
    """
    Displays the grid with keep out zones, line segments, and socket locations.

    Args:
        grid (numpy.array): The grid, where 1 represents keep out zones.
        segments (dict): Dictionary with net names as keys and lists of line segments.
        socket_locations (dict): Dictionary with net names as keys and lists of tuples (x, y) as socket locations.
        resolution (float): The resolution of the grid, for scaling the socket and segment coordinates.
    """
    plt.figure(figsize=(7, 7))
    center_x, center_y = grid.shape[1] // 2, grid.shape[0] // 2

    # Calculate the correct extents to align the grid cells with the axes
    extent = [-center_x * resolution, center_x * resolution, -center_y * resolution, center_y * resolution]
    
    # Display the grid with keep out zones
    plt.imshow(grid, cmap='gray_r', interpolation='nearest', extent=extent)
 
    # Define colors for different nets
    colors = {'JD_PWR': 'red', 'JD_GND': 'blue', 'JD_DATA': 'green', 'default': 'gray'}

    # Plot socket locations
    for net_type, positions in socket_locations.items():
        xs, ys = zip(*[(x, -y) for x, y in positions]) # Invert y-axis
        plt.scatter([x for x in xs], [y for y in ys], color=colors.get(net_type, colors['default']), s=100, label=net_type, alpha=0.6, edgecolors='white')

    # Plot the segments
    for net_type, paths in segments.items():
        for start, end in paths:
            start_x, start_y = start
            end_x, end_y = end
            plt.plot([start_x, end_x], [-start_y, -end_y], color=colors.get(net_type, colors['default']), linewidth=2, alpha=0.75) # Invert y-axis
        

    plt.grid(True)  # This can be turned off for a cleaner look
    plt.legend(title='Net Types')
    plt.gca().set_aspect('equal', adjustable='datalim')
    plt.gca().invert_yaxis()  # Invert y-axis to match traditional Cartesian coordinate systems
    plt.show()
    
def plot_zones(zones, output_file="debug_zones.gbr", trace_width=0.1, output_dir="./output"):
    """
    Draws rectangles on a Gerber file for debugging purposes.

    Args:
        rectangles (list): List of rectangles, where each rectangle is represented as a list of 4 tuples (x, y).
        output_file (str): Name of the output Gerber file. Defaults to "debug1.gbr".
        trace_width (float): Width of the rectangle edges in mm. Defaults to 0.15 mm.
        output_dir (str): Directory to store the generated Gerber file. Defaults to "./output".

    Returns:
        None
    """
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Create a DataLayer for the debug rectangles
    debug_layer = DataLayer("Debug,Rectangles", negative=False)

    # Loop through the rectangles and draw them
    for zone in zones:
        # Create a path for each rectangle
        path = Path()
        path.moveto(zone[0])  # Move to the first point
        for point in zone[1:]:
            path.lineto(point)  # Draw lines to subsequent points
        path.lineto(zone[0])  # Close the rectangle by connecting back to the first point

        # Add the rectangle path to the layer
        debug_layer.add_traces_path(path, trace_width, "DebugRectangle")

    # Generate the output file path
    file_path = os.path.join(output_dir, output_file)

    # Write the Gerber content to the file
    with open(file_path, 'w') as file:
        file.write(debug_layer.dumps_gerber())

    print(f"Debug Gerber file saved at: {file_path}")

def plot_sockets(socket_locations: Union[Dict[str, List[Tuple[float, float]]], List[Tuple[float, float]]],
                output_file: Union[str, PathLib] = "debug_sockets.gbr", 
                tool_diameter: float = 0.5, 
                output_dir: Union[str, PathLib] = "./output"):
    """
    Draws socket points on a Gerber file for debugging purposes.

    Args:
        socket_locations: Either:
            - Dictionary with net names as keys and lists of (x, y) coordinates as values
            - List of (x, y) coordinates
        output_file (str or Path): Name of the output Gerber file. Defaults to "debug_sockets.gbr".
        tool_diameter (float): Diameter of the circle in mm. Defaults to 0.5mm.
        output_dir (str or Path): Directory to store the generated Gerber file. Defaults to "./output".

    Returns:
        None
    """
    # Convert paths to strings if necessary
    output_dir = PathLib(output_dir)
    
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Create a DataLayer for the debug circles (points)
    debug_layer = DataLayer("Debug,Circles", negative=False)

    # Process points based on input type
    if isinstance(socket_locations, dict):
        # Handle dictionary of points by net
        for net_name, points in socket_locations.items():
            for point in points:
                path = Path()
                path.moveto(point)  # Move to the location of the point
                path.lineto(point)  # Draw a single line
                # Add the point to the layer
                debug_layer.add_traces_path(path, tool_diameter, f"DebugCircle_{net_name}")
    else:
        # Handle list of points directly
        for point in socket_locations:
            path = Path()
            path.moveto(point)
            path.lineto(point)
            debug_layer.add_traces_path(path, tool_diameter, "DebugCircle")

    # Generate the output file path
    file_path = output_dir / output_file

    # Write the Gerber content to the file
    with open(file_path, 'w') as file:
        file.write(debug_layer.dumps_gerber())

    print(f"Debug Gerber file saved at: {file_path}")
