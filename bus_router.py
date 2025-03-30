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
import debug
    
class BusRouter(Router):
    """
    A router that creates a vertical bus for each net and connects sockets to the bus.
    Supports buses on either the left or right side.
    """
    
    def __init__(self, board: Board, tracks_layer: Layer, buses_layer: Layer, side: str) -> None:

        # Call the parent's __init__ method
        super().__init__(board)
        
        self.bus_segments = Dict[str, Segment]

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
            side: The side to verify (should be 'left' or 'right')
            
        Returns:
            str: The verified side
        """
        if side not in ['left', 'right']:
            raise ValueError(f"🔴 Invalid side '{side}'. Must be 'left' or 'right'")
        
        return side
          
    def _create_buses(self, tracks_layer: Layer, buses_layer: Layer) -> Dict[str, Segment]:
        """
        Calculate positions and create vertical bus segments for each net.
        Bus position depends on the specified side. Also creates a zone for the bus area.
        """
        # The corner radius determines the vertical length of the buses
        corner_radius = self.board.loader.rounded_corner_radius
                
        # Vertical offset for buses
        offset = corner_radius if corner_radius > 0 else self.edge_clearance
        
        # Calculate the y extents for buses
        bus_upper_y = (self.board.height / 2) - offset
        bus_lower_y = (-self.board.height / 2) + offset
        
        bus_zone: Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]]
        
        # Create result dictionary for bus segments
        bus_segments: Dict[str, Segment] = {}
        
        # Calculate positions and create segments for each net
        if self.side == 'left':
            # Start position for first bus at left edge
            first_bus_x_position: float = (-self.board.width / 2) + self.edge_clearance
            current_x_position: float = first_bus_x_position
            
            for net in tracks_layer.nets:
                # Create segment points
                start_point = Point(current_x_position, bus_upper_y)
                end_point = Point(current_x_position, bus_lower_y)
                
                # Create segment with layer and width
                bus_segment = Segment(start_point, end_point, layer=buses_layer.name, width=self.bus_width, net=net)
                
                self.buses_layer.add_segment(bus_segment) # Add segment to buses layer
                bus_segments[net] = bus_segment # Store bus segment
                
                # Move to the next x position (right)
                current_x_position += self.bus_spacing
            
            # Store clearance needed for the buses (for backward compatibility)
            self.board.total_buses_width = current_x_position + (self.board.width / 2)
            
            # Create and add a zone for the bus area
            zone_bottom_left = (-self.board.width / 2, -self.board.height / 2)
            zone_top_left = (-self.board.width / 2, self.board.height / 2)
            zone_top_right = (current_x_position, self.board.height / 2)
            zone_bottom_right = (current_x_position, -self.board.height / 2)
            
            # Create rectangle in (bottom_left, top_left, top_right, bottom_right) format
            bus_zone = (zone_bottom_left, zone_top_left, zone_top_right, zone_bottom_right)
            
        elif self.side == 'right':
            # Start position for first bus at right edge
            first_bus_x_position: float = (self.board.width / 2) - self.edge_clearance
            current_x_position: float = first_bus_x_position
            
            for net in tracks_layer.nets:
                # Create segment points
                start_point = Point(current_x_position, bus_upper_y)
                end_point = Point(current_x_position, bus_lower_y)
                
                # Create segment with layer and width
                bus_segment = Segment(start_point, end_point, layer=buses_layer.name, width=self.bus_width, net=net)
                
                self.buses_layer.add_segment(bus_segment) # Add segment to buses layer
                bus_segments[net] = bus_segment # Store bus segment
                
                # Move to the next x position (left)
                current_x_position -= self.bus_spacing
            
            # Store clearance needed for the buses (for backward compatibility)
            self.board.total_buses_width = (self.board.width / 2) - current_x_position
            
            # Create and add a zone for the bus area
            zone_bottom_left = (current_x_position, -self.board.height / 2)
            zone_top_left = (current_x_position, self.board.height / 2)
            zone_top_right = (self.board.width / 2, self.board.height / 2)
            zone_bottom_right = (self.board.width / 2, -self.board.height / 2)
        
        # Create rectangle in (bottom_left, top_left, top_right, bottom_right) format
        bus_zone = (zone_bottom_left, zone_top_left, zone_top_right, zone_bottom_right)
        self.board.zones.add_zone(bus_zone)
        
        # Validate zones and modules once again
        self.board._validate_zones_and_modules()
        
        print(f"🟢 Created {len(bus_segments)} bus segments on {self.side} side")
        print(f"🟢 Added bus zone for {self.side} side")
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
    
    def _mark_obstacles_above_buses(self, grid: np.ndarray, net_to_protect: str) -> np.ndarray:
        """
        Mark obstacle cells to prevent traces from crossing over other traces in the bus area.
        
        Parameters:
            grid: The obstacle grid
            net_to_protect: The name of the net to protect from obstacles
            
        Returns:
            np.ndarray: Updated obstacle grid
        """
        temporary_obstacle_grid = np.copy(grid)
        
        # Determine the bus boundary depending on the side
        if self.side == 'left':
            # Convert board coordinates to grid indices
            bus_boundary_x_index = self._coordinates_to_indices(self.board.total_buses_width, 0)[0]
            # Ensure this index isn't beyond the grid width
            last_bus_x_index = min(bus_boundary_x_index, self.grid_width - 1)
            
            # Define column range for obstacles
            start_col = 0  # Left edge
            end_col = last_bus_x_index
        elif self.side == 'right':
            # For right side, calculate the position from the right edge
            bus_boundary_x = (self.board.width / 2) - self.board.total_buses_width
            bus_boundary_x_index = self._coordinates_to_indices(bus_boundary_x, 0)[0]
            
            # Ensure this index isn't below 0
            first_bus_x_index = max(bus_boundary_x_index, 0)
            
            # Define column range for obstacles
            start_col = first_bus_x_index
            end_col = self.grid_width - 1  # Right edge
        
        # Find the layer for this net
        current_layer = self.board.get_layer_for_net(net_to_protect)
        
        if not current_layer:
            return temporary_obstacle_grid
        
        # Find other nets on the same layer
        for net in current_layer.nets:
            if net == net_to_protect and self.board.allow_overlap:
                continue  # Allow overlap would allow this net to overlap (short) with itself
            
            # Mark all paths in the bus area with a larger keep-out zone around it
            for path_index in self.paths_indices.get(net, []):
                for x, y, _ in path_index:
                    if 0 <= y < self.grid_height and start_col <= x <= end_col:     
                        for dy in range(-1, 2): # 2 extra grid cells of keep out on left and right
                            for dx in range(-1, 2): # 1 extra grid cell of keep out on top and bottom
                                ny, nx = y + dy, x + dx
                                if 0 <= ny < self.grid_height and 0 <= nx < self.grid_width:
                                    temporary_obstacle_grid[ny, nx] = self.BLOCKED_CELL
        
        # Ensure edge columns are always free
        if self.side == 'left':
            # For left side, keep leftmost column free
            for y in range(self.grid_height):
                temporary_obstacle_grid[y, 0] = self.FREE_CELL
        elif self.side == 'right':
            # For right side, keep rightmost column free
            for y in range(self.grid_height):
                temporary_obstacle_grid[y, self.grid_width - 1] = self.FREE_CELL
            
        return temporary_obstacle_grid
    
    def _route_socket_to_bus(self, grid: np.ndarray, socket_coordinate: Tuple[float, float], 
                                    bus_connection_coordinates: Point, net_name: str) -> List[Tuple[int, int, int]]:
        """
        Route a socket to the bus, taking into account which side the buses are on.
        
        Parameters:
            grid: The base grid for pathfinding
            socket_coordinate: The (x, y) coordinate of the socket
            bus_connection_coordinates: The target point on the bus
            net_name: The name of the net being routed
            
        Returns:
            List of (x, y, layer) tuples representing the path
        """
        # Apply obstacles from other nets on the same layer
        current_grid = self._mark_obstacles_on_grid(grid, net_name)
        current_grid = self._mark_obstacles_above_buses(current_grid, net_name)
        
        # Apply socket margin to ensure the socket is routable
        socket_index = self._coordinates_to_indices(socket_coordinate[0], socket_coordinate[1])

        # Mark GerberSockets accordingly
        current_grid = self._apply_socket_margins(current_grid, socket_index)
        
        # Convert to grid indices
        bus_connection_index = self._coordinates_to_indices(bus_connection_coordinates.x, bus_connection_coordinates.y)
        
        # Determine target column based on the side and socket position
        if self.side == 'left':
            # For left side: sockets to the right of the bus target the left edge
            # sockets to the left of the bus target the right edge
            target_column_index = 0 if socket_index[0] > bus_connection_index[0] else self.grid_width - 1
        elif self.side == 'right':
            # For right side: sockets to the left of the bus target the right edge
            # sockets to the right of the bus target the left edge
            target_column_index = self.grid_width - 1 if socket_index[0] < bus_connection_index[0] else 0
        
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
                
                # Adjust crossing detection based on the side
                if self.side == 'left':
                    # For left side buses
                    if socket_index[0] > bus_connection_index[0]:
                        # Socket is to the right of the bus
                        for i, node in enumerate(path):
                            chopped_path.append(node)
                            if node.x <= bus_connection_index[0]:
                                bus_crossed = True
                                break
                    else:
                        # Socket is to the left of the bus
                        for i, node in enumerate(path):
                            chopped_path.append(node)
                            if node.x >= bus_connection_index[0]:
                                bus_crossed = True
                                break
                elif self.side == 'right':
                    # For right side buses
                    if socket_index[0] < bus_connection_index[0]:
                        # Socket is to the left of the bus
                        for i, node in enumerate(path):
                            chopped_path.append(node)
                            if node.x >= bus_connection_index[0]:
                                bus_crossed = True
                                break
                    else:
                        # Socket is to the right of the bus
                        for i, node in enumerate(path):
                            chopped_path.append(node)
                            if node.x <= bus_connection_index[0]:
                                bus_crossed = True
                                break
                
                # If we never crossed the bus, something went wrong
                if not bus_crossed:
                    print(f"🔴 Path never crossed the bus column at {bus_connection_index[0]}")
                    return []
                
                # Add a node exactly at the bus position if needed
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
                return []
        except Exception as e:
            print(f"🔴 Error in pathfinding: {e}")
            return []
            
    def route(self) -> None:
        """
        Route sockets to buses with adaptive routing strategy that dynamically
        changes the routing order when pathfinding fails.
        
        Strategy:
        1. Sort sockets left-to-right, then top-to-bottom
        2. Group sockets by module on the x-axis and y-axis
        3. If routing fails, backtrack and reorder subsequent sockets in that group
        """    
        # Get the socket locations for the tracks layer
        socket_locations = self.board.sockets.get_socket_positions_for_nets(self.tracks_layer.nets)
        
        # Step 1: Collect all sockets with their metadata
        all_sockets = []
        for net_name, locations in socket_locations.items():
            bus = self.bus_segments.get(net_name)
            if not bus:
                continue
                
            for socket_pos in locations:
                socket_x, socket_y = socket_pos
                all_sockets.append((net_name, socket_pos, socket_x, socket_y))
        
        # Step 2: Group sockets by zone
        zones_data = self.board.zones.get_data()
        sockets_by_zone = {}
        
        for socket_info in all_sockets:
            net_name, socket_pos, x, y = socket_info
            
            # Find which zone this socket belongs to
            assigned_zone = None
            for zone_idx, zone in enumerate(zones_data):
                bottom_left, top_left, top_right, bottom_right = zone
                
                # Check if socket is within this zone
                if (bottom_left[0] <= x <= top_right[0] and 
                    bottom_left[1] <= y <= top_left[1]):
                    assigned_zone = zone_idx
                    break
            
            # Add socket to its zone group
            if assigned_zone is not None:
                if assigned_zone not in sockets_by_zone:
                    sockets_by_zone[assigned_zone] = []
                sockets_by_zone[assigned_zone].append(socket_info)
        
        # Step 3: Sort sockets within each zone (different order based on side)
        for zone_idx in sockets_by_zone:
            if self.side == 'left':
                # For left side buses, left-to-right priority
                sockets_by_zone[zone_idx].sort(key=lambda s: (s[2], -s[3]))  # Sort by x, then -y
            elif self.side == 'right':
                # For right side buses, right-to-left priority
                sockets_by_zone[zone_idx].sort(key=lambda s: (-s[2], -s[3]))  # Sort by -x, then -y
        
        # Step 4: Create a queue of sockets to route
        routing_queue = []
        for zone_idx in sorted(sockets_by_zone.keys()):
            for socket_info in sockets_by_zone[zone_idx]:
                net_name, socket_pos, x, y = socket_info
                routing_queue.append((zone_idx, net_name, socket_pos, x, y))
        
        # Step 5: Track zone routing orders and already routed sockets
        zone_orders = {}  # Maps zone_idx -> {(x,y) -> direction}
        zone_routed = {}  # Maps zone_idx -> list of routed sockets
        
        for zone_idx in sockets_by_zone:
            zone_orders[zone_idx] = {}
            zone_routed[zone_idx] = []
        
        # Step 6: Route each socket with backtracking when needed
        print(f"🟢 Routing {len(routing_queue)} sockets with buses on {self.side} side")
        i = 0
        while i < len(routing_queue):
            zone_idx, net_name, socket_coordinate, x, y = routing_queue[i]
            
            print(f"🟢 Routing socket {i+1}/{len(routing_queue)} for net {net_name}")
            
            # Get the bus for this net
            bus = self.bus_segments.get(net_name)
            if not bus:
                print(f"🔴 No bus found for net {net_name}")
                i += 1
                continue
            
            # Find nearest point on the bus
            bus_point = self._get_point_on_bus(socket_coordinate, bus)
            print(f"🔵 Routing socket at {socket_coordinate} to bus point at {(bus_point.x, bus_point.y)}")
            
            # Route the socket to the bus
            path = self._route_socket_to_bus(self.base_grid, socket_coordinate, bus_point, net_name)

            if debug.do_video:
                debug.show_grid_routes_sockets(self.base_grid, self.paths_indices, socket_locations, self.board.loader.resolution)
            
            if path:
                print(f"🟢 Found path for socket at {socket_coordinate} to bus")
                self.paths_indices[net_name].append(path)
                
                # Add to routed sockets for this zone
                zone_routed[zone_idx].append((net_name, socket_coordinate, x, y))
                
                # Remember the current direction for this coordinate group
                coord_key = (x, y)
                if coord_key not in zone_orders[zone_idx]:
                    zone_orders[zone_idx][coord_key] = 1  # 1 = original order
                
                # Keep track of the number of connected sockets on the board
                i += 1
                self.board.connected_sockets_count += 1
            else:
                print(f"🔴 No path found for socket at {socket_coordinate} to bus")
                
                # Backtracking logic - only if we've routed at least one socket in this zone
                if zone_routed[zone_idx]:
                    print(f"🟡 Backtracking in zone {zone_idx}")
                    
                    # Find all sockets in this zone with the same x-coordinate
                    same_x_sockets = [(idx, s) for idx, s in enumerate(routing_queue) 
                                    if s[0] == zone_idx and s[3] == x]
                    
                    # If multiple sockets with same x-coordinate exist
                    if len(same_x_sockets) > 1:
                        # Find which ones we've already routed and which ones are left
                        routed_indices = []
                        
                        for r_net, r_pos, r_x, r_y in zone_routed[zone_idx]:
                            if r_x == x:
                                # Find the index in the routing queue
                                for q_idx, q_item in enumerate(routing_queue):
                                    if (q_item[0] == zone_idx and q_item[1] == r_net and 
                                        q_item[2] == r_pos):
                                        routed_indices.append(q_idx)
                                        break
                        
                        # If we have at least one routed socket with this x
                        if routed_indices:
                            # Get the last routed socket
                            last_routed_idx = max(routed_indices)
                            last_zone, last_net, last_pos, last_x, last_y = routing_queue[last_routed_idx]
                            
                            # Remove its path
                            for path_idx, path in enumerate(self.paths_indices.get(last_net, [])):
                                # Check if this path connects to the socket we're removing
                                socket_indices = self._coordinates_to_indices(last_pos[0], last_pos[1])
                                if path and path[0][0] == socket_indices[0] and path[0][1] == socket_indices[1]:
                                    del self.paths_indices[last_net][path_idx]
                                    
                                    # Also remove the via at the end of the path
                                    connection_point = path[-1]
                                    for via_idx, via in enumerate(self.vias_indices.get(last_net, [])):
                                        if via[0] == connection_point[0] and via[1] == connection_point[1]:
                                            del self.vias_indices[last_net][via_idx]
                                            break
                                    break
                            
                            # Remove this socket from the routed list
                            for r_idx, (r_net, r_pos, r_x, r_y) in enumerate(zone_routed[zone_idx]):
                                if r_net == last_net and r_pos == last_pos:
                                    del zone_routed[zone_idx][r_idx]
                                    break
                            
                            # Get all unrouted sockets with this x (including the one that just failed)
                            unrouted_sockets = []
                            current_idx = i
                            
                            # Track the current socket that failed
                            current_socket = routing_queue[current_idx]
                            
                            # Start from the last routed socket that we just removed
                            for q_idx in range(last_routed_idx, len(routing_queue)):
                                q_item = routing_queue[q_idx]
                                if q_item[0] == zone_idx and q_item[3] == x:  # Same zone and x
                                    unrouted_sockets.append((q_idx, q_item))
                            
                            # Change the ordering direction for these sockets
                            coord_key = (x, y)
                            if coord_key in zone_orders[zone_idx]:
                                zone_orders[zone_idx][coord_key] *= -1  # Flip the direction
                            else:
                                zone_orders[zone_idx][coord_key] = -1  # Start with reversed order
                            
                            # Sort unrouted sockets based on the new direction
                            direction = zone_orders[zone_idx][coord_key]
                            
                            if direction == 1:  # Top to bottom
                                unrouted_sockets.sort(key=lambda s: -s[1][4])  # Sort by -y
                            else:  # Bottom to top
                                unrouted_sockets.sort(key=lambda s: s[1][4])   # Sort by y
                            
                            # Replace sockets in routing queue with reordered ones
                            for new_idx, (old_idx, socket) in enumerate(unrouted_sockets):
                                routing_queue[last_routed_idx + new_idx] = socket
                            
                            # Reset index to retry routing from the last routed point
                            i = last_routed_idx
                            
                            print(f"🟢 Backtracking succeeded! Reordered {len(unrouted_sockets)} sockets in zone {zone_idx}")
                            continue

                # If no backtracking was done or possible, just skip this socket
                i += 1
                self.failed_routes += 1
                print(f"🔴 Failed to route socket {i} in zone {zone_idx}")
        
        # Consolidate grid paths to segments (also adds to board layers)
        self._convert_trace_indices_to_segments()
        
        # Convert via indexes to points (also adds to board layers)
        self._convert_via_indexes_to_points()
