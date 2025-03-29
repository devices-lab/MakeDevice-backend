import math
import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple, DefaultDict

from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.finder.breadth_first import BreadthFirstFinder
from pathfinding.core.diagonal_movement import DiagonalMovement

from board import Board
from objects import Point, Segment

# Constants for grid cells
FREE_CELL = 1
BLOCKED_CELL = 0

class BusRouter:
    """
    A router that creates a vertical bus for each net and connects sockets to the bus.
    """
    
    def __init__(self, board: Board):
        """
        Initialize the bus router with a board.
        
        Parameters:
            board: The Board object containing all the PCB data
        """
        self.board = board
        self.resolution = board.resolution
        self.allow_diagonal_traces = board.allow_diagonal_traces
        self.allow_overlap = board.allow_overlap
        self.algorithm = board.algorithm
        self.grid_height = self._to_grid_resolution(board.height)
        self.grid_width = self._to_grid_resolution(board.width)
        self.grid_center_x = self.grid_width // 2
        self.grid_center_y = self.grid_height // 2
        self.sockets = board.sockets
        self.zones = board.zones
        
        # Will be populated during routing
        self.trace_indexes: DefaultDict[str, List[List[Tuple[int, int, int]]]] = defaultdict(list)
        self.via_indexes: DefaultDict[str, List[Tuple[int, int]]] = defaultdict(list)
        self.buses = Dict[str, Segment]
        
        # Track routed nets by layer
        self.routed_nets_by_layer = defaultdict(list)  # {layer_name: [list of net names]}
        
        # Configuration for bus spacing and traces
        self.trace_width = board.loader.fabrication_options['track_width']
        self.bus_width = board.loader.fabrication_options['bus_width']
        self.bus_spacing = board.loader.fabrication_options['bus_spacing']
        self.edge_clearance = board.loader.fabrication_options['edge_clearance']
        
        # Create net to layer mapping
        self.net_to_layer_map = self._invert_layer_map()
        
        # Retrieve layers that will be used in this routing
        self.front_layer = self.board.layers.get("F_Cu.gtl")
        self.back_layer = self.board.layers.get("B_Cu.gbl")
        
        if not self.front_layer or not self.back_layer:
            raise ValueError("🔴 Front or back layer not found in board")
       
        # Add corner keep-out zones to prevent traces from crossing rounded corners
        self._add_corner_keep_out_zones()
        
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
        """Build a dict that maps net names to their layer files by using Layer objects from Board"""
        net_to_layer = {}
        
        # Iterate through all layers in the board
        for layer_name, layer in self.board.layers.items():
            # For each net in this layer, map it to the layer name
            for net_name in layer.nets:
                net_to_layer[net_name] = layer_name
        
        return net_to_layer
    
    def _get_nets_for_layer(self, layer_name: str) -> List[str]:
        """Get all nets assigned to a specific layer."""
        layer = self.board.layers.get(layer_name)
        if not layer:
            return []
        return layer.nets
    
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
    
    def _create_buses(self, nets: List[str]) -> Dict[str, Segment]:
        """Calculate positions and create vertical bus segments for each net."""
        # The corner radius determines the vertical length of the buses
        corner_radius = self.board.loader.fabrication_options['rounded_corner_radius']
        
        # Start position for first bus
        leftmost_bus_x: float = (-self.board.width / 2) + self.edge_clearance
                
        # Vertical offset for buses
        offset = corner_radius if corner_radius > 0 else self.edge_clearance
        
        # Calculate the y extents for buses
        bus_upper_y = (self.board.height / 2) - offset
        bus_lower_y = (-self.board.height / 2) + offset
        
        # Create result dictionary for bus segments
        bus_segments = {}
        
        # Group nets by layer using the board's layer structure
        nets_by_layer = defaultdict(list)
        for net_name in nets:
            layer_name = self.net_to_layer_map.get(net_name)
            if layer_name:
                nets_by_layer[layer_name].append(net_name)
        
        # Calculate positions and create segments for each net
        current_x: float = leftmost_bus_x
        
        for layer_name, layer_nets in nets_by_layer.items():
            for net_name in layer_nets:
                # Calculate bus position
                x = current_x
                y_top = bus_upper_y
                y_bottom = bus_lower_y
                
                # Create segment points
                start_point = Point(x, y_top)
                end_point = Point(x, y_bottom)
                
                # Create segment with layer and width (all buses go on back layer)
                bus_segment = Segment(start_point, end_point, layer="B_Cu.gbl", width=self.bus_width)
                bus_segment.net_name = net_name
                
                # Store in the bus segments dictionary
                bus_segments[net_name] = bus_segment
                
                # Add the bus segment directly to the back layer in the board
                back_layer = self.board.layers.get("B_Cu.gbl")
                if back_layer:
                    back_layer.add_segment(bus_segment)
                
                # Move to the next x position
                current_x += self.bus_spacing
        
        # Store clearance needed for the buses
        self.board.bus_clearance = current_x + (self.board.width / 2)
        
        print(f"🟢 Created {len(bus_segments)} bus segments")
        return bus_segments
    
    def _add_via(self, net_name: str, point: Tuple[int, int]) -> None:
        """Add a via to the via indexes."""
        # First check if the via is already places at that location
        if point in self.via_indexes[net_name]:
            print(f"⚠️ Via already exists at {point}")
            return
        
        self.via_indexes[net_name].append(point)

    def _find_point_on_bus(self, socket_pos: Tuple[float, float], bus: Segment) -> Point:
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
        x_position = bus.start.x
        
        # Clamp the y-coordinate to the bus extent
        bus_y_min = min(bus.start.y, bus.end.y)
        bus_y_max = max(bus.start.y, bus.end.y)
        clamped_y_position = max(bus_y_min, min(socket_y, bus_y_max))
        
        center_y_position = 0 # Use the center point of all buses, instead of the clamped 
        
        return Point(x_position, clamped_y_position)
    
    def _block_elements_on_grid(self, grid: np.ndarray, net_name: str) -> np.ndarray:
        """Mark traces from other nets on the same layer as obstacles."""
        temp_grid = np.copy(grid)
        
        # Find the layer for this net
        current_layer_name = self.net_to_layer_map.get(net_name)
        if not current_layer_name:
            return temp_grid
        
        # Get all nets on the same layer from the board structure
        nets_on_current_layer = self._get_nets_for_layer(current_layer_name)
        
        last_bus_x_index = self._to_grid_indices(self.board.bus_clearance, 0)[0] - self.grid_width // 2
        
        # Find other nets on the same layer
        for other_net in nets_on_current_layer:
            if other_net == net_name and self.allow_overlap:
                continue  # Skip the current net, allow elements to short
            
            # Mark all paths for this other net as obstacles
            for path in self.trace_indexes.get(other_net, []):
                for x, y, _ in path:
                    if 0 <= y < self.grid_height and 0 <= x < self.grid_width:
                        temp_grid[y, x] = BLOCKED_CELL
                        
                        # Ensure that the paths above the buses have more clearance to accomondate for vias
                        if x < last_bus_x_index:
                            temp_grid[y-1, x] = BLOCKED_CELL
                            temp_grid[y+1, x] = BLOCKED_CELL
            
            # Mark all vias on the bus as obstacles
            for via_index in self.via_indexes.get(other_net, []):
                for dx in range(-1, 2): # 2 extra grid cells of keep out on left and right
                    for dy in range(-1, 2): # 1 extra grid cell of keep out on top and bottom
                        nx, ny = via_index[0] + dx, via_index[1] + dy
                        if 0 <= ny < self.grid_height and 0 <= nx < self.grid_width:
                            temp_grid[ny, nx] = BLOCKED_CELL
        
        # Ensure the first column is always free
        for y in range(self.grid_height):
            temp_grid[y, 0] = FREE_CELL
            
        return temp_grid
    
    def _add_corner_keep_out_zones(self) -> None:
        """
        Apply keep-out zones to each corner of the board with dimensions based on corner radius.
        This prevents routing traces through the rounded corners of the board.
        """
        # Skip if zones are not available
        if not self.zones:
            print("⚠️ Cannot add corner keep-out zones: zones object not initialized")
            return
        
        # Get corner radius from board fabrication options
        corner_radius = self.board.loader.fabrication_options.get('rounded_corner_radius', 0)
        
        # If corner radius is zero or not set, no need to add corner keep-out zones
        if corner_radius <= 0:
            print("🟠 No corner radius defined, skipping corner keep-out zones")
            return
        
        # Get board dimensions and origin
        width = self.board.width
        height = self.board.height
        origin_x = self.board.origin['x']
        origin_y = self.board.origin['y']
        
        # Calculate the board boundaries
        xmin = origin_x - width / 2
        xmax = origin_x + width / 2
        ymin = origin_y - height / 2
        ymax = origin_y + height / 2
        
        # Create square keep-out zones for each corner, with size equal to corner radius
        # Bottom-left corner
        bottom_left_zone = (
            (xmin, ymin),                          # bottom-left
            (xmin, ymin + corner_radius),          # top-left
            (xmin + corner_radius, ymin + corner_radius),  # top-right
            (xmin + corner_radius, ymin)           # bottom-right
        )
        
        # Bottom-right corner
        bottom_right_zone = (
            (xmax - corner_radius, ymin),          # bottom-left
            (xmax - corner_radius, ymin + corner_radius),  # top-left
            (xmax, ymin + corner_radius),          # top-right
            (xmax, ymin)                           # bottom-right
        )
        
        # Top-left corner
        top_left_zone = (
            (xmin, ymax - corner_radius),          # bottom-left
            (xmin, ymax),                          # top-left
            (xmin + corner_radius, ymax),          # top-right
            (xmin + corner_radius, ymax - corner_radius)   # bottom-right
        )
        
        # Top-right corner
        top_right_zone = (
            (xmax - corner_radius, ymax - corner_radius),  # bottom-left
            (xmax - corner_radius, ymax),          # top-left
            (xmax, ymax),                          # top-right
            (xmax, ymax - corner_radius)           # bottom-right
        )
        
        # Add these zones to the board's zones
        # You may need to adjust how you add zones based on your Zones class implementation
        corner_zones = [bottom_left_zone, bottom_right_zone, top_left_zone, top_right_zone]
        
        print(f"🟢 Adding {len(corner_zones)} corner keep-out zones with size {corner_radius}mm")
        
        # Add zones to the grid
        for zone in corner_zones:
            self.zones.add_zone(zone)

    def _apply_socket_margins(self, grid: np.ndarray, socket_position: Tuple[float, float], 
                             keep_out_mm: float = 0.5) -> np.ndarray:
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
        
        x_index, y_index = self._to_grid_indices(socket_position[0], socket_position[1])
        
        # Mark all sockets for this other net as obstacles
        for position in self.sockets.get_all_positions():
            x, y = self._to_grid_indices(position[0], position[1])                
            for i in range(-keep_out_cells+1, keep_out_cells):
                for j in range(-keep_out_cells+1, keep_out_cells):
                    dx = x + i
                    dy = y + j
                    # Check if within grid boundaries
                    if 0 <= dx < self.grid_width and 0 <= dy < self.grid_height:
                        temp_grid[dy, dx] = BLOCKED_CELL
                        
        # # Apply keep-out zone around the socket
        for i in range(-keep_out_cells+1, keep_out_cells):
            for j in range(-keep_out_cells+1, keep_out_cells):
                xi = x_index + i
                yi = y_index + j
                
                # Check if within grid boundaries
                if 0 <= xi < self.grid_width and 0 <= yi < self.grid_height:
                    temp_grid[yi, xi] = FREE_CELL  # Ensure socket areas are free
        
        return temp_grid
    
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

    def _consolidate_trace_indexes(self) -> Dict[str, List[List[Tuple[int, int, int]]]]:
        """
        Consolidate trace indexes to eliminate duplicate grid points or segments.
        Returns a clean version of trace_indexes with no duplicates.
        """
        consolidated_indexes = {}
        
        for net_name, paths in self.trace_indexes.items():
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

    def _convert_trace_indexes_to_segments(self) -> None:
        """
        Convert grid paths to physical line segments and assign them to board layers directly.
        """
        # First consolidate trace indexes to eliminate duplicates
        # consolidated_indexes = self._consolidate_trace_indexes()
        
        for net_name, grid_paths in self.trace_indexes.items():
            # Get the layer for this net
            layer_name = self.net_to_layer_map.get(net_name)
            layer = self.board.layers.get(layer_name)
            if not layer:
                print(f"🔴 Layer {layer_name} not found in board")
                continue
            
            for path in grid_paths:
                # Convert grid points to board coordinates
                points = [self._from_grid_indices(x, y) for x, y, _ in path]
                key_points = self._identify_key_points(points)
                
                # Create segments between consecutive key points
                for i in range(len(key_points) - 1):
                    start_idx = key_points[i]
                    end_idx = key_points[i + 1]
                    
                    # Create a segment connecting the key points
                    segment = Segment(points[start_idx], points[end_idx], layer=layer_name, width=self.trace_width)
                    segment.net_name = net_name
                    
                    # Add directly to the board layer
                    layer.add_segment(segment)
    
    def _convert_via_indexes_to_points(self) -> None:
        """Convert via grid indices to board coordinate points and add to layers."""
        if not self.front_layer or not self.back_layer:
            print("⚠️ Front or back layer not found for via placement")
        
        for net_name, via_positions in self.via_indexes.items():
            for x, y in via_positions:
                via_point = self._from_grid_indices(x, y)
            
                # Add annular rings front and back layers
                if self.front_layer and self.back_layer:
                    self.front_layer.add_annular_ring(via_point)
                    self.back_layer.add_annular_ring(via_point)
                
                # Add drill hole to the board
                self.board.add_drill_hole(via_point)
               
    def _sort_all_sockets_by_proximity(self, socket_locations: Dict[str, List[Tuple[float, float]]]) -> List[Tuple[str, Tuple[float, float]]]:
        """
        Sort ALL sockets from all nets based on position, prioritizing left-to-right,
        and then top-to-bottom for sockets with the same x-coordinate.
        
        Parameters:
            socket_locations: Dictionary mapping net names to lists of socket positions
            
        Returns:
            List of (net_name, socket_position) tuples sorted left-to-right, then top-to-bottom
        """
        all_sockets = []
        
        for net_name, locations in socket_locations.items():
            # Get the bus for this net
            bus = self.buses.get(net_name)
            if not bus:
                continue
                
            # Add all socket positions for this net
            for socket_pos in locations:
                socket_x, socket_y = socket_pos
                
                # Store socket with coordinates for sorting
                all_sockets.append(
                    (net_name, socket_pos, socket_x, -socket_y)  # Store x and -y for sorting
                )
        
        # Sort by x-coordinate (ascending) and then by y-coordinate (descending)
        # This gives left (lowest x) to right, and top (highest y) to bottom for same x
        sorted_sockets = [(net, socket) for net, socket, _, _ in sorted(all_sockets, key=lambda x: (x[2], x[3]))]
        
        return sorted_sockets
    
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
        current_grid = self._block_elements_on_grid(grid, net_name)
        
        # Apply socket margin to ensure the socket is routable
        current_grid = self._apply_socket_margins(current_grid, socket_pos)
        
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
            finder.diagonal_movement = DiagonalMovement.only_when_no_obstacle
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
                
                # If successfully reached the bus, add a via at the connection point
                if bus_crossed:
                    # Get the last point in the path (where it connects to the bus)
                    connection_index = chopped_path[-1]                    
                    self._add_via(net_name, (connection_index.x, connection_index.y))
                    
                # Convert path to tuples with layer information
                path_tuples = [(node.x, node.y, -1) for node in chopped_path]
                return path_tuples
            else:
                print(f"🔴 No path found between socket at {socket_pos} and target")
                return []
        except Exception as e:
            print(f"🔴 Error in pathfinding: {e}")
            return []

    def route(self) -> None:
        """
        Route sockets to buses for all nets, prioritizing by proximity.
        
        The routing happens in two phases:
        - First, route all sockets that have buses using your proximity sorting
        - Then, process the remaining sockets that don't have buses but are in filled layers (need vias)
        
        Returns:
            None
        """
        if not self.sockets:
            print("No sockets to route")
            return
        
        # Get socket locations and all layers
        socket_locations = self.sockets.get_socket_locations()
        layers = self.board.get_layers()

        # Filter for layers with fill=False
        non_fill_layers = [layer for layer in layers if layer.fill == False]
        fill_layers = [layer for layer in layers if layer.fill == True]
        
        bus_nets = []
        fill_nets = []
        
        for layer in non_fill_layers:
            for net in layer.nets:
                bus_nets.append(net)
        
        for layer in fill_layers:
            for net in layer.nets:
                fill_nets.append(net)
            
        # Create bus segments
        self.buses = self._create_buses(bus_nets)
        
        # Sort ALL sockets from all nets by proximity to their buses
        all_sockets_sorted = self._sort_all_sockets_by_proximity(socket_locations)
        
        print(f"🟢 Routing {len(all_sockets_sorted)} sockets with buses")
        # Route each socket in order of proximity
        for i, (net_name, socket_pos) in enumerate(all_sockets_sorted):
            print(f"🟢 Routing socket {i+1}/{len(all_sockets_sorted)} for net {net_name}")
            
            # Get the bus for this net
            bus = self.buses.get(net_name)
            if not bus:
                print(f"🔴 No bus found for net {net_name}")
                continue
            
            # Find nearest point on the bus
            bus_point = self._find_point_on_bus(socket_pos, bus)
            print(f"🔵 Routing socket at {socket_pos} to bus point at {(bus_point.x, bus_point.y)}")
            
            # Route the socket to the bus
            path = self._route_socket_to_bus(self.base_grid, socket_pos, bus_point, net_name)
            
            if path:
                print(f"🟢 Found path for socket at {socket_pos} to bus")
                self.trace_indexes[net_name].append(path)
            else:
                print(f"🔴 No path found for socket at {socket_pos} to bus")
        
        # Now, handle remaining sockets that don't have buses (typically for filled zones)
        print(f"🟢 Processing sockets for filled zones")
        for net_name, locations in socket_locations.items():
            # Skip if this net was already handled (has a bus)
            if net_name in bus_nets:
                continue
                
            # Check if this net is in a filled layer
            if net_name in fill_nets:
                print(f"🟢 Processing {len(locations)} sockets for filled net {net_name}")
                for socket_pos in locations:
                    print(f"🟢 Placing a via for {net_name} net at {socket_pos}")
                    self._add_via(net_name, self._to_grid_indices(socket_pos[0], socket_pos[1]))
            else:
                print(f"🔴 Net {net_name} has no bus and is not in a filled layer")
    
        # Consolidate grid paths to segments (also adds to board layers)
        self._convert_trace_indexes_to_segments()
        
        # Convert via indexes to points (also adds to board layers)
        self._convert_via_indexes_to_points()