import matplotlib.pyplot as plt
import numpy as np

def print_full_array(array):
    # Temporarily set NumPy print options to display the entire array
    with np.printoptions(threshold=np.inf):
        print(array)


def show_plot(grid, socket_locations, routes, resolution=0.1):
    plt.figure(figsize=(10, 10))  # Set the figure size
    plt.imshow(grid, cmap='gray', interpolation='nearest')  # Display the grid
    
    # Define colors or markers for different types of sockets
    colors = {'JD_PWR': 'red', 'JD_GND': 'blue', 'JD_DATA': 'green'}
    
    # Center coordinates for plotting
    center_x, center_y = grid.shape[1] // 2, grid.shape[0] // 2

    # Add the socket locations to the plot, categorized by type
    for net_type, positions in socket_locations.items():
        for (x, y) in positions:
            # Adjust coordinates for the plot: shifting origin to the center of the grid
            plot_x = (center_y + int(y)/resolution)  # Adjust for numpy's row-major order (flip x and y)
            plot_y = (center_x + int(x)/resolution)
            plt.scatter(plot_y, plot_x, c=colors[net_type], s=100, label=net_type, alpha=0.6)

     # Draw the routes
    for net_type, paths in routes.items():
        for path in paths:
            if path:  # Ensure there is a valid path
                path_x, path_y = zip(*[(center_y + int(p[0]), center_x + int(p[1])) for p in path])
                plt.plot(path_y, path_x, c=colors[net_type], linewidth=2, alpha=0.5)  # Use the same color as the sockets
                
    plt.colorbar()
    plt.grid(True)
    plt.legend(title='Net Types')
    plt.show()