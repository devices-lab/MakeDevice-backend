from typing import Dict, List, Tuple, Optional
import json
from collections import defaultdict
    
from gerbonara import GerberFile
from gerbonara.graphic_objects import Line
from gerbonara.apertures import CircleAperture

from loader import Loader
from debug import plot_sockets, plot_zones

class Object:
    """
    Base class for PCB objects that provides common functionality
    for Sockets and Zones.
    """
    
    def __init__(self, loader: Loader, gerber: GerberFile = None):
        """
        Initialize the base PCB object.
        
        Parameters:
            loader: The PCB data loader with configuration
            gerber: Optional GerberFile object from gerbonara
        """
        self.loader = loader
        self.gerber = gerber
        self.resolution = loader.resolution
    
    def _round_to_resolution(self, value: float, resolution: float = None) -> float:
        """
        Rounds a value to the nearest multiple of the resolution.
        
        Parameters:
            value: The value to round
            resolution: The resolution to round to (defaults to self.resolution)
            
        Returns:
            float: The rounded value
        """
        if resolution is None:
            resolution = self.resolution
        return round(value / resolution) * resolution
    
    def _is_aligned_with_resolution(self, value: float, resolution: float = None) -> bool:
        """
        Checks if a value is aligned with the resolution grid (is a multiple of resolution).
        
        Parameters:
            value: The value to check
            resolution: The resolution to check against (defaults to self.resolution)
            
        Returns:
            bool: True if the value is aligned with the resolution grid, False otherwise
        """
        if resolution is None:
            resolution = self.resolution
            
        # Account for floating point precision issues
        remainder = abs(value) % resolution
        epsilon = 1e-4  # Small tolerance for floating point comparisons
        
        return remainder < epsilon or abs(remainder - resolution) < epsilon
    
    def _get_raw_location_from_object(self, obj) -> Optional[Tuple[float, float]]:
        """
        Extract raw location coordinates from a Gerber object based on its type.
        
        Parameters:
            obj: The Gerber object
            
        Returns:
            Optional[Tuple[float, float]]: The raw (x, y) coordinates or None if not extractable
        """
        # For Line objects
        if hasattr(obj, 'x1') and hasattr(obj, 'y1'):
            return (obj.x1, obj.y1)
        
        # For Flash objects
        elif hasattr(obj, 'x') and hasattr(obj, 'y'):
            return (obj.x, obj.y)
        
        return None
    
    def save_to_file(self, file_path: str) -> None:
        """
        Save object data to a JSON file.
        
        Parameters:
            file_path: Path to save the JSON file
        """
        with open(file_path, 'w') as f:
            json.dump(self.get_data(), f, indent=2)
    
    def get_data(self) -> Dict:
        """
        Get data representation of the object.
        
        Returns:
            Dict: Data representation
        """
        raise NotImplementedError("Subclasses must implement get_data()")


class Sockets(Object):
    """
    Handles the extraction and management of socket locations from Gerber files.
    Provides methods to process and access socket data organized by net.
    """

    def __init__(self, loader: Loader, gerber: GerberFile = None):
        """
        Initialize the Sockets processor.
        
        Parameters:
            loader: The PCB data loader with configuration settings
            gerber: Optional GerberFile object from gerbonara
        """
        super().__init__(loader, gerber)
        self.socket_locations: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
        
        if self.loader and self.gerber:
            self.extract_ASCII_socket_locations()

    def extract_ASCII_socket_locations(self) -> Dict[str, List[Tuple[float, float]]]:
        """
        Extracts socket locations from Gerber objects using encoded ASCII identifiers.

        This method scans the loaded Gerber data for zero-length lines (interpreted as "circles")
        with specific aperture diameters that encode ASCII characters. It decodes these diameters
        to reconstruct net names and associates each net name with its corresponding (x, y) position.

        Returns:
            Dict[str, List[Tuple[float, float]]]: A dictionary mapping each decoded net name to a list
            of (x, y) positions where sockets for that net are located.

        Raises:
            ValueError: If no Gerber data is loaded or the Gerber object lacks the required attributes.

        Notes:
            - The encoding expects diameters in the format "0.iippp", where 'ii' is an index and 'ppp'
              is the ASCII code of the character.
            - Only diameters matching the expected format and value ranges are decoded.
            - Socket locations are stored in the `socket_locations` attribute as a defaultdict(list).
        """
        if not self.gerber or not hasattr(self.gerber, "objects"):
            raise ValueError("No Gerber data loaded.")

        # Ensure storage is a defaultdict(list)
        if not hasattr(self, "socket_locations") or not isinstance(self.socket_locations, defaultdict):
            self.socket_locations = defaultdict(list)

        # 1–2. Collect zero-length lines as “circles”
        circles = defaultdict(list)  # (x, y) -> List[float diameter]
        for obj in self.gerber.objects:
            if isinstance(obj, Line) and obj.x1 == obj.x2 and obj.y1 == obj.y2:
                ap = getattr(obj, "aperture", None)
                d = getattr(ap, "diameter", None)
                if d is not None:
                    # Optional: quantize to avoid float-key fragmentation
                    pos = (obj.x1, obj.y1)
                    circles[pos].append(float(d))

        for pos, dlist in circles.items():
            # Identifier present?
            if not any(abs(d - 0.00999) < 1e-6 for d in dlist):
                continue

            decoded: List[Tuple[int, str]] = []
            seen_indices = set()

            for d in dlist:
                s = f"{d:.5f}"
                if s == "0.00999":
                    continue
                # Expect "0.iippp" with exactly 5 decimals -> len("0.01071") == 7
                if not (s.startswith("0.") and len(s) == 7):
                    continue
                ii_str, ppp_str = s[2:4], s[4:7]
                try:
                    ii = int(ii_str)
                    code = int(ppp_str)
                except ValueError:
                    continue
                if not (1 <= ii <= 99 and 32 <= code <= 127):
                    continue
                if ii in seen_indices:
                    continue
                seen_indices.add(ii)
                decoded.append((ii, chr(code)))

            if not decoded:
                continue

            decoded.sort(key=lambda t: t[0])
            net_name = "".join(ch for _, ch in decoded)
            self.socket_locations[net_name].append(pos)

        return dict(self.socket_locations)

    def get_socket_count(self, net_name: str = None) -> int:
        """
        Get the number of sockets for a specific net or all nets.
        
        Parameters:
            net_name: Optional net name to count sockets for
            
        Returns:
            int: Number of sockets
        """
        if net_name:
            return len(self.socket_locations.get(net_name, []))
        else:
            return sum(len(sockets) for sockets in self.socket_locations.values())
        
    def get_nets(self) -> List[str]:
        """
        Get all net names that have sockets.
        
        Returns:
            List[str]: List of net names
        """
        return list(self.socket_locations.keys())
    
    def get_socket_positions_for_net(self, net: str) -> List[Tuple[float, float]]:
        """Get all socket locations for a specific net
        
        Parameters:
            net: The net name
            
        Returns:
            List[Tuple[float, float]]: List of socket locations for the net
        """
        return self.socket_locations.get(net, [])
    
    def get_socket_positions_for_nets(self, nets: List[str]) -> Dict[str, List[Tuple[float, float]]]:
        """Get all socket locations for a list of specific nets
        
        Parameters:
            nets: List of net names
            
        Returns:
            Dict[str, List[Tuple[float, float]]]: Dictionary mapping net names to lists of socket locations
        """
        result = {}
        for net in nets:
            positions = self.socket_locations.get(net, [])
            if positions:  # Only add to result if there are positions for this net
                result[net] = positions
        return result
    
    def get_all_coordinates(self) -> List[Tuple[float, float]]:
        """ Get all raw positions for all sockets """
        return [pos for net in self.socket_locations.values() for pos in net]
    
    def get_data(self) -> Dict[str, List[Tuple[float, float]]]:
        """
        Get data representation of the socket locations.
        
        Returns:
            Dict: Socket locations by net
        """
        return self.socket_locations
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'Sockets':
        """
        Load socket locations from a JSON file.
        
        Parameters:
            file_path: Path to the JSON file
            
        Returns:
            Sockets: A new Sockets instance with the loaded data
        """
        instance = cls()
        with open(file_path, 'r') as f:
            instance.socket_locations = json.load(f)
        return instance
    
    def add_socket(self, net_name: str, location: Tuple[float, float]) -> None:
        """
        Add a new socket location to a specific net.
        
        Parameters:
            net_name: The net name to add the socket to
            location: The (x, y) coordinates of the socket
        """
        # Ensure location is aligned with resolution
        x, y = location
        if not self._is_aligned_with_resolution(x) or not self._is_aligned_with_resolution(y):
            raise ValueError(f"Socket location {location} is not aligned with resolution {self.resolution}")
            
        self.socket_locations.setdefault(net_name, []).append(location)
    
    def remove_socket(self, net_name: str, location: Tuple[float, float]) -> bool:
        """
        Remove a socket location from a specific net.
        
        Parameters:
            net_name: The net name to remove the socket from
            location: The (x, y) coordinates of the socket to remove
            
        Returns:
            bool: True if the socket was removed, False otherwise
        """
        if net_name in self.socket_locations:
            try:
                self.socket_locations[net_name].remove(location)
                return True
            except ValueError:
                return False
        return False
    
    def update_net_names(self, net_mapping: Dict[str, str]) -> None:
        """
        Update socket net names according to the provided mapping.
        Used to replace special net names (e.g., with ~ and ~^) with paired names.
        
        Parameters:
            net_mapping (Dict[str, str]): Mapping from old net names to new net names
            
        Returns:
            None
        """
        # Create a new socket_locations dictionary with updated net names
        updated_socket_locations = {}
        
        # Process each net and its locations
        for net, locations in self.socket_locations.items():
            if net in net_mapping:
                # Use the new net name from the mapping
                new_net = net_mapping[net]
                print(f"🟢 Updating socket net from '{net}' to '{new_net}'")
                
                # If the new net already exists, extend its locations
                if new_net in updated_socket_locations:
                    updated_socket_locations[new_net].extend(locations)
                else:
                    updated_socket_locations[new_net] = locations.copy()
            else:
                # Keep the original net name
                updated_socket_locations[net] = locations.copy()
        
        # Replace the old socket_locations with the updated one
        self.socket_locations = updated_socket_locations
        
    def plot_extracted_sockets(self, output_file: str) -> None:
        """
        Plot the keep-out zones on a Gerber file.
        
        Parameters:
            output_file: The path to save the Gerber file
        """
        plot_sockets(self.socket_locations, output_file)


class Zones(Object):
    """
    Handles the extraction and management of keep-out zones from Gerber files.
    Provides methods to process and access zone data.
    """
    
    def __init__(self, loader: Loader =None, gerber=None):
        """
        Initialize the Zones processor.
        
        Parameters:
            loader: The PCB data loader with configuration settings
            gerber: Optional GerberFile object from gerbonara
        """
        super().__init__(loader, gerber)
        self.zone_rectangles: List[Tuple[Tuple[float, float], Tuple[float, float], 
                                        Tuple[float, float], Tuple[float, float]]] = []
        
        if self.loader and self.gerber:
            self.extract_keep_out_zones()
    
    # FIXME: This is just a mess, can we simplify it? It's pretty sloppy right now
    def extract_keep_out_zones(self, debug=False) -> List[Tuple]:
        """
        Extracts and returns a list of rectangles representing the keep-out zones from the given Gerber object.
        Validates that zone coordinates align with the grid resolution.
        
        Parameters:
            debug (bool): If True, the function will draw the keep-out zones on a separate Gerber file.
        
        Returns:
            List[Tuple]: A list of tuples representing the rectangles of the keep-out zones.
            Each tuple contains four points in the order (bottom_left, top_left, top_right, bottom_right).
            
        Raises:
            ValueError: If any zone coordinate is not aligned with the resolution grid.
        """
        if not self.gerber:
            raise ValueError("Gerber file not provided.")
        
        if not self.loader:
            raise ValueError("Loader with configuration not provided.")
        
        module_margin = self.loader.module_margin
        resolution = self.resolution
        
        # Extract Line objects
        raw_lines = []
        for obj in getattr(self.gerber, "objects", []):
                if isinstance(obj, Line):
                    if not (obj.x1 == obj.x2 and obj.y1 == obj.y2):
                        raw_lines.append(obj)

        self.zone_rectangles = []
        used_indices = set()
        alignment_errors = []

        def find_continuation(current_index):
            current_line = raw_lines[current_index]
            x2, y2 = current_line.x2, current_line.y2
            for index, line in enumerate(raw_lines):
                if index not in used_indices and index != current_index:
                    # Check connection
                    if (abs(line.x1 - x2) < 1e-4 and abs(line.y1 - y2) < 1e-4) or \
                       (abs(line.x2 - x2) < 1e-4 and abs(line.y2 - y2) < 1e-4):
                        return index
            return None

        for index, line in enumerate(raw_lines):
            if index in used_indices:
                continue
                
            current_index = index
            rectangle_indices = [current_index]

            for _ in range(3):
                next_index = find_continuation(current_index)
                if next_index is not None:
                    rectangle_indices.append(next_index)
                    current_index = next_index
                else:
                    break

            if len(rectangle_indices) == 4:
                rectangle_lines = [raw_lines[i] for i in rectangle_indices]
                # Check if the rectangle is closed
                if (abs(rectangle_lines[0].x1 - rectangle_lines[-1].x2) < 1e-4 and 
                    abs(rectangle_lines[0].y1 - rectangle_lines[-1].y2) < 1e-4):
                    
                    # Collect all corner points
                    points = set((line.x1, line.y1) for line in rectangle_lines) | \
                             set((line.x2, line.y2) for line in rectangle_lines)
                    
                    if len(points) == 4:
                        # Check alignment with resolution
                        for point in points:
                            x, y = point
                            if not self._is_aligned_with_resolution(x) or \
                               not self._is_aligned_with_resolution(y):
                                alignment_errors.append((point, resolution))
                        
                        # Round points to resolution
                        rounded_points = {
                            (self._round_to_resolution(p[0]), self._round_to_resolution(p[1]))
                            for p in points
                        }
                        
                        # Sort points to identify corners
                        sorted_points = sorted(rounded_points, key=lambda p: (p[0], p[1]))
                        
                        # Apply margin to create the keep-out zone
                        bottom_left = (sorted_points[0][0] - module_margin, sorted_points[0][1] - module_margin)
                        top_left = (sorted_points[1][0] - module_margin, sorted_points[1][1] + module_margin)
                        bottom_right = (sorted_points[2][0] + module_margin, sorted_points[2][1] - module_margin)
                        top_right = (sorted_points[3][0] + module_margin, sorted_points[3][1] + module_margin)
                        
                        self.zone_rectangles.append((bottom_left, top_left, top_right, bottom_right))
                        used_indices.update(rectangle_indices)
        
        # Raise error if alignment issues were found
        if alignment_errors:
            error_msg = "The following zone coordinates are not aligned with the resolution grid:\n"
            for point, res in alignment_errors:
                error_msg += f"  Point: {point}, Resolution: {res}\n"
            raise ValueError(error_msg)
            
        print(f"🟢 Extracted {len(self.zone_rectangles)} keep-out zones")
        
        return self.zone_rectangles
    
    def get_zone_count(self) -> int:
        """
        Get the number of keep-out zones.
        
        Returns:
            int: Number of zones
        """
        return len(self.zone_rectangles)
    
    def get_data(self) -> List[Tuple]:
        """
        Get data representation of the zones.
        
        Returns:
            List[Tuple]: List of zone rectangles
        """
        return self.zone_rectangles
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'Zones':
        """
        Load zone data from a JSON file.
        
        Parameters:
            file_path: Path to the JSON file
            
        Returns:
            Zones: A new Zones instance with the loaded data
        """
        instance = cls()
        with open(file_path, 'r') as f:
            instance.zone_rectangles = json.load(f)
        return instance
    
    def add_zone(self, zone_rectangle: Tuple[Tuple[float, float], Tuple[float, float], 
                                           Tuple[float, float], Tuple[float, float]]) -> None:
        """
        Add a new keep-out zone rectangle.
        
        Parameters:
            zone_rectangle: Tuple of four corner points 
                           (bottom_left, top_left, top_right, bottom_right)
        """
        # Ensure all coordinates are aligned with resolution
        for point in zone_rectangle:
            x, y = point
            if not self._is_aligned_with_resolution(x) or not self._is_aligned_with_resolution(y):
                raise ValueError(f"Zone coordinate {point} is not aligned with resolution {self.resolution}")
                
        self.zone_rectangles.append(zone_rectangle)
    
    def remove_zone(self, zone_rectangle: Tuple) -> bool:
        """
        Remove a keep-out zone rectangle.
        
        Parameters:
            zone_rectangle: The rectangle to remove
            
        Returns:
            bool: True if the zone was removed, False otherwise
        """
        try:
            self.zone_rectangles.remove(zone_rectangle)
            return True
        except ValueError:
            return False
    
    def is_point_in_a_zone(self, point: Tuple[float, float]) -> bool:
        """
        Check if a point is within any keep-out zone.
        
        Parameters:
            point: The (x, y) coordinate to check
            
        Returns:
            bool: True if the point is in a keep-out zone, False otherwise
        """
        x, y = point
        
        for zone in self.zone_rectangles:
            bottom_left, top_left, top_right, bottom_right = zone
            
            # Check if point is within rectangle
            if (bottom_left[0] <= x <= bottom_right[0] and
                bottom_left[1] <= y <= top_left[1]):
                return True
                
        return False
    
    def plot_extracted_zones(self, output_file: str) -> None:
        """
        Plot the keep-out zones on a Gerber file.
        
        Parameters:
            output_file: The path to save the Gerber file
        """
        plot_zones(self.zone_rectangles, output_file)
