import numpy as np
import math
from heapq import heappush, heappop
from collections import deque

def create_grid(dimensions, keep_out_zones, resolution):
    """
    Create an array grid for the pathfinding algorithm. 

    Args:
        dimensions (dict): A dictionary with 'x' and 'y' keys representing the width and height 
                           of the grid in units (e.g., millimeters).
        keep_out_zones (list of tuples): Each tuple contains four points
                                         (top_left, top_right, bottom_right, bottom_left) representing
                                         a rectangle in the same units as dimensions. Those are the keep-out
                                         zones, where the algorithm will avoid routing.
        resolution (float): The size of each grid cell in units. Coordinate values are rounded up to the
                            nearest resolution value. Increasing the resolution will result in a larger grid,
                            hence increasing the precision at the cost of increased computation time.

    Returns:
        numpy.ndarray: A 2D grid where 0 represents a free cell and 1 represents a blocked cell.
    """
    
    width = dimensions['x']
    height = dimensions['y']
    grid_width = math.ceil(width / resolution)
    grid_height = math.ceil(height / resolution)

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
        grid[y1:y2, x1:x2] = 1

    return grid

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def a_star_search(grid, start, goal):
    neighbors = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    grid_shape = grid.shape

    # Initialize for pathfinding
    gscore = np.full(grid_shape, np.inf)
    fscore = np.full(grid_shape, np.inf)
    close_set = np.zeros(grid_shape, dtype=bool)
    came_from = {}

    # Start node scores
    gscore[start] = 0
    fscore[start] = heuristic(start, goal)

    open_set = []
    heappush(open_set, (fscore[start], start))

    while open_set:
        current = heappop(open_set)[1]

        if current == goal:
            return reconstruct_path(came_from, current)

        close_set[current] = True
        for i, j in neighbors:
            neighbor = (current[0] + i, current[1] + j)

            if 0 <= neighbor[0] < grid_shape[0] and 0 <= neighbor[1] < grid_shape[1]:
                # Allow stepping into the keep-out zone if it's the goal node
                if neighbor == goal or not grid[neighbor]:
                    tentative_g_score = gscore[current] + 1  # Uniform cost assumed

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

def breadth_first_search(grid, start, goal):
    neighbors = [(0, 1), (1, 0), (0, -1), (-1, 0)]
    grid_shape = grid.shape

    # Initialize for pathfinding
    visited = np.zeros(grid_shape, dtype=bool)
    came_from = {}

    # Start node
    queue = deque([start])
    visited[start] = True

    while queue:
        current = queue.popleft()

        if current == goal:
            return reconstruct_path(came_from, current)

        for i, j in neighbors:
            neighbor = (current[0] + i, current[1] + j)

            if 0 <= neighbor[0] < grid_shape[0] and 0 <= neighbor[1] < grid_shape[1]:
                if not visited[neighbor]:
                    # Allow stepping onto the goal even if it is in a keep-out zone
                    if neighbor == goal or grid[neighbor] == 0:
                        queue.append(neighbor)
                        visited[neighbor] = True
                        came_from[neighbor] = current

    return False

def calculate_net_distances(socket_locations, resolution):
    net_distances = {}
    for net, locations in socket_locations.items():
        distances = []
        for i in range(len(locations) - 1):
            for j in range(i + 1, len(locations)):
                loc_i = locations[i]
                loc_j = locations[j]
                dist = heuristic((loc_i[0] / resolution, loc_i[1] / resolution), (loc_j[0] / resolution, loc_j[1] / resolution))
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
                    
def apply_socket_keep_out_zones(grid, socket_locations, current_net, resolution, keep_out_mm=1):
    """
    Applies keep-out zones around sockets in other nets. This is essential for ensuring that the routes
    on a given layer do not cut through vias on their respetive layers. Keep-out zones around sockets 
    are applied as a square around each socket point.

    Args:
        grid (numpy.array): Current grid with already applied keep-out zones.
        socket_locations (dict): Locations of the sockets by net.
        current_net (string): Name of the net currently being processed.
        resolution (float): Units per grid cell, defining the scale of the grid.
        keep_out_mm (int): Radius of the keep-out zone in millimeters. Default is 1mm. 

    Returns:
        numpy.ndarray: Updated grid with the additional keep-out zones applied.
    """
    temp_grid = np.copy(grid)
    keep_out_cells = int(np.ceil(keep_out_mm / resolution))  # Convert mm to grid cells

    for net, locations in socket_locations.items():
        if net != current_net:  # Apply keep-out zones only for other nets
            for x, y in locations:
                x_index = int(x / resolution) + grid.shape[1] // 2
                y_index = int(y / resolution) + grid.shape[0] // 2
                # Apply keep-out zone around the socket
                for i in range(-keep_out_cells, keep_out_cells + 1):
                    for j in range(-keep_out_cells, keep_out_cells + 1):
                        xi = x_index + i
                        yi = y_index + j
                        if 0 <= xi < grid.shape[1] and 0 <= yi < grid.shape[0]:
                            temp_grid[yi, xi] = 1  # Mark this position as blocked

    return temp_grid
                    
def route_sockets(grid, socket_locations, resolution, algorithm='breadth_first', debug=False):
    """
    Performs routing for each Gerber Socket on the same net, based on the grid with the keep-out zones. Also
    applies additional keep-out zones for the socket on other nets to avoid shorts with vias.

    Args:
        grid (numpy.array): The grid on which to perform the routing, with obstacles marked.
        socket_locations (dict): A dictionary of socket locations grouped by net names.
        resolution (float): The resolution of the grid in units per grid cell.
        algorithm (str): Optional, the pathfinding algorithm to use, either 'a_star' or 'breadth_first'.
            Default is 'breadth_first'.

    Returns:
        dict: A dictionary of nets and segments, where each key is a net name and the value is a list of tuples of line segments
                ((start_x, start_y), (end_x, end_y)) in the Gerber coordinates.
    """    
    routes = {}
    net_distances = calculate_net_distances(socket_locations, resolution)
    
    for net, distances in net_distances.items():
        temp_grid = apply_socket_keep_out_zones(grid, socket_locations, net, resolution)
        uf = UnionFind([tuple(loc) for loc in socket_locations[net]])  # Using tuples as UnionFind elements
        
        for dist, loc1, loc2 in distances:
            if uf.find(tuple(loc1)) != uf.find(tuple(loc2)):
                start_index = (int(loc1[1] / resolution) + temp_grid.shape[0] // 2, int(loc1[0] / resolution) + temp_grid.shape[1] // 2)
                end_index = (int(loc2[1] / resolution) + temp_grid.shape[0] // 2, int(loc2[0] / resolution) + temp_grid.shape[1] // 2)
                
                if algorithm == 'a_star':
                    path = a_star_search(temp_grid, start_index, end_index)
                else:
                    path = breadth_first_search(temp_grid, start_index, end_index)
                
                if path:
                    routes.setdefault(net, []).append(path)
                    uf.union(tuple(loc1), tuple(loc2))
    
    # For debug purposes only
    if debug:
        return routes
    
    # Get the centers of the grid for translating the indices
    center_x = grid.shape[0] // 2
    center_y = grid.shape[1] // 2
    
    # Consolidate the the list of grid indices into line segments on the coordinate plane
    segments = consolidate_segments(routes, resolution, center_x, center_y)
    
    return segments

def route_sockets_deprecated(grid, socket_locations, resolution, algorithm='breadth_first'):
    """ This is a previous implementation of the route_sockets function. It simply routes each socket within a net
    to the next one in the list. The new implementation is more optimized and routes sockets based on the distance between
    them.

    Args:
        grid (numpy.array): The grid on which to perform the routing, with obstacles marked.
        socket_locations (dict): A dictionary of socket locations grouped by net names.
        resolution (float): The resolution of the grid in units per grid cell.
        algorithm (str): Optional, the pathfinding algorithm to use, either 'a_star' or 'breadth_first'.
            Default is 'breadth_first'.

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
        
        # Apply keep-out zones for socket in nets
        temp_grid = apply_socket_keep_out_zones(grid, socket_locations, net, resolution)
        
        # Connect each socket with the next one in the list
        for i in range(len(locations) - 1):
            start = locations[i]
            end = locations[i + 1]
            # Convert real-world coordinates to grid indices considering the resolution
            start_index = (center_y + int(start[1] / resolution), center_x + int(start[0] / resolution))
            end_index = (center_y + int(end[1] / resolution), center_x + int(end[0] / resolution))

            if algorithm == 'a_star':
                path = a_star_search(temp_grid, start_index, end_index)
            else:   
                path = breadth_first_search(temp_grid, start_index, end_index)
                
            net_routes.append(path if path else None)

        routes[net] = net_routes

    return routes

def consolidate_segments(routes, resolution, center_x, center_y):
    """
    Consolidates contiguous line segments into longer lines. This translates the indices from the grid to 
    line ednpoints that can be used for creating traces using `gerber-writer`.

    Args:
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
            real_start = ((start[1] - center_x) * resolution, (center_y - start[0]) * resolution * -1) # Invert y-axis
            real_end = ((end[1] - center_x) * resolution, (center_y - end[0]) * resolution * -1) # Invert y-axis
            real_world_paths.append((real_start, real_end))

        consolidated_routes[net] = real_world_paths

    return consolidated_routes