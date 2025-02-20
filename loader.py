import json
from typing import Dict, Any, Union, List, Tuple
from pathlib import Path


class Loader:
    """
    Handles loading and validating PCB data from JSON files.
    Provides a clean interface for accessing structured PCB data.
    """
    
    def __init__(self, file_path: Union[str, Path]):
        """Initialize with path to JSON file"""
        self.file_path = Path(file_path)
        self.data: Dict[str, Any] = {}
        self._load()
        
    def _load(self) -> None:
        """Load and validate the JSON data"""
        try:
            with open(self.file_path, 'r') as file:
                self.data = json.load(file)
            self._validate()
        except FileNotFoundError:
            raise FileNotFoundError(f"File {self.file_path} not found.")
        except json.JSONDecodeError:
            raise ValueError(f"File {self.file_path} is not a valid JSON.")
        
    def _validate(self) -> None:
        """Validate the loaded JSON data structure"""
        required_keys = ['board_info', 'configuration', 'modules']
        for key in required_keys:
            if key not in self.data:
                raise ValueError(f"Missing required key '{key}' in JSON data")
                
        # Validate board_info
        required_board_info = ['name', 'size', 'generation_software', 'origin']
        for key in required_board_info:
            if key not in self.data['board_info']:
                raise ValueError(f"Missing required board_info field '{key}'")
                
        # Validate configuration
        required_config = [
            'algorithm', 'allow_diagonal_traces', 'resolution', 
            'connectors', 'keep_out_zone_aperture_diameter',
            'keep_out_zone_margin', 'gs_layer_name', 
            'socket_diameter_mapping', 'layer_mapping',
            'gerber_options'
        ]
        for key in required_config:
            if key not in self.data['configuration']:
                raise ValueError(f"Missing required configuration '{key}'")
                
        # Validate specific configuration elements
        if not isinstance(self.data['configuration']['socket_diameter_mapping'], dict):
            raise ValueError("'socket_diameter_mapping' must be a dictionary")
            
        if not isinstance(self.data['configuration']['layer_mapping'], dict):
            raise ValueError("'layer_mapping' must be a dictionary")
            
        # Validate modules
        if not isinstance(self.data['modules'], list):
            raise ValueError("'modules' must be a list")
            
        # Validate each module has required fields
        for i, module in enumerate(self.data['modules']):
            required_module_fields = ['name', 'position', 'rotation']
            for field in required_module_fields:
                if field not in module:
                    raise ValueError(f"Module at index {i} is missing required field '{field}'")
            
            # Validate position has x and y
            if 'x' not in module['position'] or 'y' not in module['position']:
                raise ValueError(f"Module at index {i} has invalid position format")
    
    @property
    def board_name(self) -> str:
        """Get the board name"""
        return self.data['board_info']['name']
    
    @property
    def board_size(self) -> Dict[str, int]:
        """Get the board size"""
        return self.data['board_info']['size']
    
    @property
    def board_origin(self) -> Dict[str, int]:
        """Get the board origin"""
        return self.data['board_info']['origin']
        
    @property
    def generation_software(self) -> Dict[str, str]:
        """Get the generation software info"""
        return self.data['board_info']['generation_software']
    
    @property
    def algorithm(self) -> str:
        """Get the routing algorithm"""
        return self.data['configuration']['algorithm']
    
    @property
    def allow_diagonal_traces(self) -> bool:
        """Get whether diagonal traces are allowed"""
        return bool(self.data['configuration']['allow_diagonal_traces'])
    
    @property
    def resolution(self) -> float:
        """Get the resolution setting"""
        return self.data['configuration']['resolution']
    
    @property
    def connectors(self) -> Dict[str, bool]:
        """Get connector settings"""
        return self.data['configuration']['connectors']
    
    @property
    def gs_layer_name(self) -> str:
        """Get the GerberSockets layer name"""
        return self.data['configuration']['gs_layer_name']
    
    @property
    def socket_diameter_mapping(self) -> Dict[str, float]:
        """Get the socket diameter mapping"""
        return self.data['configuration']['socket_diameter_mapping']
    
    @property
    def keep_out_zone_settings(self) -> Dict[str, float]:
        """Get keep-out zone settings"""
        return {
            'aperture_diameter': self.data['configuration']['keep_out_zone_aperture_diameter'],
            'margin': self.data['configuration']['keep_out_zone_margin']
        }
    
    @property
    def layer_mapping(self) -> Dict[str, Dict[str, Any]]:
        """Get the layer mapping configuration"""
        return self.data['configuration']['layer_mapping']
    
    @property
    def gerber_options(self) -> Dict[str, float]:
        """Get Gerber generation options"""
        return self.data['configuration']['gerber_options']
    
    @property
    def modules_data(self) -> List[Dict[str, Any]]:
        """Get the raw modules data"""
        return self.data['modules']
    
    @property
    def configuration(self) -> Dict[str, Any]:
        """Get the full configuration object"""
        return self.data['configuration']
        
    @property
    def board_dimensions(self) -> Tuple[int, int]:
        """Get board dimensions as a tuple (width, height)"""
        return (self.board_size['x'], self.board_size['y'])