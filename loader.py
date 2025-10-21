import json
from typing import Any, Dict, List
from pathlib import Path

class Loader:
    """
    Handles loading data from JSON sent from MakeDevice
    """
    
    def __init__(self, file_path: Path):
        """Initialize with a path to project file"""
        self.file_path = file_path
        self.data: Dict[str, Any] = {}
        # TODO: not sure where this property is used, everything by default is from server, so will set to True   
        self.run_from_server = True # TODO: find out where this is necessary
        
        # TODO: Default values, originally included in the legacy JSON format - move them into a separate place later
        self.generation_software = {
            "vendor": "Devices-Lab",
            "application": "MakeDevice",
            "version": "0.3"
        }
        self.origin = {'x': 0, 'y': 0}
        self.debug = False
        self.resolution = 0.25
        self.allow_diagonal_traces = True
        self.allow_overlap = False
        self.algorithm = "a_star"
        self.gerbersockets_layer_name = "GerberSockets.gbr"
        self.layer_map = {
            "F_Cu.gtl": {
                "nets": [],
                "fill": False,
                "attributes": "Copper,L1,Top,Signal"
            },
            # "In1_Cu.g2": {
            #     "nets": [],
            #     "fill": False,
            #     "attributes": "Copper,L2,Inner,Signal"
            # },
            # "In2_Cu.g3": {
            #     "nets": [],
            #     "fill": False,
            #     "attributes": "Copper,L3,Inner,Signal"
            # },
            "B_Cu.gbl": {
                "nets": [
                    "SWDIO~",
                    "SWDIO~^"
                ],
                "fill": False,
                "attributes": "Copper,L4,Bottom,Signal"
            }
        }
        self.module_margin = 0
        self.bus_width = 0.25
        self.bus_spacing = 0.5
        self.edge_clearance = 0.5
        self.track_width = 0.125
        self.via_diameter = 0.4
        self.via_hole_diameter = 0.3
        
        self._load()
        
    def _load(self) -> None:
        """Load JSON data"""
        try:
            with open(self.file_path, 'r') as file:
                self.data = json.load(file)

        except FileNotFoundError:
            raise FileNotFoundError(f"🔴 Project file could not be found: {self.file_path}")
        except json.JSONDecodeError:
            raise ValueError(f"🔴 File {self.file_path} is not a valid JSON (.MakeDevice file)")
    
    # -------------------- PROJECT DATA (from main JSON) --------------------------

    @property
    def id(self) -> str:
        """Get the project ID"""
        return self.data.get('id', '')

    @property
    def name(self) -> str:
        """Get the project name"""
        return self.data.get('name', '')

    @property
    def size(self) -> Dict[str, float]:
        """Get the board size"""
        return self.data.get('size', {})

    @property
    def width(self) -> float:
        """Get the board width"""
        return self.data.get('size', {}).get('width', 0)

    @property
    def height(self) -> float:
        """Get the board height"""
        return self.data.get('size', {}).get('height', 0)

    @property
    def fabrication_house(self) -> str:
        """Get fabrication house"""
        return self.data.get('pcbOptions', {}).get('fabricationHouse', '')

    @property
    def rounded_corner_radius(self) -> float:
        """Get corner radius"""
        return self.data.get('pcbOptions', {}).get('cornerRadius', 0)

    @property
    def connectors(self) -> Dict[str, bool]:
        """Get connector settings"""
        return self.data.get('pcbOptions', {}).get('connectors', {})

    @property
    def connector_top(self) -> bool:
        """Get whether top connector is enabled"""
        return bool(self.data.get('pcbOptions', {}).get('connectors', {}).get('top', False))

    @property
    def connector_bottom(self) -> bool:
        """Get whether bottom connector is enabled"""
        return bool(self.data.get('pcbOptions', {}).get('connectors', {}).get('bottom', False))

    @property
    def modules(self) -> List[Dict[str, Any]]:
        """Get modules list"""
        return self.data.get('modules', [])