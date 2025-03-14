import json
from typing import Dict, Any, Union, List, Tuple
from pathlib import Path

from module import Module

class Loader:
    """
    Handles loading and validating PCB data from JSON files.
    Provides a clean interface for accessing structured PCB data.
    """
    
    def __init__(self, file_path: Union[str, Path]):
        """Initialize with path to JSON file"""
        self.file_path = Path(file_path)
        self.data: Dict[str, Any] = {}
        self._module_objects = None  # Cache for module objects
        self._load()
        
    def _load(self) -> None:
        """Load and validate the JSON data"""
        try:
            with open(self.file_path, 'r') as file:
                self.data = json.load(file)
            # self._validate()
        except FileNotFoundError:
            raise FileNotFoundError(f"File {self.file_path} not found.")
        except json.JSONDecodeError:
            raise ValueError(f"File {self.file_path} is not a valid JSON.")
        
    @property
    def board(self) -> List[Dict[str, Any]]:
        """Get board information"""
        return self.data['board']
    
    @property
    def name(self) -> str:
        """Get the board name"""
        return self.data['board']['name']
    
    @property
    def generation_software(self) -> Dict[str, str]:
        """Get the generation software info"""
        return self.data['board']['generation_software']
    
    @property
    def size(self) -> Dict[str, int]:
        """Get the board size"""
        return self.data['board']['size']
    
    @property
    def dimensions(self) -> Tuple[int, int]:
        """Get board dimensions as a tuple (width, height)"""
        return (self.board_size['x'], self.board_size['y'])
    
    @property
    def origin(self) -> Dict[str, int]:
        """Get the board origin"""
        return self.data['board']['origin']
    
    @property
    def debug(self) -> bool:
        """Get the debug flag"""
        return bool(self.data['board'].get('debug', False))
    
    # ----------------------------------------------------------
    
    @property
    def configuration(self) -> Dict[str, Any]:
        """Get the full configuration object"""
        return self.data['configuration']
    
    @property
    def algorithm(self) -> str:
        """Get the routing algorithm"""
        return self.data['configuration']['routing_options']['algorithm']
    
    @property
    def allow_diagonal_traces(self) -> bool:
        """Get whether diagonal traces are allowed"""
        return bool(self.data['configuration']['routing_options'].get('allow_diagonal_traces', False))
    
    @property
    def resolution(self) -> float:
        """Get the resolution setting"""
        return self.data['configuration']['routing_options']['resolution']
    
    @property
    def constrained_routing(self) -> bool:
        """Get whether constrained routing is enabled"""
        return bool(self.data['configuration']['routing_options'].get('constrained_routing', False))
    
    @property
    def connectors(self) -> Dict[str, bool]:
        """Get connector settings"""
        return self.data['configuration']['fabrication_options']['connectors']
    
    @property
    def gerbersockets_layer_name(self) -> str:
        """Get the GerberSockets layer name"""
        return self.data['configuration']['gerbersockets_options']['layer_name']

    @property
    def keep_out_zone_aperture_diameter(self) -> Dict[str, float]:
        """Get tool diameter used to trace out the keep-out zones"""
        return self.data['configuration']['gerbersockets_options']['keep_out_zone_aperture_diameter']

    @property
    def net_diameter_map(self) -> Dict[str, float]:
        """Get the socket diameter mapping"""
        return self.data['configuration']['gerbersockets_options']['net_diameter_map']
    
    @property
    def legacy_sockets(self) -> bool:
        """Get whether legacy sockets are enabled"""
        return bool(self.data['configuration']['gerbersockets_options'].get('legacy_sockets', False))
    
    @property
    def layer_map(self) -> Dict[str, Dict[str, Any]]:
        """Get the layer mapping configuration"""
        return self.data['configuration']['layer_map']
    
    @property
    def fabrication_options(self) -> Dict[str, Any]:
        """Get fabrication options"""
        return self.data['configuration']['fabrication_options']
    
    @property
    def module_margin(self) -> Dict[str, float]:
        """Get margin around the keep-out zones"""
        return self.data['configuration']['fabrication_options']['module_margin']
    
    # ----------------------------------------------------------

    @property
    def modules(self) -> List[Module]:
        """
        Get modules as a list of Module objects
        
        Returns:
            List[Module]: List of Module objects with data from the JSON file
        """
        # Use cached module objects if available
        if self._module_objects is not None:
            return self._module_objects
        
        # Create Module objects from raw data
        self._module_objects = []
        for module_data in self.data['modules']:
            name = module_data['name']
            # Extract position as a tuple
            position = (module_data['position']['x'], module_data['position']['y'])
            # Get rotation (default to 0 if not present)
            rotation = module_data.get('rotation', 0)
            
            # Create Module object
            module = Module(name=name, position=position, rotation=rotation)
            self._module_objects.append(module)
            
        return self._module_objects
    
    @property
    def module_count(self) -> int:
        """Get the count of modules"""
        return len(self.data['modules'])
