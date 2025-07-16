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

from thread_context import thread_context
    
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
                    
                    if self.tracks_layer.name != "F_Cu.gtl":
                        # Add via to the location of the socket
                        self._add_via(net_name, (socket_index[0], socket_index[1]))
                        
                # Convert path to tuples with layer information
                path_tuples = [(node.x, node.y, -1) for node in chopped_path]
                return path_tuples
            else:
                print(f"🟡 No path found between socket at {socket_coordinate} and bus")
                return []
        except Exception as e:
            print(f"🔴 Error in pathfinding: {e}")
            return []
           
    def _group_sockets(self, sockets_data, zones_data):
        """
        Group sockets that appear on the same line on a zone edge and sort them
        based on the routing side.
        
        Parameters:
            sockets_data: Dict mapping net names to lists of socket positions
            zones_data: List of zone rectangles
            
        Returns:
            OrderedDict mapping zone center point to list of sorted socket groups,
            with zones sorted according to routing side
        """
        from collections import OrderedDict
        
        # Initialize result structure
        socket_groups = defaultdict(list)
        
        # Calculate zone centers first
        zone_centers = []
        for zone in zones_data:
            bottom_left, top_left, top_right, bottom_right = zone
            center_x = (bottom_left[0] + top_right[0]) / 2
            center_y = (bottom_left[1] + top_right[1]) / 2
            zone_centers.append((center_x, center_y))
        
        # Organize all sockets by zone
        zone_sockets = defaultdict(list)
        for net_name, positions in sockets_data.items():
            for socket_pos in positions:
                socket_x, socket_y = socket_pos
                
                # Find which zone this socket belongs to
                for zone_idx, zone in enumerate(zones_data):
                    bottom_left, top_left, top_right, bottom_right = zone
                    
                    # Check if socket is within this zone
                    if (bottom_left[0] <= socket_x <= top_right[0] and 
                        bottom_left[1] <= socket_y <= top_right[1]):
                        # Add to zone's sockets using center as key
                        zone_center = zone_centers[zone_idx]
                        zone_sockets[zone_center].append((net_name, socket_pos))
                        break

        # Print all zone sockets for debugging
        for zone_center, sockets in zone_sockets.items():
            print(f"Zone center: {zone_center}, Sockets: {sockets}")
        
        # Track which sockets have been added to groups
        added_sockets = set()
        
        # For each zone, group sockets by alignment
        for zone_center, sockets in zone_sockets.items():
            # Group by x-coordinate (vertical alignment)
            x_groups = defaultdict(list)
            # Group by y-coordinate (horizontal alignment)
            y_groups = defaultdict(list)
            
            for socket_info in sockets:
                net_name, socket_pos = socket_info
                socket_x, socket_y = socket_pos
                x_groups[socket_x].append(socket_info)
                y_groups[socket_y].append(socket_info)
            
            # Store all groups with position information
            all_groups = []
            
            # Add multi-socket vertical groups
            for x, group in x_groups.items():
                if len(group) > 1: 
                    # Sort vertically aligned sockets from top to bottom (decreasing y)
                    sorted_group = sorted(group, key=lambda s: -s[1][1])
                    # Add group with its x position
                    all_groups.append((x, sorted_group))
                    
                    # Mark these sockets as added
                    for socket_info in group:
                        added_sockets.add((socket_info[0], tuple(socket_info[1])))
            
            # Add multi-socket horizontal groups
            for y, group in y_groups.items():
                if len(group) > 1: 
                    # Calculate the average x position for this group
                    avg_x = sum(s[1][0] for s in group) / len(group)
                    
                    # Sort horizontally aligned sockets based on routing side
                    if self.side == "left":
                        # Left to right for left side routing
                        sorted_group = sorted(group, key=lambda s: s[1][0])
                    else:  # self.side == "right"
                        # Right to left for right side routing
                        sorted_group = sorted(group, key=lambda s: -s[1][0])
                    
                    # Add group with its average x position
                    all_groups.append((avg_x, sorted_group))
                    
                    # Mark these sockets as added
                    for socket_info in group:
                        added_sockets.add((socket_info[0], tuple(socket_info[1])))
            
            # Now add any single sockets that weren't part of a multi-socket group
            for socket_info in sockets:
                socket_key = (socket_info[0], tuple(socket_info[1]))
                if socket_key not in added_sockets:
                    # Use the socket's x position
                    x = socket_info[1][0]
                    all_groups.append((x, [socket_info]))
                    added_sockets.add(socket_key)
            
            # Sort all groups by distance from edge
            if self.side == "left":
                # For left routing: sort by x position, leftmost first
                all_groups.sort(key=lambda g: g[0])
            else:  # self.side == "right"
                # For right routing: sort by x position, rightmost first
                all_groups.sort(key=lambda g: -g[0])
            
            # Extract the sorted groups
            socket_groups[zone_center] = [group for _, group in all_groups]
        
        # Sort zones and create an ordered dictionary
        sorted_zones = list(socket_groups.keys())
        
        # Sort zones based on routing side: horizontal position first, then vertical
        if self.side == "left":
            # For left routing: left-to-right, then top-to-bottom
            sorted_zones.sort(key=lambda center: (center[0], -center[1]))
        else:  # self.side == "right"
            # For right routing: right-to-left, then top-to-bottom
            sorted_zones.sort(key=lambda center: (-center[0], -center[1]))
        
        # Create ordered dictionary with sorted zone keys
        ordered_socket_groups = OrderedDict()
        for zone_center in sorted_zones:
            ordered_socket_groups[zone_center] = socket_groups[zone_center]

        # Print ordered socket groups for debugging
        for zone_center, groups in ordered_socket_groups.items():
            print(f"Ordered zone center: {zone_center}, Groups: {groups}")
        
        return ordered_socket_groups
    
    def route(self) -> None:
        # Get all of the sockets for the tracks layer
        sockets_data = self.board.sockets.get_socket_positions_for_nets(self.tracks_layer.nets)
        
        # Get the total number of sockets
        total_sockets = sum(len(positions) for positions in sockets_data.values())
        
        # Group them by zone, and orientation (in a row, or in a column)
        zones_data = self.board.zones.get_data()
        
        # Group sockets by zone edges and order them top-to-bottom or left-to-right
        grouped_sockets = self._group_sockets(sockets_data, zones_data)
        
        socket_count = 1
        
        for zone_center, socket_groups in grouped_sockets.items():
            
            module_name = self.board.get_module_name_from_position(zone_center)
            
            # For each group of sockets
            for group_idx, socket_group in enumerate(socket_groups):
                i = 0
                
                # Process all sockets in the group
                print(f"Socket group length: {len(socket_group)}")
                while i < len(socket_group):
                    socket = socket_group[i]
                    net_name, socket_pos = socket
                    
                    # Check if this socket has already failed
                    socket_key = (net_name, tuple(socket_pos))

                    # Get the bus for this net
                    bus = self.bus_segments.get(net_name)
                    if not bus:
                        print(f"🔴 No bus found for net {net_name}")
                        i += 1
                        socket_count += 1
                        continue
                    
                    # Find nearest point on the bus
                    bus_point = self._get_point_on_bus(socket_pos, bus)
                    
                    # Route the socket to the bus
                    print(f"🔵 Routing socket {socket_count}/{total_sockets} for net {net_name} for module {module_name}")

                    # Progress bar update
                    if self.board.loader.run_from_server:
                        all = self.board.sockets.get_socket_count()
                        connected = self.board.connected_sockets_count
                        progress = round(float(connected) / float(all), 4) * 100
                        print(f"🔵 Updating progress: {progress}")
                        # Write the progress to a file
                        # TODO: A better way to do progress updates?
                        # should get the board variable from a running thread, but that
                        # requires keeping track of what threads are running and what job ids
                        # they have... this is easier
                        with open(thread_context.job_folder / "progress.txt", 'w') as file:
                            file.write(str(progress))


                    path = self._route_socket_to_bus(self.base_grid, socket_pos, bus_point, net_name)
                    
                    if debug.do_video:
                        debug.show_grid_routes_sockets(self.base_grid, self.paths_indices, 
                            self.board.sockets.get_socket_positions_for_nets(self.tracks_layer.nets), 
                            self.board.loader.resolution)
                    
                    if path:
                        print(f"🟢 Found path for socket at {socket_pos} to bus\n")
                        
                        # Add path indices
                        self.paths_indices[net_name].append(path)
                        
                        # Add to routed sockets count
                        self.board.connected_sockets_count += 1                
                        
                        # Move to the next socket
                        i += 1
                        socket_count += 1
                    else:                        
                        # If this is the first socket in the group, routing failed
                        if i == 0:
                            print(f"🔴 Routing failed for the first socket in group and cannot backtrack\n")
                            i += 1
                            socket_count += 1
                            continue
                        
                        # Otherwise, we can backtrack
                        print(f"🟠 Backtracking in group {group_idx} at socket {i}")
                        
                        # Get the previously routed socket
                        previous_socket = socket_group[i-1]
                        previous_net, previous_pos = previous_socket
                        
                        # Remove its path
                        for path_idx, path in enumerate(self.paths_indices.get(previous_net, [])):
                            # Check if this path connects to the socket we're removing
                            socket_indices = self._coordinates_to_indices(previous_pos[0], previous_pos[1])
                            if path and path[0][0] == socket_indices[0] and path[0][1] == socket_indices[1]:
                                # Also remove the via at the end of the path
                                connection_point = path[-1]
                                for via_idx, via in enumerate(self.vias_indices.get(previous_net, [])):
                                    if via[0] == connection_point[0] and via[1] == connection_point[1]:
                                        del self.vias_indices[previous_net][via_idx]
                                        break
                                
                                # Now remove the path
                                del self.paths_indices[previous_net][path_idx]
                                
                                # Decrement connected sockets count
                                self.board.connected_sockets_count -= 1
                                socket_count -= 1
                                
                                break
                        
                        # Reverse the order from i-1 to the end
                        remaining = socket_group[i-1:]
                        remaining.reverse()
                        socket_group[i-1:] = remaining
                        print(f"🟢 Reversed routing order for the remaining sockets in group")
                    
                        # Restart from the previous socket position
                        i = i - 1
        
        # Convert traces and vias indices to segments (also adds to board layers)
        self._convert_trace_indices_to_segments()
        self._convert_via_indexes_to_points()

        if debug.do_video:
            debug.show_grid_routes_sockets(self.base_grid, self.paths_indices, 
                self.board.sockets.get_socket_positions_for_nets(self.tracks_layer.nets), 
                self.board.loader.resolution)
