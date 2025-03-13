import math
import numpy as np

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

def create_grid(keep_out_zones, dimensions, resolution):
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