from typing import Dict, List, Tuple, Optional, Any
from typing import TypedDict

from loader import Loader

class Module:
    def __init__(self, name: str, position: Tuple[int, int], rotation: int):
        self.name = name
        self.position = position
        self.rotation = rotation
    
class Layer:
    def __init__(self, name: str):
        self.name = name
        self.nets: List[str] = []

    def add_net(self, net: str) -> None:
        if net not in self.nets:
            self.nets.append(net)

class Stack:
    def __init__(self, dimensions: Tuple[int, int], resolution: float):
        self.layers: Dict[str, Layer] = {}
        self.resolution = resolution
        self._net_to_layer: Dict[str, str] = {}

    def add_layer(self, name: str, z_index: int, is_ground_plane: bool = False) -> None:
        layer = Layer(name=name, z_index=z_index, is_ground_plane=is_ground_plane)
        layer.initialize_matrix(self.dimensions)
        self.layers[name] = layer

class Metadata(TypedDict):
    vendor: str
    application: str
    version: str

class Board():
    def __init__(self, loader: Loader):
        self.loader: Loader = loader
        self.name: str = loader.board_name
        self.dimensions: Tuple[int, int] = loader.board_dimensions
        self.resolution: float = loader.resolution
        self.modules: List[Module] = []
        self.generation_software: Metadata = loader.generation_software
        self._create_board()
        
    def _create_board(self) -> None:
        """Load information about the board from the loader"""
        self._add_modules_from_loader()
        

    def _add_modules_from_loader(self) -> None:
        """
        Load modules from data dictionary structure.
        
        Expected format:
        [
            {
              "name": "module_name",
              "position": { "x": 0, "y": 0 },
              "rotation": 0
            },
            ...
        ]
        """
        for module_data in self.loader.modules_data:
            # Extract the module properties
            name = module_data['name']
            position = (module_data['position']['x'], module_data['position']['y'])
            rotation = module_data.get('rotation', 0)
            
            # Create and add the module
            module = Module(name=name, position=position, rotation=rotation)
            self.add_module(module)
            
    def _add_layers(): 
        pass
    
    def add_module(self, module: Module) -> None:
        """Add a module to the board"""
        self.modules.append(module)
            
    def get_module_by_name(self, name: str) -> Optional[Module]:
        """Get a module by its name."""
        for module in self.modules:
            if module.name == name:
                return module
        return None
    
    def __repr__(self) -> str:
        return f"PCB(name={self.name}, size={self.size}, modules_count={len(self.modules)})"