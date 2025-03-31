import json
from typing import Any, Dict, Union, List, Tuple
from pathlib import Path

class Loader:
    """
    Handles loading data from JSON sent from MakeDevice
    """
    
    def __init__(self, file_path: Union[str, Path], run_from_server: bool = False):
        """Initialize with path to JSON file"""
        self.file_path = Path(file_path)
        self.data: Dict[str, Any] = {}        
        self.run_from_server = run_from_server
        self._load()
        
    def _load(self) -> None:
        """Load JSON data"""
        try:
            with open(self.file_path, 'r') as file:
                self.data = json.load(file)

        except FileNotFoundError:
            raise FileNotFoundError(f"File {self.file_path} not found.")
        except json.JSONDecodeError:
            raise ValueError(f"File {self.file_path} is not a valid JSON.")
    
    # -------------------- BOARD --------------------------
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
    def size(self) -> Dict[str, float]:
        """Get the board size"""
        return self.data['board']['size']
    
    @property
    def origin(self) -> Dict[str, int]:
        """Get the board origin"""
        return self.data['board']['origin']
    
    @property
    def debug(self) -> bool:
        """Get the debug flag"""
        return bool(self.data['board'].get('debug', False))
    
    # ---------------- CONFIGURATION ------------------------
    
    @property
    def configuration(self) -> Dict[str, Any]:
        """Get the full configuration object"""
        return self.data['configuration']
    
    @property
    def resolution(self) -> float:
        """Get the resolution setting"""
        return self.data['configuration']['routing_options']['resolution']

    @property
    def allow_diagonal_traces(self) -> bool:
        """Get whether diagonal traces are allowed"""
        return bool(self.data['configuration']['routing_options'].get('allow_diagonal_traces', False))
    
    @property
    def allow_overlap(self) -> bool:
        """Get whether trace overlap for the same net is allowed"""
        return bool(self.data['configuration']['routing_options'].get('allow_overlap', False))
    
    @property
    def algorithm(self) -> str:
        """Get the routing algorithm"""
        return self.data['configuration']['routing_options']['algorithm']

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

    @property
    def bus_width(self) -> float:
        """Get bus width"""
        return self.data['configuration']['fabrication_options']['bus_width']

    @property
    def bus_spacing(self) -> float:
        """Get bus spacing"""
        return self.data['configuration']['fabrication_options']['bus_spacing']

    @property
    def edge_clearance(self) -> float:
        """Get edge clearance"""
        return self.data['configuration']['fabrication_options']['edge_clearance']

    @property
    def track_width(self) -> float:
        """Get track width"""
        return self.data['configuration']['fabrication_options']['track_width']

    @property
    def via_diameter(self) -> float:
        """Get via diameter"""
        return self.data['configuration']['fabrication_options']['via_diameter']

    @property
    def via_hole_diameter(self) -> float:
        """Get via hole diameter"""
        return self.data['configuration']['fabrication_options']['via_hole_diameter']

    @property
    def rounded_corner_radius(self) -> float:
        """Get rounded corner radius"""
        return self.data['configuration']['fabrication_options']['rounded_corner_radius']
    
    @property
    def connectors(self) -> Dict[str, bool]:
        """Get connector settings"""
        return self.data['configuration']['fabrication_options'].get('connectors', {})

    @property
    def connector_left(self) -> bool:
        """Get whether left connector is enabled"""
        connectors = self.connectors
        return bool(connectors.get('left', False))

    @property
    def connector_right(self) -> bool:
        """Get whether right connector is enabled"""
        connectors = self.connectors
        return bool(connectors.get('right', False))

    @property
    def connector_bottom(self) -> bool:
        """Get whether bottom connector is enabled"""
        connectors = self.connectors
        return bool(connectors.get('bottom', False))

    @property
    def connector_top(self) -> bool:
        """Get whether top connector is enabled"""
        connectors = self.connectors
        return bool(connectors.get('top', False))
    
    # -------------------- MODULES ------------------------

    @property
    def modules(self) -> List[Dict[str, Any]]:
        """Get modules list"""
        return self.data['modules']
