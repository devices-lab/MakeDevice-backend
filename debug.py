import os
import sys
import subprocess
import matplotlib.pyplot as plt
import numpy as np
from gerber_writer import DataLayer, Path
from pathlib import Path as PathLib
from typing import Dict, List, Tuple, Union
from matplotlib.colors import ListedColormap

frame_index = 0
do_video = True

from thread_context import thread_context

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

def show_grid_routes_sockets(keepout_grid, routes, socket_locations, resolution):
    """
    Displays the grid with keep out zones, route indices (shown on grid as lines), and socket locations.

   Args:
        grid (numpy.array): The grid, where 1 represents keep out zones.
        segments (dict): Dictionary with net names as keys and lists of line segments.
        routes (dict): A dictionary where each key is a net name and the value is a list of lists containing paths 
        with points as tuples.
        resolution (float): The resolution of the grid, for scaling the socket and segment coordinates.
    """
    scale = 2
    plt.figure(figsize=((keepout_grid.shape[1] * scale) / 100, (keepout_grid.shape[0] * scale) / 100))  # Set the figure size

    plt.gcf().patch.set_facecolor('none') # Transparent (instead of 'black')
    plt.axis('off')

    colors = [(1, 1, 1, 0), (0, 0, 0, 1)]  # white transparent for 0s, black for 1s
    new_cmap = ListedColormap(colors)

    # empty_grid is just the first and last pixel of the grid, so two pixels
    # this is to ensure the image starts at its full size, so it doesn't change size when traces are drawn
    empty_grid = np.zeros((keepout_grid.shape[0], keepout_grid.shape[1], 4), dtype=float)  # RGBA format

    # Draw the top left, and bottom right pixels of the image, to ensure its size won't change
    plt.imshow(empty_grid, cmap=new_cmap, interpolation='nearest', extent=None)
    # Draw the actual keepouts (comment out for transparent image)
    # plt.imshow(keepout_grid, cmap='binary', interpolation='nearest', extent=None)
    
    # Define colors for different nets, ensure there's a default color if net not listed
    # set_colors = {
    #     'JD_PWR': 'red',
    #     'JD_GND': 'white',
    #     'JD_DATA': 'yellow',
    #     'GND': 'white', 
    #     'SWCLK': 'blue',
    #     'SWDIO~': 'green',
    #     'SWDIO~^': 'lightgreen',
    #     'RESET': 'orange',
    #     'default': 'gray'
    # }

    set_colors = { 'default': 'black' }

    # Default color for a different key
    colors = lambda key: set_colors[key] if key in set_colors else set_colors['default']

    # Center coordinates for plotting
    center_x, center_y = keepout_grid.shape[1] // 2, keepout_grid.shape[0] // 2

    # Add the socket locations to the plot, categorized by type
    for net_type, positions in socket_locations.items():
        for (x, y) in positions:
            # Adjust coordinates for the plot: shifting origin to the center of the grid
            plot_x = (center_y + int(y / resolution))  # Adjust for numpy's row-major order (flip x and y)
            plot_y = (center_x + int(x / resolution))

            # Invert the x axis to match the traditional Cartesian coordinate system
            plot_x = keepout_grid.shape[0] - plot_x

            # plt.scatter(plot_y, plot_x, c=colors(net_type), s=100, label=net_type, alpha=0.3)
            plt.scatter(plot_y, plot_x, c=colors(net_type), s=10, alpha=1.0)

     # Draw the routes
    for net_type, paths in routes.items():
        for path in paths:
            if path:  # Ensure there is a valid path
                # print(path)
                path_x, path_y, path_z = zip(*path)  # Coordinates are directly usable, no need for center adjustment
                plt.plot(path_x, path_y, c=colors(net_type), linewidth=1, alpha=1.0, antialiased=False)  # Use the same color as the sockets

    # Group lavels with the same name
    # handles, labels = plt.gca().get_legend_handles_labels()
    # by_label = dict(zip(labels, handles))
    # plt.legend(by_label.values(), by_label.keys())

    plt.grid(False)

    plt.tight_layout(pad=0)
    # plt.legend(title='Jacdac nets')
    frame(plt)

def frame(plt):
    """
    Saves the current plot as a frame for a video.
    """
    # FIX: Look into possibility of frame_index >0 when starting
    global frame_index
    routing_imgs_folder = thread_context.job_folder / "routing_imgs"
    # Make the folder if it doesn't exist
    os.makedirs(routing_imgs_folder, exist_ok=True)

    try:
        plt.savefig(routing_imgs_folder / f"{frame_index}.png", transparent=True)
    except Exception as e:
        print(f"🔴 Error saving frame {frame_index}: {e}")
    frame_index += 1

def video(name=""):
    """
    Generates a video from the frames saved in the debug folder, then removes the folder
    """

    # Target a 10 second video
    rate = float(frame_index) / 10.0

    subprocess.run(
        f"ffmpeg -y -framerate {rate} -i debug/frame_%d.png -c:v libx264 -pix_fmt yuv420p -crf 18 -preset veryfast debug_{name}.mp4",
        shell=True,
        check=True
    )

    # Remove the debug folder
    for file in os.listdir("debug"):
        os.remove(f"debug/{file}")
    os.rmdir("debug")

    print(f"🟢 Generated debug_{name}.mp4")

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
