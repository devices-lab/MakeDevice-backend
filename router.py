import math
import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple, DefaultDict

from board import Board
from objects import Point, Segment

class Router: 
    """Base router class that provides common functionality for all router types."""
    
    def __init__(self, board: Board):
        """
        Initialize the bus router with a board.
        
        Parameters:
            board: The Board object containing all the PCB data
        """
    
        self.board = board
        self.grid_height = self._to_grid_unit(board.height)
        self.grid_width = self._to_grid_unit(board.width)
        self.grid_center_x = self.grid_width // 2
        self.grid_center_y = self.grid_height // 2
        
        # Store the output of this router
        self.paths_indices: DefaultDict[str, List[List[Tuple[int, int, int]]]] = defaultdict(list)
        self.vias_indices: DefaultDict[str, List[Tuple[int, int]]] = defaultdict(list)

        self.failed_routes = 0
        
        # Cell values
        self.FREE_CELL = 1
        self.BLOCKED_CELL = 0
        
        # Create the base grid
        self.base_grid = self._create_base_grid()
                    
    def _to_grid_unit(self, value: float) -> int:
        """Convert a value to grid resolution.
        
        Parameters: 
            value: Value in mm
        
        Returns:
            Value in grid units
        """
        return math.ceil(value / self.board.resolution)

    def _coordinates_to_indices(self, x: float, y: float) -> Tuple[int, int]:
        """Convert board coordinates to grid indices.
        
        Parameters:
            x: X coordinate in mm
            y: Y coordinate in mm
        
        Returns:
            Tuple of (column, row) indices in the grid
        """
        column = int(self.grid_center_x + round(x / self.board.resolution))
        row = int(self.grid_center_y - round(y / self.board.resolution))
        return column, row

    def _indices_to_point(self, column: int, row: int) -> Point:
        """Convert grid indices to board coordinates as a Point.
        
        Parameters:
            column: Column index in the grid
            row: Row index in the grid
            
        Returns:
            Point object with the corresponding coordinates"""
            
        x = (column - self.grid_center_x) * self.board.resolution
        y = (self.grid_center_y - row) * self.board.resolution
        return Point(x, y)

    def _create_base_grid(self) -> np.ndarray:
        """Create the base grid for the entire board."""        
        # Initialize grid with free cells
        grid = np.full((self.grid_height, self.grid_width), self.FREE_CELL, dtype=int)
        
        # Mark keep-out zones in the grid
        for zone in self.board.zones.get_data():
            bottom_left, top_left, top_right, bottom_right = zone
            
            # Convert coordinates to grid indices
            bl_col, bl_row = self._coordinates_to_indices(bottom_left[0], bottom_left[1])
            tr_col, tr_row = self._coordinates_to_indices(top_right[0], top_right[1])
            
            # Ensure bounds are within grid limits and handle coordinate flips
            bl_col = max(0, min(self.grid_width - 1, bl_col))
            tr_col = max(0, min(self.grid_width - 1, tr_col))
            bl_row = max(0, min(self.grid_height - 1, bl_row))
            tr_row = max(0, min(self.grid_height - 1, tr_row))
            
            min_col, max_col = min(bl_col, tr_col), max(bl_col, tr_col)
            min_row, max_row = min(bl_row, tr_row), max(bl_row, tr_row)
            
            # Mark cells in the rectangle as blocked
            grid[min_row:max_row+1, min_col:max_col+1] = self.BLOCKED_CELL
        
        return grid
    
    def _add_via(self, net_name: str, point: Tuple[int, int]) -> None:
        """Add a via to the via indexes."""
        # First check if the via is already places at that location
        if point in self.vias_indices[net_name]:
            print(f"🟡 Via already exists at {point}")
            return
        
        self.vias_indices[net_name].append(point)
        
    def _mark_obstacles_on_grid(self, grid: np.ndarray, net_to_protect: str) -> np.ndarray:
        """
        Needs an updated documentation
        """
        
        temporary_obstacle_grid = np.copy(grid)
        
        # Find the layer for this net
        current_layer = self.board.get_layer_for_net(net_to_protect)
        
        if not current_layer:
            return temporary_obstacle_grid
        
        # Find other nets on the same layer
        for net in current_layer.nets:
            if net == net_to_protect and self.board.allow_overlap:
                continue  # Allow overlap woud allow this net to overlap (short) with itself
            
            # Mark all paths on other nets as obstacles
            for path in self.paths_indices.get(net, []):
                for x, y, _ in path:
                    if 0 <= y < self.grid_height and 0 <= x < self.grid_width:
                        temporary_obstacle_grid[y, x] = self.BLOCKED_CELL # TODO: if any problems arise, check here
                        
            # Mark all the area around all vias as obstacles
            for via_index in self.vias_indices.get(net, []):
                if 0 <= y < self.grid_height and 0 <= x < self.grid_width:
                    for dy in range(-1, 2): # 2 extra grid cells of keep out on left and right
                        for dx in range(-1, 2): # 1 extra grid cell of keep out on top and bottom
                            ny, nx = via_index[0] + dy, via_index[1] + dx
                            temporary_obstacle_grid[ny, nx] = self.BLOCKED_CELL
            
        return temporary_obstacle_grid
    
    def _apply_socket_margins(self, grid: np.ndarray, exposed_socket_index: Tuple[int, int], 
                             keep_out_mm: float = 0.5) -> np.ndarray:
        """
        Apply keep_out zones around all sockets from other nets
        
        Parameters:
            grid: The grid to apply the keep-out zone to
            exposed_socket_index: Index of the socket to be exposed
            keep_out_mm: Optional, keep-out zone size in mm
            
        Returns:
            Updated grid with socket keep-out applied
        """
        temp_grid = np.copy(grid)
        keep_out_cells = int(np.ceil(keep_out_mm / self.board.resolution))
        # Mark all sockets for this other net as obstacles
        for position in self.board.sockets.get_all_coordinates():
            socket_index = self._coordinates_to_indices(position[0], position[1])    
            for i in range(-keep_out_cells+1, keep_out_cells):
                for j in range(-keep_out_cells+1, keep_out_cells):
                    column = socket_index[0] + i
                    row = socket_index[1] + j
                    # Check if within grid boundaries
                    if 0 <= column < self.grid_width and 0 <= row < self.grid_height:
                        if socket_index == exposed_socket_index:
                            temp_grid[row, column] = self.FREE_CELL
                        else: 
                            temp_grid[row, column] = self.BLOCKED_CELL
                            
        return temp_grid
    
    def _convert_trace_indices_to_segments(self) -> None:
        """
        Convert grid paths to physical line segments and assign them to board layers directly.
        
        Returns:
            None
        """        
        for net_name, paths in self.paths_indices.items():
            # Get the layer for this net
            layer = self.board.get_layer_for_net(net_name)
            
            if not layer:
                print(f"🔴 Layer for net name {net_name} not found in board")
                continue
            
            for path in paths:
                # Convert grid indices to points
                points = [self._indices_to_point(x, y) for x, y, _ in path]
                key_points = self._identify_key_points(points)
                
                # Create segments between consecutive key points
                for i in range(len(key_points) - 1):
                    start_idx = key_points[i]
                    end_idx = key_points[i + 1]
                    
                    # Create a segment connecting the key points
                    segment = Segment(points[start_idx], points[end_idx], layer=layer.name, width=self.board.loader.track_width, net=net_name)
                    
                    # Add directly to the board layer
                    layer.add_segment(segment)
                    
    def _identify_key_points(self, points: List[Point]) -> List[int]:
        """Identify key points in a path (start, direction changes, end)."""
        key_points = [0]  # Start with the first point index
        
        for i in range(1, len(points) - 1):
            # Check if this point represents a direction change
            p0, p1, p2 = points[i-1], points[i], points[i+1]
            
            # Calculate vectors between consecutive points
            v1 = (p1.x - p0.x, p1.y - p0.y)
            v2 = (p2.x - p1.x, p2.y - p1.y)
            
            # Check if vectors are collinear by calculating cross product
            cross_product = v1[0] * v2[1] - v1[1] * v2[0]
            
            # If not collinear, this is a key point
            if abs(cross_product) > 1e-6:
                key_points.append(i)
        
        # Always include the last point
        key_points.append(len(points) - 1)
        
        return key_points

    def _consolidate_trace_indices(self) -> Dict[str, List[List[Tuple[int, int, int]]]]:
        """
        Consolidate trace indexes to eliminate duplicate grid points or segments.
        
        Returns:
            Dictionary of consolidated paths for each net
        """
        consolidated_indexes = {}
        
        for net_name, paths in self.paths_indices.items():
            # Set of unique grid segments for this net
            unique_segments = set()
            consolidated_paths = []
            
            for path in paths:
                # Skip paths with fewer than 2 points
                if len(path) < 2:
                    continue
                    
                # Create a new path with unique segments
                consolidated_path = []
                
                # Add the first point
                consolidated_path.append(path[0])
                
                # Process each segment in the path
                for i in range(1, len(path)):
                    # Create a canonical representation of this grid segment
                    p1 = path[i-1][:2]  # Just x,y coords
                    p2 = path[i][:2]
                    segment_key = tuple(sorted([p1, p2]))  # Order doesn't matter for uniqueness
                    
                    # Only add if we haven't seen this grid segment before
                    if segment_key not in unique_segments:
                        unique_segments.add(segment_key)
                        consolidated_path.append(path[i])
                
                # Only add the path if it still has at least 2 points
                if len(consolidated_path) >= 2:
                    consolidated_paths.append(consolidated_path)
            
            # Store this net's consolidated paths
            if consolidated_paths:
                consolidated_indexes[net_name] = consolidated_paths
                
            print(f"🟢 Net '{net_name}': Found {len(unique_segments)} unique grid segments across {len(consolidated_paths)} paths")
                
        return consolidated_indexes

    def _convert_via_indexes_to_points(self) -> None:
        """Convert via grid indices to board coordinate points and add to layers."""
        
        for net_name, via_positions in self.vias_indices.items():
            for x, y in via_positions:
                via_point = self._indices_to_point(x, y)
            
                # Add annular rings to all layers
                for layer in self.board.layers:
                    layer.add_annular_ring(via_point)
                    
                # Add drill hole to the board
                self.board.add_drill_hole(via_point)
               
    
    def route(self) -> None:
        """
        Abstract method to be implemented by subclasses.
        """
        raise NotImplementedError("Subclasses must implement the route method")
