from typing import Tuple, Optional

class Position:
    """
    A class representing a 2D position with x and y coordinates.
    """
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def as_tuple(self) -> Tuple[float, float]:
        """Return the position as a tuple (x, y)"""
        return (self.x, self.y)
    
    def __repr__(self) -> str:
        return f"Position(x={self.x}, y={self.y})"

class Module:
    def __init__(self, name: str, version: str, position: Tuple[float, float], rotation: float):
        self.name = name
        self.version = version
        # HACK: Manually inverting the y-coordinate here
        self.position = Position(position[0], -position[1])
        self.rotation = rotation
        self.grid = None
        # (bottom_left, top_left, top_right, bottom_right)
        self.zone: Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]] = None 
    
    def set_zone(self, p1: tuple[float, float], p2: tuple[float, float], 
             p3: tuple[float, float], p4: tuple[float, float]) -> None:
        """
        Set the keep-out zone for the module.
        """
        # Set the zone as a tuple of four tuples
        self.zone = (p1, p2, p3, p4)
    
    def is_within_board(self, board_dimensions: Tuple[float, float], origin: Tuple[float, float] = (0, 0)) -> bool:
        """
        Check if the module is entirely within the board boundaries.
        
        Parameters:
            board_dimensions: (width, height) of the board in mm
            origin: (x, y) origin of the board (default is (0, 0))
            
        Returns:
            bool: True if module is within board boundaries, False otherwise
        """
        if not self.bounding_box:
            # If no bounding box is defined, just check if the center position is within the board
            return (origin[0] <= self.position.x <= origin[0] + board_dimensions[0] and
                    origin[1] <= self.position.y <= origin[1] + board_dimensions[1])
        
        min_x, min_y, max_x, max_y = self.bounding_box
        # Adjust bounding box based on module position
        min_x += self.position.x
        min_y += self.position.y
        max_x += self.position.x
        max_y += self.position.y
        
        # Check if the entire bounding box is within the board
        return (origin[0] <= min_x and max_x <= origin[0] + board_dimensions[0] and
                origin[1] <= min_y and max_y <= origin[1] + board_dimensions[1])
    
    def get_position(self) -> Position:
        """Return the position as a tuple (x, y)"""
        return self.position.as_tuple()
    
    def get_rotation(self) -> float:
        """Return the rotation of the module"""
        return self.rotation
    
    def get_position_dict(self) -> dict:
        """Return the position as a dictionary with 'x' and 'y' keys"""
        return {"x": self.position.x, "y": self.position.y}
    
    def __repr__(self) -> str:
        return f"Module(name={self.name}, position={self.position}, rotation={self.rotation})"