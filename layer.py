from typing import List
from segment import Segment

class Layer:
    def __init__(self, name: str, attributes: str = None):
        self.name = name
        self.attributes = attributes
        self.nets: List[str] = []
        self.segments: List[Segment] = []  # Add a list to store segments

    def add_net(self, net: str) -> None:
        """Add a net to the layer if it's not already present"""
        if net not in self.nets:
            self.nets.append(net)
            
    def add_segment(self, segment: Segment) -> None:
        """Add a segment to the layer"""
        self.segments.append(segment)
    
    def get_segments_for_net(self, net_name: str) -> List[Segment]:
        """Get all segments for a specific net on this layer"""
        return [segment for segment in self.segments if segment.net_name == net_name]
    
    def clear_segments(self) -> None:
        """Clear all segments from the layer"""
        self.segments = []
    
    def __repr__(self) -> str:
        return f"Layer(name={self.name}, nets={self.nets}, segments={len(self.segments)})"