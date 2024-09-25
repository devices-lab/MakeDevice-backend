import matplotlib.pyplot as plt
import numpy as np

def generate_test_grid(dimensions):
    width, height = dimensions
    grid = np.zeros((width, height), dtype=int)
    return grid

def print_full_array(array):
    # Temporarily set NumPy print options to display the entire array
    with np.printoptions(threshold=np.inf):
        print(array)

def show_grid(grid):
    plt.figure(figsize=(7, 7))  # Set the figure size
    # Calculate the correct extents to align the grid cells with the axes
    extent = [0, grid.shape[1], 0, grid.shape[0]]
    plt.imshow(grid, cmap='gray', interpolation='nearest', extent=extent)  # Display the grid
    plt.grid(True)
    plt.show()

def show_grid_routes_sockets(grid, routes, socket_locations, resolution):
    """
    Displays the grid with keep out zones, route indices (shown on grid as lines), and socket locations.

   Args:
        grid (numpy.array): The grid, where 1 represents keep out zones.
        segments (dict): Dictionary with net names as keys and lists of line segments.
        routes (dict): A dictionary where each key is a net name and the value is a list of lists containing paths 
        with points as tuples.
        resolution (float): The resolution of the grid, for scaling the socket and segment coordinates.
    """
    plt.figure(figsize=(7, 7))  # Set the figure size
    extent = [0, grid.shape[1], 0, grid.shape[0]]
    plt.imshow(grid, cmap='gray', interpolation='nearest', extent=None)  # Display the grid
    
    # Define colors for different nets, ensure there's a default color if net not listed
    colors = {'JD_PWR': 'red', 'JD_GND': 'blue', 'JD_DATA': 'green', 'default': 'gray'}

    # Center coordinates for plotting
    center_x, center_y = grid.shape[1] // 2, grid.shape[0] // 2

    # Add the socket locations to the plot, categorized by type
    for net_type, positions in socket_locations.items():
        for (x, y) in positions:
            # Adjust coordinates for the plot: shifting origin to the center of the grid
            plot_x = (center_y + int(y / resolution))  # Adjust for numpy's row-major order (flip x and y)
            plot_y = (center_x + int(x / resolution))
            plt.scatter(plot_y, plot_x, c=colors[net_type], s=100, label=net_type, alpha=0.6)

     # Draw the routes
    for net_type, paths in routes.items():
        for path in paths:
            if path:  # Ensure there is a valid path
                path_y, path_x = zip(*path)  # Coordinates are directly usable, no need for center adjustment
                plt.plot(path_x, path_y, c=colors[net_type], linewidth=2, alpha=0.6)  # Use the same color as the sockets
                
    plt.grid(True)
    plt.legend(title='Jacdac nets')
    plt.show()

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