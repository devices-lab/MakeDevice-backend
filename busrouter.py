import math
import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.finder.breadth_first import BreadthFirstFinder
from pathfinding.core.diagonal_movement import DiagonalMovement

from board import Board
from segment import Point, Segment, NetSegments

# Constants for grid cells
FREE_CELL = 1
BLOCKED_CELL = 0

class Via: 
    """Represents a via in 2D space with x and y coordinates."""
    def __init__ (self, point: Point):
        self.point = point
    
class RoutingResult:
    """Contains the complete routing result with segments organized by net."""
    def __init__(self):
        self.nets: Dict[str, NetSegments] = {}
        self.vias: List[Via] = []
    
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
    
    def get_segments_by_layer(self, layer: str) -> Dict[str, List[Segment]]:
        """Get all segments for a specific layer across all nets"""
        result = {}
        for net_name, net_segments in self.nets.items():
            layer_segments = net_segments.get_segments_by_layer(layer)
            if layer_segments:
                result[net_name] = layer_segments
        return result
    
    def total_segments_count(self) -> int:
        """Get the total number of segments across all nets"""
        return sum(len(net_segments) for net_segments in self.nets.values())
    
    def add_via(self, point: Point) -> None:
        """Add a via to the routing result"""
        self.vias.append(Via(point))
        
    def get_all_vias(self) -> List[Via]:
        """Get a list of all vias in the routing result"""
        return self.vias
    
    def total_via_count(self) -> int:
        """Get the total number of vias in the routing result"""
        return len(self.vias)
    
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


class BusRouter:
    """
    A router that creates a vertical bus for each net and connects sockets to the bus.
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
        self.grid_height = self._to_grid_resolution(board.height)
        self.grid_width = self._to_grid_resolution(board.width)
        self.grid_center_x = self.grid_width // 2
        self.grid_center_y = self.grid_height // 2
        self.sockets = board.sockets
        self.zones = board.zones
        
        # Will be populated during routing
        self.paths = defaultdict(list)  # {net_name: [list of path tuples]}
        self.buses = Dict[str, Segment]
        self.result = RoutingResult()
        
        # Track routed nets by layer
        self.routed_nets_by_layer = defaultdict(list)  # {layer_name: [list of net names]}
        
        # Configuration for bus spacing and traces
        self.trace_width = board.loader.fabrication_options['track_width']
        self.bus_width = board.loader.fabrication_options['bus_width']
        self.bus_spacing = 1 # TODO: try to get this from the JSON
        self.bus_margin = 1 # TODO: try to get this from the JSON
        
        # Create net to layer mapping
        self.net_to_layer_map = self._invert_layer_map()
        
        # Create the base grid
        self.base_grid = self._create_base_grid()
    
    def _create_base_grid(self) -> np.ndarray:
        """Create the base grid for the entire board."""
        if not self.zones:
            raise ValueError("Cannot create grid without zones")
        
        # Initialize grid with free cells
        grid = np.full((self.grid_height, self.grid_width), FREE_CELL, dtype=int)
        
        # Mark keep-out zones in the grid
        for zone in self.zones.get_zone_rectangles():
            bottom_left, top_left, top_right, bottom_right = zone
            
            # Convert coordinates to grid indices
            bl_col, bl_row = self._to_grid_indices(bottom_left[0], bottom_left[1])
            tr_col, tr_row = self._to_grid_indices(top_right[0], top_right[1])
            
            # Ensure bounds are within grid limits and handle coordinate flips
            bl_col = max(0, min(self.grid_width - 1, bl_col))
            tr_col = max(0, min(self.grid_width - 1, tr_col))
            bl_row = max(0, min(self.grid_height - 1, bl_row))
            tr_row = max(0, min(self.grid_height - 1, tr_row))
            
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
    
    def _to_grid_resolution(self, value: float) -> int:
        """Convert a value to grid resolution."""
        return math.ceil(value / self.resolution)
    
    def _to_grid_indices(self, x: float, y: float) -> Tuple[int, int]:
        """Convert board coordinates to grid indices."""
        column = int(self.grid_center_x + round(x / self.resolution))
        row = int(self.grid_center_y - round(y / self.resolution))
        return column, row
    
    def _from_grid_indices(self, column: int, row: int) -> Point:
        """Convert grid indices to board coordinates as a Point."""
        x = (column - self.grid_center_x) * self.resolution
        y = (self.grid_center_y - row) * self.resolution
        return Point(x, y)
    
    def _calculate_bus_positions(self, nets: List[str]) -> Dict[str, Tuple[float, float, float]]:
        """
        Calculate the positions of vertical buses for each net.
        
        Parameters:
            nets: List of net names to create buses for
            
        Returns:
            Dict mapping net names to bus coordinates (x, y_top, y_bottom)
        """
        # The corner radius determines the vertical length of the busses
        corner_radius = self.board.loader.fabrication_options['rounded_corner_radius']
        
        # Start position for first bus
        leftmost_bus_x = (-self.board.width / 2) + self.bus_margin
        
        # Calculate the y extents for buses
        bus_upper_y = (self.board.height / 2) - corner_radius
        bus_lower_y = (-self.board.height / 2) + corner_radius
        
        # Create buses for each net, grouped by layer
        bus_positions = {}
        
        # Group nets by layer
        nets_by_layer = defaultdict(list)
        for net_name in nets:
            layer = self.net_to_layer_map.get(net_name)
            nets_by_layer[layer].append(net_name)
        
        # Calculate positions for each net
        current_x = leftmost_bus_x
        for layer, layer_nets in nets_by_layer.items():
            for net_name in layer_nets:
                bus_positions[net_name] = (current_x, bus_upper_y, bus_lower_y)
                current_x += self.bus_spacing
            
            # Add extra spacing between layers
            current_x += self.bus_spacing * 2
        
        return bus_positions
    
    def _create_bus_segments(self, bus_positions: Dict[str, Tuple[float, float, float]]) -> Dict[str, Segment]:
        """
        Create vertical bus segments for each net with layer and width information.
        """
        bus_segments = {}
        
        for net_name, (x, y_top, y_bottom) in bus_positions.items():
            start_point = Point(x, y_top)
            end_point = Point(x, y_bottom)
            
            # Get the layer for this net
            layer = self.net_to_layer_map.get(net_name)
            
            # Create segment with layer and width
            bus_segments[net_name] = Segment(start_point, end_point, layer=layer, width=self.bus_width)
            
            # Add the bus segment to the result
            self.result.add_segment(net_name, bus_segments[net_name])
            
            # Track which nets are on which layer
            if layer:
                self.routed_nets_by_layer[layer].append(net_name)
        
        return bus_segments
    
    def _find_nearest_point_on_bus(self, socket_pos: Tuple[float, float], bus: Segment) -> Point:
        """
        Find the nearest point on a vertical bus to a socket.
        
        Parameters:
            socket_pos: (x, y) position of the socket
            bus: The bus Segment 
            
        Returns:
            Point: The nearest point on the bus
        """
        # For vertical buses, the x-coordinate is fixed, and we clamp the y-coordinate
        socket_x, socket_y = socket_pos
        bus_x = bus.start.x
        
        # Clamp the y-coordinate to the bus extent
        bus_y_min = min(bus.start.y, bus.end.y)
        bus_y_max = max(bus.start.y, bus.end.y)
        clamped_y = max(bus_y_min, min(socket_y, bus_y_max))
        
        return Point(bus_x, clamped_y)
    
    def _mark_other_net_traces(self, grid: np.ndarray, net_name: str) -> np.ndarray:
        """
        Mark traces from other nets on the same layer as obstacles.
        
        Parameters:
            grid: The base grid
            net_name: Current net being routed
            
        Returns:
            Updated grid with other nets' traces marked as obstacles
        """
        temp_grid = np.copy(grid)
        
        # Find the layer for this net
        current_layer = self.net_to_layer_map.get(net_name)
        if not current_layer:
            return temp_grid
        
        # Find other nets on the same layer
        for other_net in self.routed_nets_by_layer.get(current_layer, []):
            if other_net == net_name:
                continue  # Skip the current net
            
            # Mark all paths for this other net as obstacles
            for path in self.paths.get(other_net, []):
                for x, y, _ in path:
                    if 0 <= y < self.grid_height and 0 <= x < self.grid_width:
                        temp_grid[y, x] = BLOCKED_CELL
        
        return temp_grid
    
    def _route_socket_to_bus(self, grid: np.ndarray, socket_pos: Tuple[float, float], 
                                    bus_point: Point, net_name: str) -> List[Tuple[int, int, int]]:
        """
        Route a socket to the bus by targeting the left edge of the grid and then chopping
        the path at the bus column.
        
        Parameters:
            grid: The routing grid
            socket_pos: (x, y) position of the socket
            bus_point: Point on the bus to connect to
            net_name: Name of the net being routed
            
        Returns:
            List of grid indices representing the path up to the bus
        """
        # Apply obstacles from other nets on the same layer
        current_grid = self._mark_other_net_traces(grid, net_name)
        
        # Apply socket margin to ensure the socket is routable
        current_grid = self._apply_socket_margin(current_grid, socket_pos)
        
        # Convert to grid indices
        socket_col, socket_row = self._to_grid_indices(socket_pos[0], socket_pos[1])
        bus_col, bus_row = self._to_grid_indices(bus_point.x, bus_point.y)
        
        # For sockets to the right of the bus, we'll target a point
        # to the left of the bus (so paths have to cross the bus)
        target_col = 0  # Use left edge of grid as target
        
        # If socket is to the left of the bus, we'll target a point
        # to the right of the bus (so paths have to cross the bus)
        if socket_col < bus_col:
            target_col = self.grid_width - 1  # Use right edge of grid as target
        
        # Create pathfinding grid
        net_grid = Grid(matrix=current_grid, grid_id=0)
        
        # Set up the pathfinder
        if self.algorithm == "breadth_first":
            finder = BreadthFirstFinder()
        else:  # default to A*
            finder = AStarFinder()
        
        # Configure diagonal movement
        if self.allow_diagonal_traces:
            finder.diagonal_movement = DiagonalMovement.always
        else:
            finder.diagonal_movement = DiagonalMovement.never
        
        # Find path
        start = net_grid.node(socket_col, socket_row)
        end = net_grid.node(target_col, bus_row)
        
        try:
            path, runs = finder.find_path(start, end, net_grid)
            print(f"🔵 Pathfinding runs: {runs}")
            
            if path:
                # Find where the path crosses the bus column
                chopped_path = []
                bus_crossed = False
                
                # For paths from the right of the bus to the left
                if socket_col > bus_col:
                    for i, node in enumerate(path):
                        if node.x <= bus_col:
                            # We've reached or crossed the bus
                            bus_crossed = True
                            # Add the current node (which is on or past the bus)
                            chopped_path.append(node)
                            # Break the loop - we've reached the bus
                            break
                        # Add nodes until we reach the bus
                        chopped_path.append(node)
                
                # For paths from the left of the bus to the right
                else:
                    for i, node in enumerate(path):
                        if node.x >= bus_col:
                            # We've reached or crossed the bus
                            bus_crossed = True
                            # Add the current node (which is on or past the bus)
                            chopped_path.append(node)
                            # Break the loop - we've reached the bus
                            break
                        # Add nodes until we reach the bus
                        chopped_path.append(node)
                
                # If we never crossed the bus, something went wrong
                if not bus_crossed:
                    print(f"🔴 Path never crossed the bus column at {bus_col}")
                    return []
                
                # Add a node exactly at the bus position if needed
                # (This ensures we connect exactly to the bus point)
                if chopped_path[-1].x != bus_col or chopped_path[-1].y != bus_row:
                    # Create a new node at the exact bus position
                    bus_node = net_grid.node(bus_col, bus_row)
                    # Only add if it's adjacent to the last node
                    last_node = chopped_path[-1]
                    if abs(last_node.x - bus_col) <= 1 and abs(last_node.y - bus_row) <= 1:
                        chopped_path.append(bus_node)
                
                # Get the layer for this net
                layer_idx = 0 
                layer = self.net_to_layer_map.get(net_name)
                
                if layer:
                    # Layer name to index map
                    layer_indices = {
                        "F_Cu.gtl": 1,  # Top layer
                        "In1_Cu.g2": 2,  # Inner layer 1
                        "In2_Cu.g3": 3,  # Inner layer 2
                        "B_Cu.gbl": 4,  # Bottom layer
                    }
                    layer_idx = layer_indices.get(layer, 0)
                
                # Convert path to tuples with layer information
                path_tuples = [(node.x, node.y, layer_idx) for node in chopped_path]
                return path_tuples
            else:
                print(f"🔴 No path found between socket at {socket_pos} and target")
                return []
        except Exception as e:
            print(f"🔴 Error in pathfinding: {e}")
            return []

    def _apply_socket_margin(self, grid: np.ndarray, socket_pos: Tuple[float, float], 
                             keep_out_mm: float = 1.0) -> np.ndarray:
        """
        Apply a keep-out zone around a specific socket.
        
        Parameters:
            grid: The routing grid
            socket_pos: (x, y) position of the socket
            keep_out_mm: Radius of keep-out zone in mm
            
        Returns:
            Updated grid with socket keep-out applied
        """
        temp_grid = np.copy(grid)
        keep_out_cells = int(np.ceil(keep_out_mm / self.resolution))
        
        x_index, y_index = self._to_grid_indices(socket_pos[0], socket_pos[1])
        
        # Apply keep-out zone around the socket
        for i in range(-keep_out_cells+1, keep_out_cells):
            for j in range(-keep_out_cells+1, keep_out_cells):
                xi = x_index + i
                yi = y_index + j
                
                # Check if within grid boundaries
                if 0 <= xi < self.grid_width and 0 <= yi < self.grid_height:
                    temp_grid[yi, xi] = FREE_CELL  # Ensure socket areas are free
        
        return temp_grid
        
    def _consolidate_segments(self) -> None:
        """
        Convert grid paths to physical line segments with layer information.
        Merges consecutive collinear segments into single, longer segments.
        """
        # Get trace width from fabrication options
        trace_width = self.board.loader.fabrication_options.get('track_width', 0.125)
        
        for net_name, net_paths in self.paths.items():
            net = self.result.get_net(net_name)
            if not net:
                net = self.result.add_net(net_name)
            
            # Get the layer for this net
            layer = self.net_to_layer_map.get(net_name)
            
            for path in net_paths:
                # Skip paths with fewer than 2 points
                if len(path) < 2:
                    continue
                
                # Convert all grid points to board coordinates
                points = [self._from_grid_indices(x, y) for x, y, _ in path]
                
                # List to keep track of key points (start, direction changes, end)
                key_points = [0]  # Start with the first point index
                
                for i in range(1, len(points) - 1):
                    # Check if this point represents a direction change
                    p0, p1, p2 = points[i-1], points[i], points[i+1]
                    
                    # Calculate vectors between consecutive points
                    v1 = (p1.x - p0.x, p1.y - p0.y)
                    v2 = (p2.x - p1.x, p2.y - p1.y)
                    
                    # Check if vectors are collinear by calculating cross product
                    # If cross product is close to zero, the points are collinear
                    cross_product = v1[0] * v2[1] - v1[1] * v2[0]
                    
                    # If not collinear, this is a key point
                    if abs(cross_product) > 1e-6:
                        key_points.append(i)
                
                # Always include the last point
                key_points.append(len(points) - 1)
                
                # Create segments between consecutive key points
                for i in range(len(key_points) - 1):
                    start_idx = key_points[i]
                    end_idx = key_points[i + 1]
                    
                    # Create a segment connecting the key points
                    segment = Segment(points[start_idx], points[end_idx], layer=layer, width=trace_width)
                    segment.net_name = net_name
                    net.add_segment(segment)
    
    def _sort_all_sockets_by_proximity(self, socket_locations: Dict[str, List[Tuple[float, float]]]) -> List[Tuple[str, Tuple[float, float]]]:
        """
        Sort ALL sockets from all nets by proximity to their respective buses.
        
        Parameters:
            socket_locations: Dictionary mapping net names to lists of socket positions
            
        Returns:
            List of (net_name, socket_position) tuples sorted by proximity to buses
        """
        all_sockets_with_distance = []
        
        for net_name, locations in socket_locations.items():
            # Get the bus for this net
            bus = self.buses.get(net_name)
            if not bus:
                continue
                
            bus_x = bus.start.x
            
            # Calculate horizontal distances from sockets to their bus
            for socket_pos in locations:
                socket_x, socket_y = socket_pos
                
                # Horizontal distance to bus
                horizontal_distance = abs(socket_x - bus_x)
                
                # Store (net_name, socket_pos) with distance and y-coordinate
                all_sockets_with_distance.append(
                    ((net_name, socket_pos), horizontal_distance, -socket_y)  # Negative y for top-to-bottom
                )
        
        # Sort by distance (ascending) and then by y-coordinate (descending)
        sorted_sockets = [(net, socket) for (net, socket), _, _ in sorted(all_sockets_with_distance, key=lambda x: (x[1], x[2]))]
        
        return sorted_sockets

    def _assign_segments_to_layers(self) -> None:
        """
        Assign segments from the routing result to the appropriate layers in the board.
        
        Parameters:
            board: The PCB board with layer objects
        """
        # Get the routing result
        routing_result = self.get_routing_result()
        
        # Clear existing segments from all layers first
        for layer in self.board.layers.values():
            layer.clear_segments()
        
        # Iterate through all nets in the routing result
        for net_name, net_segments in routing_result.nets.items():
            # Get the layer name for this net
            layer_name = self.net_to_layer_map.get(net_name)
            if not layer_name:
                print(f"⚠️ No layer mapping found for net {net_name}")
                continue
            
            # Get the layer object from the board
            layer = self.board.layers.get(layer_name)
            if not layer:
                print(f"⚠️ Layer {layer_name} not found in board")
                continue
            
            # Add all segments to the layer
            for segment in net_segments.segments:
                # Make sure the segment knows which net it belongs to
                segment.net_name = net_name
                layer.add_segment(segment)
        
        print(f"🟢 Assigned segments to layers: {len(routing_result.nets)} nets processed")
        
    def route(self) -> RoutingResult:
        """
        Route sockets to buses for all nets, prioritizing ALL sockets by proximity to their buses.
        
        Returns:
            RoutingResult: The routing result with bus segments and connections
        """
        if not self.sockets:
            print("No sockets to route")
            return self.result
        
        # Get socket locations
        socket_locations = self.sockets.get_socket_locations()
        nets = list(socket_locations.keys())
        
        # Calculate bus positions
        bus_positions = self._calculate_bus_positions(nets)
        
        # Create bus segments
        self.buses = self._create_bus_segments(bus_positions)
        
        # Sort ALL sockets from all nets by proximity to their buses
        all_sockets_sorted = self._sort_all_sockets_by_proximity(socket_locations)
        
        print(f"🟣 Routing {len(all_sockets_sorted)} sockets in proximity order")
        
        # Route each socket in order of proximity
        for i, (net_name, socket_pos) in enumerate(all_sockets_sorted):
            print(f"🟠 Routing socket {i+1}/{len(all_sockets_sorted)} for net {net_name}")
            
            # Get the bus for this net
            bus = self.buses.get(net_name)
            if not bus:
                print(f"🔴 No bus found for net {net_name}")
                continue
            
            # Find nearest point on the bus
            bus_point = self._find_nearest_point_on_bus(socket_pos, bus)
            print(f"🔵 Routing socket at {socket_pos} to bus point at {(bus_point.x, bus_point.y)}")
            
            # Route the socket to the bus
            path = self._route_socket_to_bus(self.base_grid, socket_pos, bus_point, net_name)
            
            if path:
                print(f"🟢 Found path for socket at {socket_pos} to bus")
                self.paths[net_name].append(path)
                
            else:
                print(f"🔴 No path found for socket at {socket_pos} to bus")
        
        # Consolidate grid paths to segments
        self._consolidate_segments()
        
        # Assign segments to layers 
        self._assign_segments_to_layers()
        
        return self.result

    def get_routing_result(self) -> RoutingResult:
        """Get the routing result"""
        return self.result