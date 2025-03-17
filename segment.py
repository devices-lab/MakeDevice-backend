from typing import List, Tuple, Optional
class Point:
    """Represents a point in 2D space with x and y coordinates."""
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
    
    def as_tuple(self) -> Tuple[float, float]:
        """Return the point as a tuple (x, y)"""
        return (self.x, self.y)
    
    @classmethod
    def from_tuple(cls, point_tuple: Tuple[float, float]) -> 'Point':
        """Create a Point from a tuple (x, y)"""
        return cls(point_tuple[0], point_tuple[1])
    
    def __repr__(self) -> str:
        return f"Point(x={self.x:.3f}, y={self.y:.3f})"


class Segment:
    """
    Represents a line segment with start and end points, 
    as well as layer and width information.
    """
    def __init__(self, start: Point, end: Point, layer: str = None, width: float = None):
        self.start = start
        self.end = end
        self.layer = layer  # Layer name (e.g., "F_Cu.gtl", "B_Cu.gbl")
        self.width = width  # Trace width in mm
    
    def as_tuple(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """Return the segment as a tuple of tuples ((start_x, start_y), (end_x, end_y))"""
        return (self.start.as_tuple(), self.end.as_tuple())
    
    @classmethod
    def from_tuple(cls, segment_tuple: Tuple[Tuple[float, float], Tuple[float, float]], 
                  layer: str = None, width: float = None) -> 'Segment':
        """Create a Segment from a tuple of tuples with optional layer and width"""
        start_point = Point.from_tuple(segment_tuple[0])
        end_point = Point.from_tuple(segment_tuple[1])
        return cls(start_point, end_point, layer, width)
    
    def length(self) -> float:
        """Calculate the length of the segment"""
        return ((self.end.x - self.start.x) ** 2 + (self.end.y - self.start.y) ** 2) ** 0.5
    
    def __repr__(self) -> str:
        layer_info = f", layer='{self.layer}'" if self.layer else ""
        width_info = f", width={self.width}" if self.width is not None else ""
        return f"Segment(start={self.start}, end={self.end}{layer_info}{width_info})"


class NetSegments:
    """Contains all segments for a specific net."""
    def __init__(self, net_name: str, segments: Optional[List[Segment]] = None):
        self.net_name = net_name
        self.segments = segments or []
    
    def add_segment(self, segment: Segment) -> None:
        """Add a segment to the net"""
        self.segments.append(segment)
    
    def add_segment_from_tuple(self, segment_tuple: Tuple[Tuple[float, float], Tuple[float, float]], 
                              layer: str = None, width: float = None) -> None:
        """Add a segment from a tuple representation with layer and width"""
        self.segments.append(Segment.from_tuple(segment_tuple, layer, width))
    
    def get_segments(self) -> List[Segment]:
        """Get all segments for this net"""
        return self.segments
    
    def get_segments_by_layer(self, layer: str) -> List[Segment]:
        """Get segments for a specific layer"""
        return [segment for segment in self.segments if segment.layer == layer]
    
    def total_length(self) -> float:
        """Calculate the total length of all segments in this net"""
        return sum(segment.length() for segment in self.segments)
    
    def __len__(self) -> int:
        return len(self.segments)
    
    def __getitem__(self, index: int) -> Segment:
        return self.segments[index]
    
    def __iter__(self):
        return iter(self.segments)
    
    def __repr__(self) -> str:
        return f"NetSegments(net_name='{self.net_name}', segments_count={len(self.segments)})"

