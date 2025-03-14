from typing import Dict, List, Tuple, Optional, Any, TypedDict, Set
from pathlib import Path
import math

from loader import Loader
from gerbersockets import Sockets, Zones
from module import Module
from layer import Layer

from process import merge_stacks

class Metadata(TypedDict):
    vendor: str
    application: str
    version: str
    
class Board:
    def __init__(self, loader: Loader, sockets: Optional[Sockets] = None, zones: Optional[Zones] = None):
        """
        Initialize a PCB board with data from loader and optional sockets and zones
        
        Parameters:
            loader: The PCB data loader with configuration settings
            sockets: Optional Sockets object with socket locations
            zones: Optional Zones object with keep-out zones
        """
        self.loader: Loader = loader
        self.name: str = loader.name
        self.dimensions: Tuple[float, float] = (loader.size['x'], loader.size['y'])
        self.width: int = loader.size['x']
        self.height: int = loader.size['y']
        self.resolution: float = loader.resolution
        self.origin: Dict[str, float] = loader.origin
        self.modules: List[Module] = []
        self.layers: Dict[str, Layer] = {}
        self.generation_software: Metadata = loader.generation_software
        self.constrained_routing: bool = loader.constrained_routing
        self.allow_diagonal_traces: bool = loader.allow_diagonal_traces
        self.algorithm: str = loader.algorithm
        self.include_GerberSockets: bool = False
        
        # Add sockets and zones if provided
        self._sockets: Optional[Sockets] = sockets
        self._zones: Optional[Zones] = zones
        
        # Track warnings
        self.warnings: List[str] = []
        
        # Initialize the board
        self._create_board()
    
    def _create_board(self) -> None:
        """Load information about the board from the loader"""
        self._add_modules_from_loader()
        self._add_layers_from_loader()
        self._check_module_positions()
        self._ensure_directories()
        
    def _add_modules_from_loader(self) -> None:
        """
        Load modules from loader. Works with both raw module data and Module objects.
        """
        modules = self.loader.modules
        
        for module in modules:
            self.add_module(module)
            
    def _add_layers_from_loader(self) -> None:
        """
        Load layers from loader data structure
        """
        for layer_name, layer_data in self.loader.layer_map.items():
            # Create the layer
            layer = Layer(name=layer_name, attributes=layer_data.get('attributes'))
            
            # Add nets to the layer
            for net in layer_data.get('nets', []):
                layer.add_net(net)
                
            # Add the layer to the board
            self.layers[layer_name] = layer
    
    def _check_module_positions(self) -> None:
        """
        Check if all modules and their keep-out zones are within the board boundaries
        and that they don't overlap with each other.
        Records warnings for any modules that extend beyond the board perimeter
        or overlap with other modules.
        """
        if not self._zones:
            # If no zones are available, fall back to checking just the module positions
            for module in self.modules:
                x, y = module.position.as_tuple()
                origin_x, origin_y = self.origin['x'], self.origin['y']
                width, height = self.dimensions
                
                if not (origin_x <= x <= origin_x + width and origin_y <= y <= origin_y + height):
                    warning = f"Module '{module.name}' at position {module.position.as_tuple()} is outside board boundaries: origin={self.origin}, dimensions={self.dimensions}"
                    self.warnings.append(warning)
                    print(f"⚠️ {warning}")
            return
            
        # Get module margin from loader
        try:
            module_margin = self.loader.module_margin
            # print(f"Using module margin: {module_margin}mm")
        except AttributeError:
            module_margin = 0
            print("Module margin not specified in loader, using 0mm")
        
        # Map module names to their associated keep-out zones
        module_zones = {}
        all_zones = self._zones.get_zone_rectangles()
        
        # Calculate center points for each zone to associate them with the closest module
        for i, zone in enumerate(all_zones):
            bottom_left, top_left, top_right, bottom_right = zone
            
            # Find center of the zone
            zone_center_x = (bottom_left[0] + top_right[0]) / 2
            zone_center_y = (bottom_left[1] + top_right[1]) / 2
            
            # Find which module is closest to this zone
            closest_module = None
            min_distance = float('inf')
            
            for module in self.modules:
                mx, my = module.position.as_tuple()
                distance = math.sqrt((mx - zone_center_x)**2 + (my - zone_center_y)**2)
                
                if distance < min_distance:
                    min_distance = distance
                    closest_module = module
            
            if closest_module:
                if closest_module.name not in module_zones:
                    module_zones[closest_module.name] = []
                module_zones[closest_module.name].append((i, zone))
        
        # Check if any zones extend beyond the board boundaries
        origin_x, origin_y = self.origin['x'], self.origin['y']
        width, height = self.dimensions
        board_min_x, board_min_y = origin_x - width/2, origin_y - height/2
        board_max_x, board_max_y = origin_x + width/2, origin_y + height/2
        
        for module_name, zones in module_zones.items():
            for zone_index, zone in zones:
                bottom_left, top_left, top_right, bottom_right = zone
                
                # Find min/max coordinates of the zone
                zone_min_x = min(bottom_left[0], top_left[0], top_right[0], bottom_right[0])
                zone_min_y = min(bottom_left[1], top_left[1], top_right[1], bottom_right[1])
                zone_max_x = max(bottom_left[0], top_left[0], top_right[0], bottom_right[0])
                zone_max_y = max(bottom_left[1], top_left[1], top_right[1], bottom_right[1])
                
                # Add module margin to the zone for boundary checking
                zone_min_x -= module_margin
                zone_min_y -= module_margin
                zone_max_x += module_margin
                zone_max_y += module_margin
                
                # Check if zone extends beyond board boundaries
                if zone_min_x < board_min_x or zone_max_x > board_max_x or zone_min_y < board_min_y or zone_max_y > board_max_y:
                    warning = f"Module '{module_name}' has a keep-out zone that extends beyond board boundaries. Zone coordinates (with margin): {zone_min_x, zone_min_y, zone_max_x, zone_max_y}, Board boundaries: {board_min_x, board_min_y, board_max_x, board_max_y}"
                    self.warnings.append(warning)
                    print(f"⚠️ {warning}")
        
        # Check for overlapping zones between different modules
        checked_pairs = set()
        
        for module1_name, zones1 in module_zones.items():
            for module2_name, zones2 in module_zones.items():
                if module1_name == module2_name:
                    continue
                    
                # Create a unique pair identifier
                pair_id = tuple(sorted([module1_name, module2_name]))
                if pair_id in checked_pairs:
                    continue
                checked_pairs.add(pair_id)
                
                # Check each zone from module1 against each zone from module2
                for _, zone1 in zones1:
                    for _, zone2 in zones2:
                        if self._do_zones_overlap(zone1, zone2, module_margin):
                            warning = f"Module '{module1_name}' and '{module2_name}' have overlapping keep-out zones (including margin of {module_margin}mm)"
                            self.warnings.append(warning)
                            print(f"⚠️ {warning}")
                            # Skip checking other zones for this module pair
                            break
                    else:
                        continue
                    break
                
    def _do_zones_overlap(self, zone1, zone2, margin=0):
        """
        Check if two zones overlap, considering a margin.
        
        Parameters:
            zone1: First zone as (bottom_left, top_left, top_right, bottom_right)
            zone2: Second zone as (bottom_left, top_left, top_right, bottom_right)
            margin: Additional margin to add around each zone in mm
        
        Returns:
            bool: True if zones overlap, False otherwise
        """
        # Extract points from zones
        bl1, tl1, tr1, br1 = zone1
        bl2, tl2, tr2, br2 = zone2
        
        # Find min/max coordinates for each zone
        zone1_min_x = min(bl1[0], tl1[0], tr1[0], br1[0]) - margin
        zone1_min_y = min(bl1[1], tl1[1], tr1[1], br1[1]) - margin
        zone1_max_x = max(bl1[0], tl1[0], tr1[0], br1[0]) + margin
        zone1_max_y = max(bl1[1], tl1[1], tr1[1], br1[1]) + margin
        
        zone2_min_x = min(bl2[0], tl2[0], tr2[0], br2[0]) - margin
        zone2_min_y = min(bl2[1], tl2[1], tr2[1], br2[1]) - margin
        zone2_max_x = max(bl2[0], tl2[0], tr2[0], br2[0]) + margin
        zone2_max_y = max(bl2[1], tl2[1], tr2[1], br2[1]) + margin
        
        # Check for non-overlap conditions
        if zone1_max_x < zone2_min_x or zone1_min_x > zone2_max_x:
            return False  # No horizontal overlap
        
        if zone1_max_y < zone2_min_y or zone1_min_y > zone2_max_y:
            return False  # No vertical overlap
        
        # If we get here, the zones overlap
        return True
    
    def _ensure_directories(self) -> None:
        """Ensure that the output and generated directories exist"""
        output_dir = Path("output")
        generated_dir = Path("generated")
        
        if not output_dir.exists():
            output_dir.mkdir()
        
        if not generated_dir.exists():
            generated_dir.mkdir()
            
    # def _create_grids(self) -> None:
    #     """Create a pathfinding grid for each layer"""
    #     if not self._zones:
    #         raise ValueError("Cannot create grids without zones")
            
    #     for layer in self.layers.values():
    #         layer.create_grid(self._zones, self.dimensions, self.resolution)
    
    
    def _merge_stacks(self) -> None:
        """Merge all generated Gerber files with Gerber files from the modules"""
        merge_stacks(self.modules, self.name)
        
    
    def generate(self) -> None:
        """Generate the PCB layout"""
        # TODO: all the steps to generate the routing, consolidation, merging, etc. of the PCB
        pass
        
    def add_module(self, module: Module) -> None:
        """Add a module to the board"""
        self.modules.append(module)
            
    def get_modules_by_name(self, name: str) -> List[Module]:
        """Get all modules by a specific name"""
        return [module for module in self.modules if module.name == name]
    
    def get_nets(self) -> Set[str]:
        """Get all nets used on the board"""
        nets = set()
        # Get nets from layers
        for layer in self.layers.values():
            nets.update(layer.nets)
        
        # Add nets from sockets if available
        if self._sockets:
            nets.update(self._sockets.get_nets())
            
        return nets
    
    def get_layer_for_net(self, net: str) -> Optional[Layer]:
        """Get the layer that contains a specific net"""
        for layer in self.layers.values():
            if net in layer.nets:
                return layer
        return None
    
    def get_layers(self) -> List[Layer]:
        """Get all layers on the board"""
        return list(self.layers.values())
        
    def get_socket_locations_for_net(self, net: str) -> List[Tuple[float, float]]:
        """Get all socket locations for a specific net"""
        if not self._sockets:
            return []
            
        return self._sockets.get_socket_locations(net).get(net, [])
    
    def is_point_in_keep_out_zone(self, point: Tuple[float, float]) -> bool:
        """Check if a point is within any keep-out zone"""
        if not self._zones:
            return False
            
        return self._zones.is_point_in_zone(point)
    
    def get_fabrication_options(self) -> Dict[str, Any]:
        """Get the fabrication options from the loader"""
        return self.loader.fabrication_options
    
    @property
    def zones(self) -> Optional[Zones]:
        """Get the keep-out zones for the board"""
        return self._zones
    
    @property
    def sockets(self) -> Optional[Sockets]:
        """Get the sockets for the board"""
        return self._sockets
    
    def __repr__(self) -> str:
        socket_count = self._sockets.get_socket_count() if self._sockets else 0
        zone_count = self._zones.get_zone_count() if self._zones else 0
        return f"Board(name={self.name}, dimensions={self.dimensions}, layers={len(self.layers)}, modules={len(self.modules)}, sockets={socket_count}, zones={zone_count})"

