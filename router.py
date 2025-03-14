import math
import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple, Set, Optional, Any
from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.finder.breadth_first import BreadthFirstFinder
from pathfinding.core.diagonal_movement import DiagonalMovement

from board import Board

# Constants for grid cells
FREE_CELL = 1
BLOCKED_CELL = 0
SOCKET_CELL = 2
MODULE_CELL = 3
TUNNEL_CELL = 5

class Point:
    """Represents a point in 2D space with x and y coordinates."""
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def as_tuple(self) -> Tuple[float, float]:
        """Return the point as a tuple (x, y)"""
        return (self.x, self.y)
    
    @classmethod
    def from_tuple(cls, point_tuple: Tuple[float, float]) -> 'Point':
        """Create a Point from a tuple (x, y)"""
        return cls(point_tuple[0], point_tuple[1])
    
    def __repr__(self) -> str:
        return f"Point(x={self.x:.3f}, y={self.y:.3f})"

class Segment:
    """Represents a line segment with start and end points."""
    def __init__(self, start: Point, end: Point):
        self.start = start
        self.end = end
    
    def as_tuple(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Return the segment as a tuple of tuples ((start_x, start_y), (end_x, end_y))"""
        return (self.start.as_tuple(), self.end.as_tuple())
    
    @classmethod
    def from_tuple(cls, segment_tuple: Tuple[Tuple[float, float], Tuple[float, float]]) -> 'Segment':
        """Create a Segment from a tuple of tuples ((start_x, start_y), (end_x, end_y))"""
        start_point = Point.from_tuple(segment_tuple[0])
        end_point = Point.from_tuple(segment_tuple[1])
        return cls(start_point, end_point)
    
    def length(self) -> float:
        """Calculate the length of the segment"""
        return ((self.end.x - self.start.x) ** 2 + (self.end.y - self.start.y) ** 2) ** 0.5
    
    def __repr__(self) -> str:
        return f"Segment(start={self.start}, end={self.end})"

class NetSegments:
    """Contains all segments for a specific net."""
    def __init__(self, net_name: str, segments: Optional[List[Segment]] = None):
        self.net_name = net_name
        self.segments = segments or []
    
    def add_segment(self, segment: Segment) -> None:
        """Add a segment to the net"""
        self.segments.append(segment)
    
    def add_segment_from_tuple(self, segment_tuple: Tuple[Tuple[float, float], Tuple[float, float]]) -> None:
        """Add a segment from a tuple representation"""
        self.segments.append(Segment.from_tuple(segment_tuple))
    
    def get_segments(self) -> List[Segment]:
        """Get all segments for this net"""
        return self.segments
    
    def total_length(self) -> float:
        """Calculate the total length of all segments in this net"""
        return sum(segment.length() for segment in self.segments)
    
    def __len__(self) -> int:
        return len(self.segments)
    
    def __getitem__(self, index: int) -> Segment:
        return self.segments[index]
    
    def __iter__(self):
        return iter(self.segments)
    
    def __repr__(self) -> str:
        return f"NetSegments(net_name='{self.net_name}', segments_count={len(self.segments)})"

class RoutingResult:
    """Contains the complete routing result with segments organized by net."""
    def __init__(self):
        self.nets: Dict[str, NetSegments] = {}
    
    def add_net(self, net_name: str) -> NetSegments:
        """Add a new net to the routing result"""
        if net_name not in self.nets:
            self.nets[net_name] = NetSegments(net_name)
        return self.nets[net_name]
    
    def get_net(self, net_name: str) -> Optional[NetSegments]:
        """Get segments for a specific net"""
        return self.nets.get(net_name)
    
    def add_segment(self, net_name: str, segment: Segment) -> None:
        """Add a segment to a specific net"""
        if net_name not in self.nets:
            self.add_net(net_name)
        self.nets[net_name].add_segment(segment)
    
    def get_all_nets(self) -> List[str]:
        """Get a list of all net names"""
        return list(self.nets.keys())
    
    def total_segments_count(self) -> int:
        """Get the total number of segments across all nets"""
        return sum(len(net_segments) for net_segments in self.nets.values())
    
    def __getitem__(self, net_name: str) -> NetSegments:
        if net_name not in self.nets:
            raise KeyError(f"Net '{net_name}' not found in routing result")
        return self.nets[net_name]
    
    def __contains__(self, net_name: str) -> bool:
        return net_name in self.nets
    
    def __iter__(self):
        return iter(self.nets.values())
    
    def __repr__(self) -> str:
        return f"RoutingResult(nets={len(self.nets)}, total_segments={self.total_segments_count()})"

class Router:
    """
    A class for routing connections between sockets on a PCB.
    Uses pathfinding algorithms to create efficient trace layouts.
    """
    
    def __init__(self, board: Board):
        """
        Initialize the router with a board.
        
        Parameters:
            board: The Board object containing all the PCB data
        """
        self.board = board
        self.resolution = board.resolution
        self.allow_diagonal_traces = board.allow_diagonal_traces
        self.algorithm = board.algorithm
        self.dimensions = board.dimensions
        self.sockets = board.sockets
        self.zones = board.zones
        
        # Will be populated during routing
        self.paths = {}  # {net: list of grid indices (x, y) for path}
        self.previous_paths = defaultdict(list)  # {layer_filename: list of path-indices}
        self.result = RoutingResult()
        
        # Create the base grid
        self.base_grid = self._create_base_grid()
        
        # Create net to layer mapping
        self.net_to_layer_map = self._invert_layer_map()
    
    def _create_base_grid(self) -> np.ndarray:
        """Create the base grid for the entire board."""
        if not self.zones:
            raise ValueError("Cannot create grid without zones")
            
        # Calculate grid dimensions
        width, height = self.dimensions
        grid_width = math.ceil(width / self.resolution)
        grid_height = math.ceil(height / self.resolution)
        center_x, center_y = grid_width // 2, grid_height // 2
        
        # Initialize grid with free cells
        grid = np.full((grid_height, grid_width), FREE_CELL, dtype=int)
        
        # Mark keep-out zones in the grid
        for zone in self.zones.get_zone_rectangles():
            bottom_left, top_left, top_right, bottom_right = zone
            
            # Convert coordinates to grid indices
            bl_col, bl_row = self._to_grid_indices(bottom_left[0], bottom_left[1])
            tr_col, tr_row = self._to_grid_indices(top_right[0], top_right[1])
            
            # Ensure bounds are within grid limits and handle coordinate flips
            grid_width = grid.shape[1]
            grid_height = grid.shape[0]
            
            bl_col = max(0, min(grid_width - 1, bl_col))
            tr_col = max(0, min(grid_width - 1, tr_col))
            bl_row = max(0, min(grid_height - 1, bl_row))
            tr_row = max(0, min(grid_height - 1, tr_row))
            
            min_col, max_col = min(bl_col, tr_col), max(bl_col, tr_col)
            min_row, max_row = min(bl_row, tr_row), max(bl_row, tr_row)
            
            # Mark cells in the rectangle as blocked
            grid[min_row:max_row+1, min_col:max_col+1] = BLOCKED_CELL
        
        return grid
    
    def _invert_layer_map(self) -> Dict[str, str]:
        """Build a dict that maps net names to their layer files."""
        net_to_layer = {}
        for layer_file, info in self.board.loader.layer_map.items():
            for net in info.get("nets", []):
                if net:
                    net_to_layer[net] = layer_file
        return net_to_layer
    
    def _to_grid_indices(self, x: float, y: float) -> Tuple[int, int]:
        """Convert board coordinates to grid indices."""
        grid_width = self.board.width
        grid_height = self.board.height
        center_x, center_y = grid_width // 2, grid_height // 2
        
        column = int(center_x + round(x / self.resolution))
        row = int(center_y - round(y / self.resolution))  # Y-axis is inverted in grid
        return column, row
    
    def _from_grid_indices(self, column: int, row: int) -> Point:
        """Convert grid indices to board coordinates as a Point."""
        grid_width = self.board.width
        grid_height = self.board.height
        center_x, center_y = grid_width // 2, grid_height // 2
        
        x = (column - center_x) * self.resolution
        y = (center_y - row) * self.resolution
        return Point(x, y)
    
    def _apply_socket_keep_out_zones(self, grid: np.ndarray, current_net: str, keep_out_mm: float = 1.0) -> np.ndarray:
        """Apply keep-out zones around sockets of other nets."""
        if not self.sockets:
            return grid
            
        temp_grid = np.copy(grid)
        keep_out_cells = int(np.ceil(keep_out_mm / self.resolution))
        socket_locations = self.sockets.get_socket_locations()
        
        grid_width = grid.shape[1]
        grid_height = grid.shape[0]
        
        for net, locations in socket_locations.items():
            for x, y in locations:
                x_index, y_index = self._to_grid_indices(x, y)
                
                # Apply keep-out zone around the socket
                for i in range(-keep_out_cells+1, keep_out_cells):
                    for j in range(-keep_out_cells+1, keep_out_cells):
                        xi = x_index + i
                        yi = y_index + j
                        
                        # Check if within grid boundaries
                        if 0 <= xi < grid_width and 0 <= yi < grid_height:
                            if net != current_net:
                                temp_grid[yi, xi] = BLOCKED_CELL  # Block other nets
                            else:
                                temp_grid[yi, xi] = FREE_CELL  # Free for current net
        
        return temp_grid
    
    def _heuristic_diagonal(self, a: Tuple[float, float], b: Tuple[float, float]) -> float:
        """Calculate the diagonal distance heuristic."""
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return (dx + dy) + (math.sqrt(2) - 2) * min(dx, dy)
    
    def _calculate_net_distances(self) -> Dict[str, List[Tuple[float, Tuple[float, float], Tuple[float, float]]]]:
        """Calculate distances between sockets for each net and sort by distance."""
        if not self.sockets:
            return {}
            
        socket_locations = self.sockets.get_socket_locations()
        net_distances = {}
        
        for net, locations in socket_locations.items():
            distances = []
            for i in range(len(locations) - 1):
                for j in range(i + 1, len(locations)):
                    loc_i = locations[i]
                    loc_j = locations[j]
                    # Scale by resolution for grid-based distance
                    dist = self._heuristic_diagonal(
                        (loc_i[0] / self.resolution, loc_i[1] / self.resolution),
                        (loc_j[0] / self.resolution, loc_j[1] / self.resolution)
                    )
                    distances.append((dist, loc_i, loc_j))
            distances.sort()  # Sort by distance
            net_distances[net] = distances
            
        return net_distances
    
    def _consolidate_segments(self) -> None:
        """
        Convert grid paths to physical line segments.
        Stores results in self.result
        """
        for net_name, net_paths in self.paths.items():
            net = self.result.add_net(net_name)
            
            for path in net_paths:
                # Skip paths with fewer than 2 points
                if len(path) < 2:
                    continue
                    
                # Create segments from consecutive points
                for i in range(1, len(path)):
                    prev_x, prev_y, _ = path[i-1]
                    curr_x, curr_y, _ = path[i]
                    
                    # Convert grid indices to board coordinates
                    prev_point = self._from_grid_indices(prev_x, prev_y)
                    curr_point = self._from_grid_indices(curr_x, curr_y)
                    
                    # Add the segment
                    segment = Segment(prev_point, curr_point)
                    net.add_segment(segment)
    
    def route(self) -> RoutingResult:
        """Route all nets on the board."""
        if not self.sockets:
            print("No sockets to route")
            return self.result
        
        # Calculate distances between sockets for each net
        net_distances = self._calculate_net_distances()
        
        # Get grid dimensions
        grid_height = self.base_grid.shape[0]
        grid_width = self.base_grid.shape[1]
        
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
        
        # Route each net
        socket_locations = self.sockets.get_socket_locations()
        for net, distances in net_distances.items():
            print(f"🟠 Routing net {net}")
            
            # Identify the layer for the current net
            current_layer = self.net_to_layer_map.get(net, None)
            other_nets_on_layer = False
            
            # Apply socket keep-out zones
            current_matrix = self._apply_socket_keep_out_zones(self.base_grid, net)
            
            # Block previously routed paths on this layer
            if self.previous_paths[current_layer]:
                other_nets_on_layer = True
                for path_indices in self.previous_paths[current_layer]:
                    for (x_index, y_index, z_index) in path_indices:
                        if 0 <= y_index < grid_height and 0 <= x_index < grid_width:
                            current_matrix[y_index, x_index] = BLOCKED_CELL
            
            # Union-Find to track connected sockets
            uf = UnionFind([tuple(loc) for loc in socket_locations[net]])
            
            # Route each socket pair by distance
            for dist, loc1, loc2 in distances:
                print(f"🔵 Routing between {loc1} and {loc2}")
                
                # Skip if already connected
                if uf.find(tuple(loc1)) == uf.find(tuple(loc2)):
                    print(f"🟢 {loc1} and {loc2} are already connected")
                    continue
                
                # Convert to grid indices
                start_index = self._to_grid_indices(loc1[0], loc1[1])
                end_index = self._to_grid_indices(loc2[0], loc2[1])
                
                # Create pathfinding grid
                net_grid = Grid(matrix=current_matrix, grid_id=0)
                
                # Set up the pathfinder
                if self.algorithm == "breadth_first":
                    finder = BreadthFirstFinder()
                else:  # default to A*
                    finder = AStarFinder()
                
                # Configure diagonal movement
                if other_nets_on_layer:
                    finder.diagonal_movement = DiagonalMovement.if_at_most_one_obstacle
                elif self.allow_diagonal_traces:
                    finder.diagonal_movement = DiagonalMovement.always
                else:
                    finder.diagonal_movement = DiagonalMovement.never
                
                # Find path
                start = net_grid.node(*start_index)
                end = net_grid.node(*end_index)
                path, runs = finder.find_path(start, end, net_grid)
                print(f"🔵 Pathfinding runs: {runs}")
                
                if path:
                    print(f"🟢 Found path for net {net} between {loc1} and {loc2}")
                    
                    # Convert path to tuples
                    path_tuples = [(node.x, node.y, 1) for node in path]
                    
                    # Store path
                    self.paths.setdefault(net, []).append(path_tuples)
                    self.previous_paths[current_layer].append(path_tuples)
                    
                    # Mark as connected
                    uf.union(tuple(loc1), tuple(loc2))
                else:
                    print(f"🔴 No path found for net {net} between {loc1} and {loc2}")
        
        # Convert paths to segments
        self._consolidate_segments()
        
        return self.result
    
    def get_routing_result(self) -> RoutingResult:
        """Get the routing result"""
        return self.result