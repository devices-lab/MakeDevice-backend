import math 

# Majority of the code in this file was generated using ChatGPT o1-preview 

def get_intersection_point(seg1, seg2):
    """Return the intersection point of two line segments if they intersect."""
    (A_x, A_y), (B_x, B_y) = seg1
    (C_x, C_y), (D_x, D_y) = seg2

    s1_x = B_x - A_x
    s1_y = B_y - A_y
    s2_x = D_x - C_x
    s2_y = D_y - C_y

    denom = (-s2_x * s1_y + s1_x * s2_y)
    if denom == 0:
        # Lines are parallel or colinear
        return None  # or handle colinear case if needed

    s = (-s1_y * (A_x - C_x) + s1_x * (A_y - C_y)) / denom
    t = ( s2_x * (A_y - C_y) - s2_y * (A_x - C_x)) / denom

    if 0 <= s <= 1 and 0 <= t <= 1:
        # Intersection detected
        I_x = A_x + (t * s1_x)
        I_y = A_y + (t * s1_y)
        return (I_x, I_y)
    else:
        # No intersection
        return None

def check_net_intersections_by_layer(net_segments, layer_mappings):
    """Check for intersections between nets on the same layer, if the layer has more than one net assigned to it."""
    # Build mapping from layers to nets
    layer_to_nets = {}
    for net_name, layer_info in layer_mappings.items():
        layer = layer_info[0]
        layer_to_nets.setdefault(layer, []).append(net_name)
    
    intersections = []
    points = []

    for layer, nets_on_layer in layer_to_nets.items():
        if len(nets_on_layer) > 1:
            # We have more than one net on this layer, check for intersections
            # print(f"Checking layer '{layer}' with nets {nets_on_layer}")
            # Collect segments for these nets
            net_segments_on_layer = {net: net_segments[net] for net in nets_on_layer if net in net_segments}
            # Now check for intersections between nets on this layer
            nets = list(net_segments_on_layer.keys())
            for net1_idx in range(len(nets)):
                net1 = nets[net1_idx]
                segments1 = net_segments_on_layer[net1]
                for net2_idx in range(net1_idx + 1, len(nets)):
                    net2 = nets[net2_idx]
                    segments2 = net_segments_on_layer[net2]
                    found_intersection = False
                    for seg1 in segments1:
                        for seg2 in segments2:
                            point = get_intersection_point(seg1, seg2)
                            if point and point not in points:
                                # print(f"Segments {seg1} in net '{net1}' and {seg2} in net '{net2}' intersect at {point}.")
                                points.append(point)
                                intersections.append({
                                    'layer': layer,
                                    'net1': net1,
                                    'net2': net2,
                                    'segment1': seg1,
                                    'segment2': seg2,
                                    'intersection_point': point
                                })
                                found_intersection = True
                    if not found_intersection:
                        print(f"No intersections found between nets '{net1}' and '{net2}' on layer '{layer}'.")
    return intersections

def process_intersections(intersections, intersection_clearance):
    """Process intersections to find points along the segment at a specified clearance."""
    results = []
    for item in intersections:
        intersection_point = item['intersection_point']
        segments = [item['segment1'], item['segment2']]
        used_segment = None
        for idx, segment in enumerate(segments):
            (x1, y1), (x2, y2) = segment
            ix, iy = intersection_point

            # Calculate distances from intersection point to segment ends
            d1 = ((ix - x1)**2 + (iy - y1)**2)**0.5
            d2 = ((ix - x2)**2 + (iy - y2)**2)**0.5

            if d1 > intersection_clearance and d2 > intersection_clearance:
                # Find the unit vectors towards each end of the segment
                dx1 = x1 - ix
                dy1 = y1 - iy
                l1 = (dx1**2 + dy1**2)**0.5
                u1 = (dx1 / l1, dy1 / l1)

                dx2 = x2 - ix
                dy2 = y2 - iy
                l2 = (dx2**2 + dy2**2)**0.5
                u2 = (dx2 / l2, dy2 / l2)

                # Calculate the points at intersection_clearance distance from the intersection point towards each end
                point1 = (ix + u1[0] * intersection_clearance, iy + u1[1] * intersection_clearance)
                point2 = (ix + u2[0] * intersection_clearance, iy + u2[1] * intersection_clearance)

                # Store the results
                result = {
                    'intersection': item,
                    'segment_used': segment,
                    'segment_used_index': idx + 1,  # 1 or 2
                    'point1': point1,
                    'point2': point2
                }
                results.append(result)
                used_segment = segment
                break  # Stop after finding a suitable segment
        if used_segment is None:
            print(f"🔴 Intersection at {intersection_point} is too close to the ends of both segments; clearance not satisfied.")
    return results

def merge_overlapping_segments(net_segments):
    """Merge overlapping colinear segments within each net."""

    for net_name, segments in net_segments.items():
        print(f"🟠 Processing net '{net_name}' for overlapping segments...")
        merged_segments = []
        segments = segments.copy()  # Copy to avoid modifying the list during iteration
        while segments:
            base_seg = segments.pop(0)
            base_p1, base_p2 = base_seg
            # Collect segments that are colinear and overlapping with base_seg
            colinear_segments = [base_seg]
            indices_to_remove = []
            i = 0
            while i < len(segments):
                seg = segments[i]
                if are_segments_colinear_and_overlapping(base_seg, seg):
                    colinear_segments.append(seg)
                    segments.pop(i)  # Remove the segment as it's going to be merged
                    # Do not increment i since we removed the current element
                else:
                    i += 1
            # Merge the collected colinear segments into one
            merged_seg = merge_colinear_segments(colinear_segments)
            merged_segments.append(merged_seg)
        net_segments[net_name] = merged_segments
        print(f"🟢 Net '{net_name}' now has {len(merged_segments)} segments after merging.")

def are_segments_colinear_and_overlapping(seg1, seg2):
    """Check if two segments are colinear and overlapping."""
    # Unpack points
    p1, p2 = seg1
    q1, q2 = seg2

    # Check if the two segments are colinear
    if not are_colinear(p1, p2, q1) or not are_colinear(p1, p2, q2):
        return False

    # Project points onto the line to get scalar parameters
    t1_start, t1_end = project_onto_line(p1, p2, p1), project_onto_line(p1, p2, p2)
    t2_start, t2_end = project_onto_line(p1, p2, q1), project_onto_line(p1, p2, q2)

    # Order the parameters
    t1_min, t1_max = sorted([t1_start, t1_end])
    t2_min, t2_max = sorted([t2_start, t2_end])

    # Check if the intervals overlap
    overlap = max(t1_min, t2_min) <= min(t1_max, t2_max)
    return overlap

def are_colinear(p1, p2, p3, tol=1e-8):
    """Check if three points are colinear."""
    # Calculate the area of the triangle formed by the three points
    area = abs((p1[0]*(p2[1] - p3[1]) + p2[0]*(p3[1] - p1[1]) + p3[0]*(p1[1] - p2[1])) / 2.0)
    return area < tol

def project_onto_line(a, b, p):
    """Project point p onto the line defined by points a and b, return scalar parameter t."""
    # Line vector
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    # If the line is a point
    if dx == 0 and dy == 0:
        return 0
    # Compute t such that p = a + t * (b - a)
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx*dx + dy*dy)
    return t

def merge_colinear_segments(segments):
    """Merge colinear overlapping segments into a single segment."""
    # All segments are colinear
    # Use the first segment as reference
    ref_p1, ref_p2 = segments[0]
    # Compute the line direction
    dx = ref_p2[0] - ref_p1[0]
    dy = ref_p2[1] - ref_p1[1]
    # Normalize direction vector
    length = math.hypot(dx, dy)
    if length == 0:
        # The segment is a point
        return segments[0]
    dir_vec = (dx / length, dy / length)
    # Project all endpoints onto the line to get scalar parameters
    t_values = []
    for seg in segments:
        for point in seg:
            t = project_onto_line(ref_p1, ref_p2, point)
            t_values.append(t)
    # Find the minimal and maximal t values
    t_min = min(t_values)
    t_max = max(t_values)
    # Compute the merged segment endpoints
    merged_p1 = (ref_p1[0] + t_min * dir_vec[0] * length, ref_p1[1] + t_min * dir_vec[1] * length)
    merged_p2 = (ref_p1[0] + t_max * dir_vec[0] * length, ref_p1[1] + t_max * dir_vec[1] * length)
    return (merged_p1, merged_p2)
        
def split_segments(net_segments, processed_results):
    """Modify segments by removing the original segment and adding two new segments at the intersection points."""
    for res in processed_results:
        net_name = res['intersection']['net' + str(res['segment_used_index'])]
        segment = res['segment_used']
        point1 = res['point1']
        point2 = res['point2']
        # Remove the original segment from net_segments[net_name]
        if net_name in net_segments:
            segments = net_segments[net_name]
            if segment in segments:
                # Remove the previous segment
                segments.remove(segment)
                print(f"🟠 Removed {segment} from {net_name} net")

                # Add the two new segments
                new_segment1 = (segment[0], point1)
                new_segment2 = (point2, segment[1])
                print(f"🟢 Added new segments {new_segment1}, {new_segment2} to {net_name} net")
                
                segments.extend([new_segment1, new_segment2])
            else:
                print(f"🔴 Segment {segment} not found in net '{net_name}'.")
        else:
            print(f"🔴 Net '{net_name}' not found in net_segments.")
            