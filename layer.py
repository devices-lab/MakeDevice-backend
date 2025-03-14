from typing import Tuple, List
from gerbersockets import Zones
# from router import create_grid

class Layer:
    def __init__(self, name: str, attributes: str = None):
        self.name = name
        self.attributes = attributes
        self.nets: List[str] = []
        self.grid = None
    
    # def create_grid(self, zones: Zones, dimensions: Tuple[float, float], resolution: float) -> None:
    #     """
    #     Create a grid for the layer based on board dimensions and keep-out zones
        
    #     Parameters:
    #         zones: Keep-out zones for the board
    #         dimensions: (width, height) of the board in mm
    #         resolution: Size of each grid cell in mm
    #     """
    #     self.grid = create_grid(zones, dimensions, resolution)

    def add_net(self, net: str) -> None:
        """Add a net to the layer if it's not already present"""
        if net not in self.nets:
            self.nets.append(net)
    
    def __repr__(self) -> str:
        return f"Layer(name={self.name}, nets={self.nets})"