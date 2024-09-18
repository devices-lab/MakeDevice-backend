import numpy as np
import math
from heapq import heappush, heappop

def create_grid(dimensions, keep_out_zones, resolution=0.1):
    """
    Create a grid for pathfinding where (0,0) is at the center of the grid.

    Parameters:
        dimensions (tuple): The full width and height of the grid in units (e.g., millimeters).
        keep_out_zones (list of tuples): Each tuple contains four points
                                         (top_left, top_right, bottom_right, bottom_left) representing
                                         a rectangle in the same units as dimensions.
        resolution (float): The size of each grid cell in units. Default is 1.0.

    Returns:
        numpy.ndarray: A 2D grid where 0 represents a free cell and 1 represents a blocked cell.
    """
    width, height = dimensions
    grid_width = math.ceil(width / resolution)
    grid_height = math.ceil(height / resolution)

    # Ensure grid dimensions are even numbers
    if grid_width % 2 != 0:
        grid_width += 1
    if grid_height % 2 != 0:
        grid_height += 1

    # Initialize grid to all zeros (free)
    grid = np.zeros((grid_height, grid_width), dtype=int)

    # Middle of the grid
    center_x, center_y = grid_width // 2, grid_height // 2

    # Mark keep-out zones in the grid
    for zone in keep_out_zones:
        top_left, top_right, bottom_right, bottom_left = zone
        # Convert points to grid indices, adjusting for the center
        x1 = center_x + int(min(top_left[0], bottom_left[0]) / resolution)
        x2 = center_x + int(max(top_right[0], bottom_right[0]) / resolution)
        y1 = center_y + int(min(top_left[1], top_right[1]) / resolution)
        y2 = center_y + int(max(bottom_left[1], bottom_right[1]) / resolution)
        
        # Normalize for array boundaries
        x1, x2 = max(0, x1), min(grid_width-1, x2)
        y1, y2 = max(0, y1), min(grid_height-1, y2)
        
        # Mark cells as blocked
        grid[y1:y2+1, x1:x2+1] = 1

    return grid

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def a_star_search(grid, start, goal):
    neighbors = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    grid_shape = grid.shape

    # Use a NumPy array for gscore, fscore, and closed set for faster access and updates
    gscore = np.full(grid_shape, np.inf)
    fscore = np.full(grid_shape, np.inf)
    close_set = np.zeros(grid_shape, dtype=bool)

    # Maps for reconstructing path
    came_from = {}
    
    # Start node initialization
    gscore[start] = 0
    fscore[start] = heuristic(start, goal)

    open_set = []
    heappush(open_set, (fscore[start], start))

    while open_set:
        current = heappop(open_set)[1]

        if current == goal:
            # Reconstruct path
            return reconstruct_path(came_from, current)

        close_set[current] = True
        for i, j in neighbors:
            neighbor = (current[0] + i, current[1] + j)

            if 0 <= neighbor[0] < grid_shape[0] and 0 <= neighbor[1] < grid_shape[1]:
                if grid[neighbor] or close_set[neighbor]:
                    continue

                tentative_g_score = gscore[current] + 1  # Assuming uniform cost

                if tentative_g_score < gscore[neighbor]:
                    came_from[neighbor] = current
                    gscore[neighbor] = tentative_g_score
                    fscore[neighbor] = tentative_g_score + heuristic(neighbor, goal)
                    heappush(open_set, (fscore[neighbor], neighbor))

    return False

def reconstruct_path(came_from, current):
    path = []
    while current in came_from:
        path.append(current)
        current = came_from[current]
    path.append(current)
    return path[::-1]


def route_sockets(grid, socket_locations):
    """
    Routes sockets based on the A* algorithm for each net type and returns the paths.

    Parameters:
        grid (numpy.array): The grid on which to perform the routing, with obstacles marked.
        socket_locations (dict): A dictionary of socket locations grouped by net names.

    Returns:
        dict: A dictionary where each key is a net name and the value is a list of lists containing paths 
        with points as tuples.
    """
    routes = {}  # This will store the paths for each net type

    # Middle of the grid, used to translate coordinates
    center_x, center_y = grid.shape[1] // 2, grid.shape[0] // 2

    # Process each net type
    for net, locations in socket_locations.items():
        net_routes = []  # Store routes for this net
        # Assume you want to connect each socket with the next one in the list
        for i in range(len(locations) - 1):
            start = locations[i]
            end = locations[i + 1]
            # Convert real-world coordinates to grid indices
            start_index = (center_y + int(start[1]), center_x + int(start[0]))
            end_index = (center_y + int(end[1]), center_x + int(end[0]))
            # Perform A* search
            path = a_star_search(grid, start_index, end_index)
            if path:
                net_routes.append(path)
            else:
                net_routes.append(None)  # In case no path is found

        routes[net] = net_routes

    return routes