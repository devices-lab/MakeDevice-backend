import math

def consolidate_segments(routes, resolution, center_x, center_y):
    """
    Extends your existing segment-consolidation logic to also detect changes in z-coordinate.
    If z == 0, the segment is stored under the "TUNNELS" key;
    if z == 1, the segment is stored under the original net name.

    Parameters:
        routes (dict):
            {
              net_name: [  # list of paths
                [ (r0, c0, z0), (r1, c1, z1), ... ],
                [ (rA, cA, zA), ...],
                ...
              ],
              ...
            }
        resolution (float): The grid resolution (used to scale from index to real-world units).
        center_x (int): X-center of the grid in index space.
        center_y (int): Y-center of the grid in index space.

    Returns:
        dict: 
            {
               net_name: [ ( (x_start, y_start), (x_end, y_end) ), ... ],
               "TUNNELS": [ ( (x_start, y_start), (x_end, y_end) ), ... ]
            }
    """
    consolidated_routes = {}

    # Make sure we have a place for TUNNELS
    consolidated_routes["TUNNELS"] = []

    for net, all_paths in routes.items():
        # Also ensure each net has a list, to avoid KeyErrors
        if net not in consolidated_routes:
            consolidated_routes[net] = []

        for path in all_paths:
            # If the path has fewer than 2 points, you can't form a segment
            if len(path) < 2:
                continue

            # current_segment_start is the first node
            current_segment_start = path[0]
            # Compute the initial direction & z
            prev_row, prev_col, prev_z = current_segment_start
            current_direction = None  # We'll set it on first comparison

            # Walk the path
            for i in range(1, len(path)):
                row, col, z = path[i]
                
                # Compare direction to the previous node
                direction = (row - prev_row, col - prev_col)

                # If direction changes or z changes, we end the old segment here
                if current_direction is None:
                    # first step
                    current_direction = direction
                if direction != current_direction or z != prev_z:
                    # finish the old segment
                    store_segment(
                        consolidated_routes, net,
                        current_segment_start, path[i - 1],
                        resolution, center_x, center_y
                    )
                    # start a new segment at the old point
                    current_segment_start = path[i - 1]
                    current_direction = direction

                # Update loop variables
                prev_row, prev_col, prev_z = row, col, z

                # If this is the last node, close out the segment
                if i == len(path) - 1:
                    store_segment(
                        consolidated_routes, net,
                        current_segment_start, path[i],
                        resolution, center_x, center_y
                    )

    return consolidated_routes


def store_segment(consolidated_routes, net, start_node, end_node,
                  resolution, center_x, center_y):
    """
    Appends one line segment to either the `net` list or the "TUNNELS" list,
    depending on whether the segment's z is 1 or 0.
    We take z from the start_node (you could also average start_node.z & end_node.z).
    """

    (start_r, start_c, start_z) = start_node
    (end_r,   end_c,   end_z)   = end_node

    # Convert the first node to real world
    real_start = (
        (start_r - center_x) * resolution,  # X
        (center_y - start_c) * resolution   # Y
    )

    # Convert the second node
    real_end = (
        (end_r - center_x) * resolution,   
        (center_y - end_c) * resolution
    )

    # If z=0 => store in TUNNELS, else store in net
    if start_z == 0:
        consolidated_routes["TUNNELS"].append((real_start, real_end))
    else:
        consolidated_routes[net].append((real_start, real_end))
        
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
    
    return net_segments

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
            
            