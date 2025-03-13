from typing import Dict, List, Tuple, Optional, Any, TypedDict, Set, Union
from pathlib import Path

from loader import Loader
from gerbersockets import Sockets, Zones

from constrained_route import create_grid

class Module:
    def __init__(self, name: str, position: Tuple[float, float], rotation: float):
        self.name = name
        self.position = position
        self.rotation = rotation
    
    def __repr__(self) -> str:
        return f"Module(name={self.name}, position={self.position}, rotation={self.rotation})"
    
class Layer:
    def __init__(self, name: str, attributes: str = None):
        self.name = name
        self.attributes = attributes
        self.nets: List[str] = []

    def add_net(self, net: str) -> None:
        if net not in self.nets:
            self.nets.append(net)
            
    def __repr__(self) -> str:
        return f"Layer(name={self.name}, nets={self.nets})"

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
        self.dimensions: Tuple[int, int] = loader.board
        self.resolution: float = loader.resolution
        self.origin: Dict[str, float] = loader.origin
        self.modules: List[Module] = []
        self.layers: Dict[str, Layer] = {}
        self.generation_software: Metadata = loader.generation_software
        self.constrained_routing: bool = loader.constrained_routing
        self.allow_diagonal_traces: bool = loader.allow_diagonal_traces
        self.algorithm: str = loader.algorithm
        
        # Add sockets and zones if provided
        self.sockets: Optional[Sockets] = sockets
        self.zones: Optional[Zones] = zones
        
        # Initialize the board
        self._create_board()
        
    def _create_board(self) -> None:
        """Load information about the board from the loader"""
        self._add_modules_from_loader()
        self._add_layers_from_loader()
        
    def _add_modules_from_loader(self) -> None:
        """
        Load modules from loader data structure
        """
        for module_data in self.loader.modules:
            # Extract the module properties
            name = module_data['name']
            position = (module_data['position']['x'], module_data['position']['y'])
            rotation = module_data.get('rotation', 0)
            
            # Create and add the module
            module = Module(name=name, position=position, rotation=rotation)
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
    
    def _create_grid(self) -> None:
        """Create a grid for each layer"""
        pass
        
    def _route(self) -> None:
        """Route the board and generate segments"""
        pass
    
    def _generate_gerbers(self, output_dir: Path) -> None:
        """Save the board to a directory"""
        pass
    
    def _merge_stacks(self) -> None:
        """Merge the Gerber stacks"""
        pass
    
    def _generate_fabrication_files(self, output_dir: Path) -> None:
        """Generate fabrication BOM and P&P files for the board"""
        pass
    
    def _archive_project(self, output_dir: Path) -> None:
        """Compress the board files into a single archive"""
        pass
    
    def generate(self) -> None:
        """Do everything to generate the board"""
        pass
    
    def add_module(self, module: Module) -> None:
        """Add a module to the board"""
        self.modules.append(module)
            
    def get_module_by_name(self, name: str) -> Optional[Module]:
        """Get a module by its name"""
        for module in self.modules:
            if module.name == name:
                return module
        return None
    
    def get_nets(self) -> Set[str]:
        """Get all nets used on the board"""
        nets = set()
        # Get nets from layers
        for layer in self.layers.values():
            nets.update(layer.nets)
        
        # Add nets from sockets if available
        if self.sockets:
            nets.update(self.sockets.get_nets())
            
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
        if not self.sockets:
            return []
            
        return self.sockets.get_socket_locations(net).get(net, [])
    
    def is_point_in_keep_out_zone(self, point: Tuple[float, float]) -> bool:
        """Check if a point is within any keep-out zone"""
        if not self.zones:
            return False
            
        return self.zones.is_point_in_zone(point)
    
    def get_fabrication_options(self) -> Dict[str, Any]:
        """Get the fabrication options from the loader"""
        return self.loader.fabrication_options
    
    def __repr__(self) -> str:
        socket_count = self.sockets.get_socket_count() if self.sockets else 0
        zone_count = self.zones.get_zone_count() if self.zones else 0
        return f"Board(name={self.name}, dimensions={self.dimensions}, modules={len(self.modules)}, sockets={socket_count}, zones={zone_count})"