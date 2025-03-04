import math
import numpy as np
from collections import defaultdict
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.finder.breadth_first import BreadthFirstFinder
from pathfinding.core.diagonal_movement import DiagonalMovement

from pathfinding3d.core.grid import Grid as Grid3D
from pathfinding3d.finder.a_star import AStarFinder as AStarFinder3D
from pathfinding3d.finder.dijkstra import DijkstraFinder as DijkstraFinder3D
from pathfinding3d.finder.ida_star import IDAStarFinder as IDAStarFinder3D
from pathfinding3d.core.diagonal_movement import DiagonalMovement as DiagonalMovement3D

from manipulate import consolidate_segments, merge_overlapping_segments
from debug import plot_debug_gerber

BLOCKED_CELL = 0
FREE_CELL = 1
TUNNEL_CELL = 5

def to_grid_indices(x, y, center_x, center_y, resolution):
    """
    Converts Cartesian coordinates (x, y) to grid indices (column, row) based on the given center and resolution.

    Parameters:
        x (int): The x-coordinate in Cartesian space.
        y (int): The y-coordinate in Cartesian space.
        center_x (int): The x-coordinate of the grid center.
        center_y (int): The y-coordinate of the grid center.
        resolution (int): The resolution of the grid.

    Returns:
        tuple: A tuple (collumn, row) representing the grid indices.
    """
    column = int(center_x + (x / resolution))
    row = int(center_y - (y / resolution))
    return column, row

def invert_layer_mapping(layer_mapping):
    """
    Build a dict that allows quick lookup of which layer each net is on.
    Example result:
      {
        "JD_PWR": "F_Cu.gtl",
        "JD_DATA": "F_Cu.gtl",
        "JD_GND": "B_Cu.gbl",
      }
    """
    net_to_layer = {}
    for layer_file, info in layer_mapping.items():
        for net in info["nets"]:
            # Guard against empty or None in "nets" if needed.
            if net:
                net_to_layer[net] = layer_file
    return net_to_layer

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
    grid = np.full((grid_height, grid_width), FREE_CELL, dtype=int)
    
    # Mark keep-out zones in the grid
    for zone in keep_out_zones:
        bottom_left, top_left, top_right, bottom_right = zone
        
        # Convert coordinates to grid indices
        top_left_column_index, top_left_row_index = to_grid_indices(*top_left, center_x, center_y, resolution)
        bottom_right_column_index, bottom_right_row_index = to_grid_indices(*bottom_right, center_x, center_y, resolution)
        
        # Ensure bounds are within grid limits
        top_left_column_index = max(0, min(grid_width - 1, top_left_column_index))
        bottom_right_column_index = max(0, min(grid_width - 1, bottom_right_column_index))
        top_left_row_index = max(0, min(grid_height - 1, top_left_row_index))
        bottom_right_row_index = max(0, min(grid_height - 1, bottom_right_row_index))
        
        # Mark cells in the rectangle as blocked
        grid[top_left_row_index+1:bottom_right_row_index, top_left_column_index+1:bottom_right_column_index] = BLOCKED_CELL 

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
    rectangles = []  

    for net, locations in socket_locations.items():
        for x, y in locations:
            
            # For debugging: add the keep-out zones as rectangle verices tuples to the list
            x1 = x - keep_out_mm
            x2 = x + keep_out_mm
            y1 = y - keep_out_mm
            y2 = y + keep_out_mm
            rectangles.append(((x1, y1), (x2, y1), (x2, y2), (x1, y2))) # (bottom left, bottom right, top right, top left)

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
                            temp_grid[yi, xi] = BLOCKED_CELL # Mark this position as blocked
                        else:
                            temp_grid[yi, xi] = FREE_CELL # Mark this position as free

    # For debugging: plot the rectangles on debug.gbr
    plot_debug_gerber(rectangles, output_file="debug_keepouts.gbr")
    
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

def print_debug_grid(matrix, path=None, start=None, end=None):
    debug_grid = Grid(matrix=matrix)
    print(debug_grid.grid_str(path, start, end, show_weight=False))

    
def route_sockets(grid, socket_locations, configuration):
    
    # Unpack the JSON configuration
    algorithm = configuration['algorithm']
    allow_diagonal_traces = configuration['allow_diagonal_traces']
    resolution = configuration['resolution']
    layer_mapping = configuration['layer_mapping']
    
    # Net to layer mapping for quicker lookups
    net_to_layer_mapping = invert_layer_mapping(layer_mapping)
    
    paths = {} # {net: list of grid indeces (x, y) for path}
    previous_paths = defaultdict(list) # {layer_filename: list of path-indicies}
    
    # Calculate the distances between the sockets for each net
    net_distances = calculate_net_distances(socket_locations, resolution)
    
    # Center coordinates of the grid
    grid_height = grid.shape[0]
    grid_width = grid.shape[1]
    center_x, center_y = grid_width // 2, grid_height // 2
            
    for net, distances in net_distances.items():
        print(f"🟠 Routing net {net}")
        # Identify the layer for the current net (if any)
        current_layer = net_to_layer_mapping.get(net, None)
        other_nets_on_layer = False
        
        # Apply the socket keep-out zones - to either expose or block sockets from other nets
        current_matrix = apply_socket_keep_out_zones(grid, socket_locations, net, resolution)
        tunnel_matrix = np.copy(current_matrix) # Make a copy for later tunnelling
        
        # Block previously routed paths from all nets on the current layer
        if previous_paths[current_layer]:
            other_nets_on_layer = True
            for path_indexes in previous_paths[current_layer]:
                for (x_index, y_index, z_index) in path_indexes:
                    if 0 <= x_index < grid_height and 0 <= y_index < grid_width:
                        current_matrix[y_index, x_index] = BLOCKED_CELL
        
        # A Union-Find for sockets on the current net, so that only routing of new lines will be made if essential
        uf = UnionFind([tuple(loc) for loc in socket_locations[net]]) 

        # Iterate over the distances between the sockets, sorted in ascending order
        for dist, loc1, loc2 in distances:
            print(f"🔵 Routing between {loc1} and {loc2}")
            tunnels_placed = False
            
            # Check if the two locations are already connected in the union-find structure
            if uf.find(tuple(loc1)) == uf.find(tuple(loc2)):
                print(f"🟢 {loc1} and {loc2} are already connected")
                continue  # already connected, skip
                
            # Convert the start and end coordinates to grid indices
            start_index = to_grid_indices(loc1[0], loc1[1], center_x, center_y, resolution)
            end_index = to_grid_indices(loc2[0], loc2[1], center_x, center_y, resolution)

            # Create a 2D grid for the pathfinding
            net_grid = Grid(matrix=current_matrix, grid_id=0)

            if algorithm == "breadth_first":
                    finder = BreadthFirstFinder()
            if algorithm == "a_star":
                    finder = AStarFinder()
        
            finder.diagonal_movement = (
                DiagonalMovement.if_at_most_one_obstacle if other_nets_on_layer 
                else DiagonalMovement.always if allow_diagonal_traces 
                else DiagonalMovement.never
            )
            
            start = net_grid.node(*start_index)
            end = net_grid.node(*end_index)
            path, runs = finder.find_path(start, end, net_grid)
            print(f"🔵 Pathfinding runs: {runs}")
            
            if not path and other_nets_on_layer:
                
                print(f"🔵 Making a 3D grid to accomondate routing for {net} on layer {current_layer}")
                
                # Set the weights for the tunnelling matrix
                tunnel_matrix[tunnel_matrix == FREE_CELL] = TUNNEL_CELL
                                            
                # Create a 3D matrix for the tunneling, transpose to match the grid indices
                combined_matrix = np.stack((tunnel_matrix.T, current_matrix.T), axis=2)
                
                # Create a 3D grid for the pathfinding
                tunnel_grid = Grid3D(matrix=combined_matrix)
                
                # Only use A* for 3D pathfinding, as it takes the direction and cost into the heuristic calculation
                # Routing diagonally does not work in the current implementation 
                finder = AStarFinder3D(diagonal_movement=DiagonalMovement3D.never)
                    
                start = tunnel_grid.node(start_index[0], start_index[1], 0)
                end = tunnel_grid.node(end_index[0], end_index[1], 0)
                
                path, runs = finder.find_path(start, end, tunnel_grid)
                print(f"🔵 Pathfinding runs: {runs}")
                
                tunnels_placed = True
                
            if path:
                print(f"🟢 Found path for net {net} between {loc1} and {loc2}")
                
                if tunnels_placed:
                    path_tuples = [(node.x, node.y, node.z) for node in path]
                else:
                    path_tuples = [(node.x, node.y, 1) for node in path]
                
                paths.setdefault(net, []).append(path_tuples) 
                previous_paths[current_layer].append(path_tuples) 

                uf.union(tuple(loc1), tuple(loc2)) # Union-Find logic for an optimised routing strategy         
                
            else:
                print(f"🔴 No path found for net {net} between {loc1} and {loc2}")
    
    # Consolidate the the list of grid indices into line segments on the coordinate plane
    segments = consolidate_segments(paths, resolution, center_x, center_y)
    
    # Merge overlapping segments 
    # segments = merge_overlapping_segments(segments)

    return segments
                
