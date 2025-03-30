from typing import Dict, List, Tuple, Optional
from pathlib import Path

from loader import Loader
from gerbersockets import Sockets, Zones
from module import Module
from layer import Layer
from objects import Point
    
class Board:
    def __init__(self, loader: Loader, sockets: Optional[Sockets] = None, zones: Optional[Zones] = None):
        """
        Initialize a PCB board with data from loader and optional sockets and zones
        
        Parameters:
            loader (Loader): The PCB data loader with configuration settings
            sockets (Sockets): Optional Sockets object with socket locations
            zones (Zones): Optional Zones object with keep-out zones
        """
        self.loader: Loader = loader
        self.name: str = loader.name
        self.generation_software: Dict[str, str] = loader.generation_software
        self.size: Dict[str, float] = loader.size
        self.width: float = self.size['x']
        self.height: float = self.size['y']
        self.dimensions: Tuple[float, float] = (self.width, self.height)
        self.origin: Dict[str, float] = loader.origin
        self.origin_x: float = self.origin['x']
        self.origin_y: float = self.origin['y']
        self.resolution: float = loader.resolution
        self.allow_diagonal_traces: bool = loader.allow_diagonal_traces
        self.allow_overlap: bool = loader.allow_overlap
        self.algorithm: str = loader.algorithm
        self.module_margin: float = loader.module_margin
        
        # Store the modules and layers
        self.modules: List[Module] = []
        self.layers: List[Layer] = []
        
        # Add sockets and zones if provided
        self.sockets: Optional[Sockets] = sockets
        self.zones: Optional[Zones] = zones
        self.drill_holes: List[Point] = []
        
        # Fabrication parameters coming from routing
        self.total_buses_width: float = 0.0
        
        # Track warnings
        self.position_warnings: List[str] = []
        
        # Store the number of connected sockets
        self.connected_sockets_count = 0
    
        # Initialize the board
        self._ensure_directories()
        self._add_modules_from_loader()
        self._add_layers_from_loader()
        
        # If sockets are are available, assign nets to layers
        if self.sockets:
            self._assign_nets_to_layers()
        
        # If zones have been provided, check their positions
        if self.zones:
            self._assign_zones_to_modules()
            self._add_corner_zones() # TODO: will cause issues when placing corner holes
            self._validate_zones_and_modules()

    def _ensure_directories(self) -> None:
        """Ensure that the output and generated directories exist"""
        output_dir = Path("output")
        generated_dir = Path("generated")
        
        if not output_dir.exists():
            output_dir.mkdir()
        
        if not generated_dir.exists():
            generated_dir.mkdir()
        
    def _add_modules_from_loader(self) -> None:
        """
        Load modules from loader JSON and create Module objects.
        """
        # Create Module objects from modules list from JSON
        for module_data in self.loader.modules:
            # Get module properties
            name = module_data.get('name')
            position = (module_data['position']['x'], module_data['position']['y'])
            rotation = module_data.get('rotation')
                    
            # Create Module object
            module = Module(name=name, position=position, rotation=rotation)
            self.modules.append(module)
            
    def _add_layers_from_loader(self) -> None:
        """
        Load layers from loader data structure.
        Creates layer objects without adding any nets at this stage.
        """
        # Create Layer objects from layer map from JSON
        for layer_name, layer_data in self.loader.layer_map.items():
            # Create the layer
            layer = Layer(
                name=layer_name, 
                fill=layer_data.get('fill'), 
                attributes=layer_data.get('attributes')
            )
            self.layers.append(layer)
    
    def _assign_nets_to_layers(self) -> None:
        """ Assign nets to layers based on the layer map and socket data """
        
        # First, add any explicit nets from the layer map
        for layer_name, layer_data in self.loader.layer_map.items():
            nets = layer_data.get('nets')
            if nets:
                # Get the layer by name
                layer = self.get_layer(layer_name)
                # Add nets to the layer
                for net in layer_data.get('nets', []):
                    layer.add_net(net)
        
        # Second, assign the remaining nets from the extracted sockets
        if self.sockets:
                socket_nets = set(self.sockets.get_nets())
                
                # Get all nets that are already assigned to layers
                assigned_nets = set()
                for layer in self.layers:
                    assigned_nets.update(layer.nets)
                
                # Find unassigned nets
                unassigned_nets = socket_nets - assigned_nets
                
                # Assign unassigned nets to the top layer "F_Cu.gtl"
                if unassigned_nets:
                    top_layer = self.get_layer("F_Cu.gtl")
                    if top_layer:
                        for net in unassigned_nets:
                            top_layer.add_net(net)
                    else:
                        print(f"🔴 Warning: Unable to find top layer 'F_Cu.gtl' for unassigned nets: {unassigned_nets}")
    
    def _assign_zones_to_modules(self) -> None:
        """
        Assigns zones to modules by matching zone centers to module positions.
        """
        if not self.zones:
            return
        
        all_zones = self.zones.get_data()
        
        for zone in all_zones:
            # Calculate zone center (from bottom_left and top_right corners)
            bottom_left, _, top_right, _ = zone
            center_x = (bottom_left[0] + top_right[0]) / 2
            center_y = (bottom_left[1] + top_right[1]) / 2
            
            # Find module at this position
            for module in self.modules:
                if module.position.x == center_x and module.position.y == center_y:
                    module.set_zone(*zone)
                    print(f"🟢 Assigned zone to module '{module.name}' at position ({center_x}, {center_y})")
                    break 
                
                
    def _validate_zones_and_modules(self) -> None:
        """
        Validates the positions of modules and zones by:
        1. Checking if any module zones overlap with each other
        2. Checking if any module zone extends beyond the board size
        3. Checking if any zones in self.zones overlap with other zones
        
        Adds warnings to self.position_warnings for any issues found.
        """
        if not self.zones:
            print("🟠 No zones to validate")
            return
        
        # 1. Check if any module zones overlap
        print("🟢 Validating module zone overlaps...")
        modules_with_zones = [module for module in self.modules if hasattr(module, 'zone') and module.zone]
        
        for i, module1 in enumerate(modules_with_zones):
            for j, module2 in enumerate(modules_with_zones):
                # Skip comparing the same module or modules already compared
                if i >= j:
                    continue
                
                if self._do_zones_overlap(module1.zone, module2.zone):
                    warning = f"🔴 WARNING: Zone overlap detected between modules '{module1.name}' and '{module2.name}'"
                    print(warning)
                    self.position_warnings.append(warning)
        
        # 2. Check if any module zone extends beyond the board size
        print("🟢 Validating module zones within board boundaries...")
        # Calculate the board boundaries
        xmin = self.origin_x - self.width / 2
        xmax = self.origin_x + self.width / 2
        ymin = self.origin_y - self.height / 2
        ymax = self.origin_y + self.height / 2
        
        for module in modules_with_zones:
            # Extract corner points from module's zone
            bl, tl, tr, br = module.zone
            
            # Check if any corner is outside the board boundaries
            if (bl[0] < xmin or bl[1] < ymin or 
                tl[0] < xmin or tl[1] > ymax or 
                tr[0] > xmax or tr[1] > ymax or 
                br[0] > xmax or br[1] < ymin):
                
                warning = f"🔴 WARNING: Module '{module.name}' zone extends beyond board boundaries"
                print(warning)
                self.position_warnings.append(warning)
        
        # 3. Check if any module zones overlap with remaining zones in self.zones
        print("🟢 Validating module zones against other zones...")
        all_zones = self.zones.get_data()
        
        for module in modules_with_zones:
            module_zone = module.zone
            
            for zone in all_zones:
                # Skip if this is the module's own zone
                # Calculate zone center for comparison
                bl_z, _, tr_z, _ = zone
                center_x = (bl_z[0] + tr_z[0]) / 2
                center_y = (bl_z[1] + tr_z[1]) / 2
                
                # Skip if this is the module's own zone
                if module.position.x == center_x and module.position.y == center_y:
                    continue
                    
                if self._do_zones_overlap(module_zone, zone):
                    warning = f"🔴 WARNING: Module '{module.name}' zone overlaps with a zone at position {(zone[0], zone[2])}"
                    print(warning)
                    self.position_warnings.append(warning)
        
        if not self.position_warnings:
            print("🟢 All zones and modules validated successfully!")
        else:
            print(f"🔴 Found {len(self.position_warnings)} validation issues")
        
               
    def _do_zones_overlap(self, zone1: List[Tuple[float, float]], zone2: List[Tuple[float, float]]) -> bool: 
        """
        Check if two zones overlap, considering a module margin.
        
        Parameters:
            zone1: First zone as (bottom_left, top_left, top_right, bottom_right)
            zone2: Second zone as (bottom_left, top_left, top_right, bottom_right)
        
        Returns:
            bool: True if zones overlap, False otherwise
        """
        # Extract corner points
        bl1, _, tr1, _ = zone1
        bl2, _, tr2, _ = zone2
        
        # Add margin to the bounding boxes
        margin = self.module_margin
        
        # Create bounding boxes with margin [min_x, min_y, max_x, max_y]
        box1 = [bl1[0] - margin, bl1[1] - margin, tr1[0] + margin, tr1[1] + margin]
        box2 = [bl2[0] - margin, bl2[1] - margin, tr2[0] + margin, tr2[1] + margin]
        
        # Check for non-overlap using axis-aligned bounding box test
        return not (box1[2] < box2[0] or  # box1 is left of box2
                box1[0] > box2[2] or   # box1 is right of box2
                box1[3] < box2[1] or   # box1 is below box2
                box1[1] > box2[3])     # box1 is above box2

    def _add_corner_zones(self) -> None:
        """
        Apply keep-out zones to each corner of the board with dimensions based on corner radius.
        This prevents routing traces through the rounded corners of the board.
        
        Returns:
            None
        """        
        # Get corner radius from board fabrication options
        corner_radius = self.loader.rounded_corner_radius
        
        # If corner radius is zero or not set, no need to add corner keep-out zones
        if corner_radius <= 0:
            print("🟠 NO ROUNDED CORNERS!? How dare you... skipping corner keep-out zones")
            return
        
        # Calculate the board boundaries
        xmin = self.origin_x - self.width / 2
        xmax = self.origin_x + self.width / 2
        ymin = self.origin_y - self.height / 2
        ymax = self.origin_y + self.height / 2
        
        # Create square keep-out zones for each corner, with size equal to corner radius
        # Bottom-left corner
        bottom_left_zone = (
            (xmin, ymin),                                  # bottom-left
            (xmin, ymin + corner_radius),                  # top-left
            (xmin + corner_radius, ymin + corner_radius),  # top-right
            (xmin + corner_radius, ymin)                   # bottom-right
        )
        
        # Bottom-right corner
        bottom_right_zone = (
            (xmax - corner_radius, ymin),                  # bottom-left
            (xmax - corner_radius, ymin + corner_radius),  # top-left
            (xmax, ymin + corner_radius),                  # top-right
            (xmax, ymin)                                   # bottom-right
        )
        
        # Top-left corner
        top_left_zone = (
            (xmin, ymax - corner_radius),                  # bottom-left
            (xmin, ymax),                                  # top-left
            (xmin + corner_radius, ymax),                  # top-right
            (xmin + corner_radius, ymax - corner_radius)   # bottom-right
        )
        
        # Top-right corner
        top_right_zone = (
            (xmax - corner_radius, ymax - corner_radius),  # bottom-left
            (xmax - corner_radius, ymax),                  # top-left
            (xmax, ymax),                                  # top-right
            (xmax, ymax - corner_radius)                   # bottom-right
        )
        
        # Add these zones to the board's zones
        corner_zones = [bottom_left_zone, bottom_right_zone, top_left_zone, top_right_zone]
        
        print(f"🟢 Adding {len(corner_zones)} corner keep-out zones with size {corner_radius}mm")
        
        # Add zones to the grid
        for zone in corner_zones:
            self.zones.add_zone(zone)

            
    def generate(self) -> None:
        """Does nothing for now"""
        if not self.sockets:
            print("🔴 No sockets found, cannot generate routing")
            return
        
        if not self.zones:
            print("🔴 No keep-out zones found, cannot generate routing")
            return
        
        if not self.modules:
            print("🔴 No modules found, cannot generate routing")
            return
        
        if not self.layers:
            print("🔴 No layers found, cannot generate routing")
            return

        pass
    
    def add_drill_hole(self, position: Point) -> None:
        """Add a drill hole to the board
        
        Parameters:
            position (Point): coordinates of the drill hole
        
        Returns:
            None"""
        self.drill_holes.append(position)
    
    def get_nets(self) -> List[str]:
        """Get all nets used on the board
        
        Returns:
            List[str]: A list of all nets used on the board"""
        if not self.sockets:
            return None
                    
        return self.sockets.get_nets()
        
    def get_layer(self, layer_name: str) -> Optional[Layer]:
        """Get the layer by its name
        
        Parameters:
            layer_name (str): The name of the layer to search for
        
        Returns:
            Layer: The layer object if found, or None if not found"""
        for layer in self.layers:
            if layer_name == layer.name:
                return layer
        return None
    
    def get_layer_for_net(self, net: str) -> Optional[Layer]:
        """Get the layer that contains a specific net
        
        Parameters:
            net (str): The net name to search for
        
        Returns:
            Layer: The layer containing the net, or None if not found"""
        for layer in self.layers:
            if net in layer.nets:
                return layer
        return None
    
    def add_sockets(self, sockets: Sockets) -> None:
        """Add sockets to the board
        
        Parameters:
            sockets (Sockets): The Sockets object containing socket locations
            
        Returns:
            None
        """
        self.sockets = sockets
        self._assign_nets_to_layers()
    
    def add_zones(self, zones: Zones) -> None:
        """Add keep-out zones to the board
        
        Parameters:
            zones (Zones): The Zones object containing keep-out zones
            
        Returns:
            None
        """
        self.zones = zones
        self._assign_zones_to_modules()
        self._add_corner_zones() # TODO: will cause issues when placing corner holes
        self._validate_zones_and_modules()
    
    def __repr__(self) -> str:
        socket_count = self.sockets.get_socket_count() if self.sockets else 0
        zone_count = self.zones.get_zone_count() if self.zones else 0
        return f"Board(name={self.name}, dimensions={self.dimensions}, layers={len(self.layers)}, modules={len(self.modules)}, sockets={socket_count}, zones={zone_count})"

