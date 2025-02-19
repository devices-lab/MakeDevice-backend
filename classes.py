from typing import Dict, List, Tuple, Optional, Any
from typing import TypedDict

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
        self.dimensions = dimensions
        self.resolution = resolution
        self._net_to_layer: Dict[str, str] = {}

    def add_layer(self, name: str, z_index: int, is_ground_plane: bool = False) -> None:
        layer = Layer(name=name, z_index=z_index, is_ground_plane=is_ground_plane)
        layer.initialize_matrix(self.dimensions)
        self.layers[name] = layer

class BoardInfo(TypedDict):
    vendor: str
    application: str
    version: str

class Board():
    def __init__(self, name: str, size: Tuple[int, int], resolution: float):
        self.name = name
        self.size = size
        self.resolution = resolution
        self.modules = List[Module] = []
        self.board_info: BoardInfo = {}
        
    def add_module(self, module):
        self.modules.append(module)
        
    def load_modules_from_data(self, modules_data: List[Dict[str, Any]]) -> None:
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
        for module_data in modules_data:
            name = module_data['name']
            position = (module_data['position']['x'], module_data['position']['y'])
            rotation = module_data.get('rotation', 0)
            
            module = Module(name=name, position=position, rotation=rotation)
            self.add_module(module)
            
    def get_module_by_name(self, name: str) -> Optional[Module]:
        """Get a module by its name."""
        for module in self.modules:
            if module.name == name:
                return module
        return None
    
    def __repr__(self) -> str:
        return f"PCB(name={self.name}, size={self.size}, modules_count={len(self.modules)})"