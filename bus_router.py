import numpy as np
from collections import defaultdict
from typing import Dict, List, Tuple

from pathfinding.core.grid import Grid
from pathfinding.finder.a_star import AStarFinder
from pathfinding.finder.breadth_first import BreadthFirstFinder
from pathfinding.core.diagonal_movement import DiagonalMovement

from board import Board
from layer import Layer
from objects import Point, Segment

from router import Router
    
class BusRouter(Router):
    """
    A router that creates a vertical bus for each net and connects sockets to the bus.
    """
    
    def __init__(self, board: Board, tracks_layer: Layer, buses_layer: Layer, side: str) -> None:

        # Call the parent's __init__ method
        super().__init__(board)
        
        self.bus_segments = Dict[str, Segment]
        self.total_buses_width: float = 0.0

        # Configuration for bus spacing and traces
        self.track_width = board.loader.track_width
        self.bus_width = board.loader.bus_width
        self.bus_spacing = board.loader.bus_spacing
        self.edge_clearance = board.loader.edge_clearance
        
        self.tracks_layer = tracks_layer
        self.buses_layer = buses_layer
        self.side = self._verify_side(side)
        
        # Create bus segments 
        self.bus_segments = self._create_buses(tracks_layer, buses_layer)
    
    def _verify_side(self, side: str) -> str:
        """
        Verify if the provided side is valid.
        
        Parameters:
            side: The side to verify (should be 'top' or 'bottom')
            
        Returns:
            str: The verified side
        """
        if side not in ['top', 'bottom', 'left', 'right']:
            raise ValueError(f"🔴 Invalid side '{side}'. Must be 'top' or 'bottom'")
        
        return side
          
    def _create_buses(self, tracks_layer: Layer, buses_layer: Layer) -> Dict[str, Segment]:
        """Calculate positions and create vertical bus segments for each net."""
        # The corner radius determines the vertical length of the buses
        corner_radius = self.board.loader.fabrication_options['rounded_corner_radius']
        
        # Start position for first bus
        first_bus_x_position: float = (-self.board.width / 2) + self.edge_clearance
                
        # Vertical offset for buses
        offset = corner_radius if corner_radius > 0 else self.edge_clearance
        
        # Calculate the y extents for buses
        bus_upper_y = (self.board.height / 2) - offset
        bus_lower_y = (-self.board.height / 2) + offset
        
        # Create result dictionary for bus segments
        bus_segments: Dict[str, Segment] = {}
        
        # Calculate positions and create segments for each net
        current_x_position: float = first_bus_x_position
        
        for net in tracks_layer.nets:
            # Create segment points
            start_point = Point(current_x_position, bus_upper_y)
            end_point = Point(current_x_position, bus_lower_y)
            
            # Create segment with layer and width (all buses go on back layer)
            bus_segment = Segment(start_point, end_point, layer=buses_layer.name, width=self.bus_width, net=net)
            
            self.buses_layer.add_segment(bus_segment) # Add segment to buses layer
            bus_segments[net] = bus_segment # Store bus segment
            
            # Move to the next x position
            current_x_position += self.bus_spacing
        
        # Store clearance needed for the buses
        self.total_buses_width = current_x_position + (self.board.width / 2)
        
        print(f"🟢 Created {len(bus_segments)} bus segments")
        return bus_segments

    def _get_point_on_bus(self, socket_pos: Tuple[float, float], bus: Segment) -> Point:
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
        
        return Point(x_position, clamped_y_position)
    
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
            bus = self.bus_segments.get(net_name)
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

    def custom_heuristic(self, dx: int, dy: int) -> float:
        """
        Custom heuristic for A* pathfinding.
        
        Parameters:
            dx: The x-coordinate difference
            dy: The y-coordinate difference
            
        Returns:
            float: The heuristic value
        """
        # Use Manhattan distance
        return dx + dy
    
    def _route_socket_to_bus(self, grid: np.ndarray, socket_coordinate: Tuple[float, float], 
                                    bus_connection_coordinates: Point, net_name: str) -> List[Tuple[int, int, int]]:
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
        current_grid = self._mark_obstacles_on_grid(grid, net_name)
        
        # Apply socket margin to ensure the socket is routable
        socket_index = self._coordinates_to_indices(socket_coordinate[0], socket_coordinate[1])

        current_grid = self._apply_socket_margins(current_grid, socket_index)
        # Mark the socket position as free
        
        # Convert to grid indices
        bus_connection_index = self._coordinates_to_indices(bus_connection_coordinates.x, bus_connection_coordinates.y)
        
        # For sockets to the right of the bus, we'll target a point
        # to the left of the bus (so paths have to cross the bus)
        target_column_index = 0  # Use left edge of grid as target
        
        # If socket is to the left of the bus, we'll target a point
        # to the right of the bus (so paths have to cross the bus)
        if socket_index[0] < bus_connection_index[0]:
            target_column_index = self.grid_width - 1 # Use right edge of grid as target
        
        # Create pathfinding grid
        pathfinding_grid = Grid(matrix=current_grid, grid_id=0)
        
        # Set up the pathfinder
        if self.board.algorithm == "breadth_first":
            finder = BreadthFirstFinder()
        else:  # default to A*
            finder = AStarFinder(heuristic=self.custom_heuristic)
        
        # Configure diagonal movement
        if self.board.allow_diagonal_traces:
            finder.diagonal_movement = DiagonalMovement.only_when_no_obstacle
        else:
            finder.diagonal_movement = DiagonalMovement.never
        
        # Find path
        start = pathfinding_grid.node(socket_index[0], socket_index[1])
        end = pathfinding_grid.node(target_column_index, bus_connection_index[1])
        
        try:
            path, runs = finder.find_path(start, end, pathfinding_grid)
            print(f"🔵 Pathfinding runs: {runs}")
            
            if path:
                # Find where the path crosses the bus column
                chopped_path = []
                bus_crossed = False
                
                # For paths from the right of the bus to the left
                if socket_index[0] > bus_connection_index[0]:
                    for i, node in enumerate(path):
                        if node.x <= bus_connection_index[0]:
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
                        if node.x >= bus_connection_index[0]:
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
                    print(f"🔴 Path never crossed the bus column at {bus_connection_index[0]}")
                    return []
                
                # Add a node exactly at the bus position if needed
                # (This ensures we connect exactly to the bus point)
                if chopped_path[-1].x != bus_connection_index[0] or chopped_path[-1].y != bus_connection_index[1]:
                    # Create a new node at the exact bus position
                    bus_node = pathfinding_grid.node(bus_connection_index[0], bus_connection_index[1])
                    # Only add if it's adjacent to the last node
                    last_node = chopped_path[-1]
                    if abs(last_node.x - bus_connection_index[0]) <= 1 and abs(last_node.y - bus_connection_index[1]) <= 1:
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
                print(f"🔴 No path found between socket at {socket_coordinate} and target")
                self.failed_routes += 1
                return []
        except Exception as e:
            print(f"🔴 Error in pathfinding: {e}")
            return []

    def _mark_obstacles_above_buses(self, grid: np.ndarray, net_to_protect: str) -> np.ndarray:
        """TODO: Make a function that marks obstacles above the bus segments"""
        
        last_bus_x_index = self._coordinates_to_indices(self.total_buses_width, 0)[0] - self.grid_width // 2

        temporary_obstacle_grid = np.copy(grid)
        
        # Find the layer for this net
        current_layer = self.board.get_layer_for_net(net_to_protect)
        
        if not current_layer:
            return temporary_obstacle_grid
        
        # Find other nets on the same layer
        for net in current_layer.nets:
            if net == net_to_protect and self.board.allow_overlap:
                continue  # Allow overlap woud allow this net to overlap (short) with itself
            
            
            # TODO: double check if the following x and y are correct, there could be a mistake leading to wrong 
            # obstacle markings above the buses, and potentially via shorts
            
            # Mark all paths on other nets as obstacles
            for path_index in self.paths_indices.get(net, []):
                for x, y, _ in path_index:
                    if 0 <= y < self.grid_height and 0 <= x < last_bus_x_index:     
                        for dx in range(-1, 2): # 2 extra grid cells of keep out on left and right                   
                            nx = path_index[1] + dx
                            temporary_obstacle_grid[y, nx] = self.BLOCKED_CELL
        
        # Ensure the first column is always free   
        for y in range(self.grid_height):
            temporary_obstacle_grid[y, 0] = self.FREE_CELL
            
        return temporary_obstacle_grid
    
        
    def route(self) -> None:
        """
        Route sockets to buses for all nets, prioritizing by proximity.
        
        The routing happens in two phases:
        - First, route all sockets that have buses using your proximity sorting
        - Then, process the remaining sockets that don't have buses but are in filled layers (need vias)
        
        Returns:
            None
        """
        if not self.board.sockets:
            print("No sockets to route")
            return
        
        # Get socket locations and all layers
        socket_locations = self.board.sockets.get_data()
        layers = self.board.layers

        # Filter for layers with fill=False
        non_fill_layers = [layer for layer in layers if not layer.fill]
        fill_layers = [layer for layer in layers if layer.fill]
        
        bus_nets = []
        fill_nets = []
        
        for layer in non_fill_layers:
            for net in layer.nets:
                bus_nets.append(net)
        
        for layer in fill_layers:
            for net in layer.nets:
                fill_nets.append(net)
        
        # Sort ALL sockets from all nets by proximity to their buses
        all_sockets_sorted = self._sort_all_sockets_by_proximity(socket_locations)
        
        print(f"🟢 Routing {len(all_sockets_sorted)} sockets with buses")
        
        # Route each socket in order of proximity
        for i, (net_name, socket_coordinate) in enumerate(all_sockets_sorted):
            print(f"🟢 Routing socket {i+1}/{len(all_sockets_sorted)} for net {net_name}")
            
            # Get the bus for this net
            bus = self.bus_segments.get(net_name)
            if not bus:
                print(f"🔴 No bus found for net {net_name}")
                continue
            
            # Find nearest point on the bus
            bus_point = self._get_point_on_bus(socket_coordinate, bus)
            print(f"🔵 Routing socket at {socket_coordinate} to bus point at {(bus_point.x, bus_point.y)}")
            
            # Route the socket to the bus
            path = self._route_socket_to_bus(self.base_grid, socket_coordinate, bus_point, net_name)
            
            if path:
                print(f"🟢 Found path for socket at {socket_coordinate} to bus")
                self.paths_indices[net_name].append(path)
            else:
                print(f"🔴 No path found for socket at {socket_coordinate} to bus")
        
        # Now, handle remaining sockets that don't have buses (typically for filled zones)
        print(f"🟢 Processing sockets for filled zones")
        for net_name, locations in socket_locations.items():
            # Skip if this net was already handled (has a bus)
            if net_name in bus_nets:
                continue
                
            # Check if this net is in a filled layer
            if net_name in fill_nets:
                print(f"🟢 Processing {len(locations)} sockets for filled net {net_name}")
                for socket_coordinate in locations:
                    print(f"🟢 Placing a via for {net_name} net at {socket_coordinate}")
                    self._add_via(net_name, self._coordinates_to_indices(socket_coordinate[0], socket_coordinate[1]))
            else:
                print(f"🔴 Net {net_name} has no bus and is not in a filled layer")
    
        # Consolidate grid paths to segments (also adds to board layers)
        self._convert_trace_indices_to_segments()
        
        # Convert via indexes to points (also adds to board layers)
        self._convert_via_indexes_to_points()
