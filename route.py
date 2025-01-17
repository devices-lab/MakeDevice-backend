import math
import numpy as np
from pathfinding.core.diagonal_movement import DiagonalMovement
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.finder.breadth_first import BreadthFirstFinder
from debug import show_grid, plot_debug_gerber

def to_grid_indices(x, y, center_x, center_y, resolution):
    """
    Converts Cartesian coordinates (x, y) to grid indices (row, col) based on the given center and resolution.

    Parameters:
        x (int): The x-coordinate in Cartesian space.
        y (int): The y-coordinate in Cartesian space.
        center_x (int): The x-coordinate of the grid center.
        center_y (int): The y-coordinate of the grid center.
        resolution (int): The resolution of the grid.

    Returns:
        tuple: A tuple (row, col) representing the grid indices.
    """
    row = int(center_y - (y / resolution))
    col = int(center_x + (x / resolution))
    return row, col

def create_grid(dimensions, keep_out_zones, resolution):
    """
    Create an numpy array grid for the pathfinding algorithm.
    
    Parameters:
        dimensions (dict): The width and height of the grid in units (e.g., millimeters).
        keep_out_zones (list of tuples): List of rectangles with four points 
                                         (bottom_left, top_left, top_right, bottom_right).
        resolution (float): The size of each grid cell in units. Coordinate values are rounded up to the
                            nearest resolution value. Increasing the resolution will result in a larger grid,
                            hence increasing the precision at the cost of increased computation time.
    
    Returns:
        numpy.ndarray: A 2D grid where 1 represents a free cell and 0 a blocked cell.
    """
    # Calculate grid dimensions in number of cells
    width = dimensions['x']
    height = dimensions['y']
    
    # Center coordinates of the grid
    grid_width = math.ceil(width / resolution)
    grid_height = math.ceil(height / resolution)
    center_x, center_y = grid_width // 2, grid_height // 2
    
    # Initialize grid with all ones (free cells)
    grid = np.ones((grid_height, grid_width), dtype=int)
    
    # Mark keep-out zones in the grid
    for zone in keep_out_zones:
        bottom_left, top_left, top_right, bottom_right = zone
        
        # Convert coordinates to grid indices
        y1, x1 = to_grid_indices(*top_left, center_x, center_y, resolution)
        y2, x2 = to_grid_indices(*bottom_right, center_x, center_y, resolution)
        
        # Ensure bounds are within grid limits
        x1 = max(0, min(grid_width - 1, x1))
        x2 = max(0, min(grid_width - 1, x2))
        y1 = max(0, min(grid_height - 1, y1))
        y2 = max(0, min(grid_height - 1, y2))
        
        # Mark cells in the rectangle as blocked
        grid[y1+1:y2, x1+1:x2] = 0 # IDK why, but adding +1 made the grid work correctly (assuming it's an index thing)

    return grid

def apply_socket_keep_out_zones(grid, socket_locations, current_net, resolution, keep_out_mm=1):
    """
    Applies keep-out zones around sockets in other nets. This is essential for ensuring that the routes
    on a given net do not cut through vias on other nets. These keep-out zones around the sockets are of 
    square shape. 
    
    Parameters:
        grid (numpy.array): Current grid (with already applied keep-out zones).
        socket_locations (dict): Locations of the sockets, organised by net.
        current_net (string): Name of the net currently being processed.
        resolution (float): Units per grid cell, defining the scale of the grid.
        keep_out_mm (int): Radius of the keep-out zone in millimeters. Defaults to 1mm. 
    Returns:
        numpy.ndarray: Updated 2D grid with the additional keep-out zones applied. On the 
                       grid, 0 is blocked, 1 is free.
    """
    temp_grid = np.copy(grid)
    keep_out_cells = int(np.ceil(keep_out_mm / resolution))  # Convert mm to grid cells

    # For debugging: list of rectangles for plotting
    # rectangles = []  

    for net, locations in socket_locations.items():
        for x, y in locations:
            
            # For debugging: add the keep-out zones as rectangle verices tuples to the list
            # x1 = x - keep_out_mm
            # x2 = x + keep_out_mm
            # y1 = y - keep_out_mm
            # y2 = y + keep_out_mm
            # rectangles.append(((x1, y1), (x2, y1), (x2, y2), (x1, y2))) # (bottom left, bottom right, top right, top left)

            x_index = int(x / resolution) + grid.shape[1] // 2
            y_index = int(-y / resolution) + grid.shape[0] // 2
                        
            # Apply keep-out zone around the socket
            for i in range(-keep_out_cells+1, keep_out_cells):
                for j in range(-keep_out_cells+1, keep_out_cells):
                    xi = x_index + i
                    yi = y_index + j
                    
                    # Check if the keep-out zone for the socket is within the grid boundaries
                    if 0 <= xi < grid.shape[1] and 0 <= yi < grid.shape[0]:
                        if net != current_net:
                            temp_grid[yi, xi] = 0 # Mark this position as blocked
                        else:
                            temp_grid[yi, xi] = 1 # Mark this position as free

    # For debugging: plot the rectangles on debug.gbr
    # plot_debug_gerber(rectangles, output_file="debug_keepouts.gbr")
    
    return temp_grid

def heuristic_diagonal(a, b):
    dx = abs(a[0] - b[0])
    dy = abs(a[1] - b[1])
    return (dx + dy) + (math.sqrt(2) - 2) * min(dx, dy)

def calculate_net_distances(socket_locations, resolution):
    """
    Calculate the net distances between socket locations, and sort them in ascending order.

    Parameters:
        socket_locations (dict): A dictionary where keys are net identifiers and
                                 values are lists of (x, y) tuples representing
                                 socket locations.
        resolution (float): The resolution factor to be applied to the coordinates.

    Returns:
        dict: A dictionary where keys are net identifiers and values are lists of
              tuples containing the distance and the pair of socket locations
              (distance, loc_i, loc_j), sorted by distance.
    """
    net_distances = {}
    for net, locations in socket_locations.items():
        distances = []
        for i in range(len(locations) - 1):
            for j in range(i + 1, len(locations)):
                loc_i = locations[i]
                loc_j = locations[j]
                dist = heuristic_diagonal((loc_i[0] / resolution, loc_i[1] / resolution), (loc_j[0] / resolution, loc_j[1] / resolution))
                distances.append((dist, loc_i, loc_j))
        distances.sort()
        net_distances[net] = distances
        
    return net_distances

class UnionFind:
    def __init__(self, elements):
        self.parent = {element: element for element in elements}
        self.rank = {element: 0 for element in elements}

    def find(self, element):
        if self.parent[element] != element:
            self.parent[element] = self.find(self.parent[element])
        return self.parent[element]

    def union(self, element1, element2):
        root1 = self.find(element1)
        root2 = self.find(element2)
        if root1 != root2:
            if self.rank[root1] > self.rank[root2]:
                self.parent[root2] = root1
            else:
                self.parent[root1] = root2
                if self.rank[root1] == self.rank[root2]:
                    self.rank[root2] += 1

def route_sockets(grid, socket_locations, resolution, algorithm="breadth_first", diagonals=True, debug=False):
    """
    Performs routing for each Gerber Socket on the same net, based on the grid with the keep-out zones. Also
    applies additional keep-out zones for the socket on other nets to avoid shorts with vias. The Union-Find 
    (also called Disjoint Set Union or DSU) is used to determine if two sockets belong to the same net, and
    if they are already connected. For each pair of sockets, if they are connected, no need to route again, 
    and if not, perform pathfinding - and if successful - union them together.

    Parameters:
        grid (numpy.array): The grid on which to perform the routing, with obstacles marked.
                            socket_locations (dict): A dictionary of socket locations grouped by net names.
        resolution (float): The resolution of the grid in units per grid cell.
        algorithm (str): Optional, the pathfinding algorithm to use, either 'a_star' or 'breadth_first'.
                         Default is 'breadth_first'.
        diagonals (bool): Optional, whether to allow diagonal movement in pathfinding. Default is True.
        
    Returns:
        dict: A dictionary of nets and segments, where each key is a net name and the value is a list of tuples of line segments
              ((start_x, start_y), (end_x, end_y)) in the Gerber coordinates.
    """    

    paths = {}
    net_distances = calculate_net_distances(socket_locations, resolution)
    
    # Center coordinates of the grid
    grid_width = grid.shape[1]
    grid_height = grid.shape[0]
    center_x, center_y = grid_width // 2, grid_height // 2
    
    print(f"Center of the panel <{center_x}, {center_y}>")

    for net, distances in net_distances.items():
        temp_grid = apply_socket_keep_out_zones(grid, socket_locations, net, resolution)
        uf = UnionFind([tuple(loc) for loc in socket_locations[net]])  # Using tuples as UnionFind elements
        
        for dist, loc1, loc2 in distances:
            # Check if the two locations are already connected in the union-find structure
            if uf.find(tuple(loc1)) != uf.find(tuple(loc2)):
                
                # Convert the start and end coordinates to grid indices
                start_index = to_grid_indices(-loc1[1], -loc1[0], center_x, center_y, resolution)
                end_index = to_grid_indices(-loc2[1], -loc2[0], center_x, center_y, resolution)
                
                # Pathfinding setup
                path_grid = Grid(matrix=temp_grid)
                
                if algorithm == "breadth_first":
                    finder = BreadthFirstFinder(diagonal_movement=(DiagonalMovement.always if diagonals else DiagonalMovement.never))
                if algorithm == "a_star":
                    finder = AStarFinder(diagonal_movement=(DiagonalMovement.always if diagonals else DiagonalMovement.never))
                
                print(path_grid)
                
                start = path_grid.node(start_index[0], start_index[1])
                end = path_grid.node(end_index[0], end_index[1])
                
                path, runs = finder.find_path(start, end, path_grid)
                print(f"🔵 Pathfinding runs: {runs}")
                
                if path:
                    print(f"🟢 Found path for net {net} between {loc1} and {loc2}")

                    # Convert GridNodes -> (row, col)
                    path_tuples = [(node.x, node.y) for node in path]
                    
                    # Add it to our dictionary
                    paths.setdefault(net, []).append(path_tuples)
                    
                    # Union-Find logic for an optimised routing strategy
                    uf.union(tuple(loc1), tuple(loc2))
                else:
                    print(f"🔴 No path found for net {net} between {loc1} and {loc2}")
    
    # Get the centers of the grid for translating the indices
    center_x = grid.shape[0] // 2
    center_y = grid.shape[1] // 2
    
    # Consolidate the the list of grid indices into line segments on the coordinate plane
    segments = consolidate_segments(paths, resolution, center_x, center_y)

    return segments
                
def consolidate_segments(routes, resolution, center_x, center_y):
    """
    Consolidates contiguous/overlaping line segments into longer lines. This translates the indices from the grid to 
    line ednpoints that can be used for creating traces using `gerber-writer`.

    Parameters:
        routes (dict): The routing paths indexed by net names, each path is a list of grid indices.
        resolution (float): The grid resolution.
        center_x (int): X-coordinate of the grid center.
        center_y (int): Y-coordinate of the grid center.

    Returns:
        dict: A dictionary where each key is a net name and the value is a list of line segments
              (start point, end point) in real-world coordinates.
    """
    consolidated_routes = {}

    for net, paths in routes.items():
        consolidated_paths = []
        for path in paths:
            if len(path) < 2:
                continue
            # Start the new segment
            current_segment_start = path[0]
            current_direction = None

            for i in range(1, len(path)):
                # Calculate direction
                previous = path[i - 1]
                current = path[i]
                direction = (current[0] - previous[0], current[1] - previous[1])

                if current_direction is None:
                    current_direction = direction
                elif direction != current_direction:
                    # Finish the current segment
                    consolidated_paths.append((current_segment_start, previous))
                    
                    # Start a new segment
                    current_segment_start = previous
                    current_direction = direction

                # Extend the segment
                if i == len(path) - 1:
                    consolidated_paths.append((current_segment_start, current))

        # Convert grid indices to real-world coordinates
        real_world_paths = []
        for start, end in consolidated_paths:
            real_start = ((start[0] - center_x) * resolution, (center_y - start[1]) * resolution)
            real_end = ((end[0] - center_x) * resolution, (center_y - end[1]) * resolution) 
            real_world_paths.append((real_start, real_end))

        consolidated_routes[net] = real_world_paths

    return consolidated_routes
