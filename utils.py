import csv
import math

# Rotate a point around an arbitrary center point by given angle in degrees
def rotate_point(x, y, center_x, center_y, angle_degrees):
    """Rotate a point around a center point by given angle in degrees."""
    angle_rad = math.radians(angle_degrees)
    dx = x - center_x
    dy = y - center_y
    new_x = center_x + (dx * math.cos(angle_rad) - dy * math.sin(angle_rad))
    new_y = center_y + (dx * math.sin(angle_rad) + dy * math.cos(angle_rad))
    return new_x, new_y

# Rotate entries of a component placement file in the form of a list of dictionaries
def rotate_entries(entries, center_x, center_y, angle_degrees):
    """Rotate a list of component placement entries around a center point."""
    rotated_entries = []
    for entry in entries:
        # Create a new dict to avoid modifying the original
        new_entry = entry.copy()
        # Rotate the x, y coordinates
        new_x, new_y = rotate_point(entry['Mid X'], entry['Mid Y'], center_x, center_y, angle_degrees)
        new_entry['Mid X'] = new_x
        new_entry['Mid Y'] = new_y
        # Adjust the rotation angle if present
        if 'Rotation' in new_entry:
            new_entry['Rotation'] = str(
                round((float(new_entry['Rotation']) + angle_degrees) % 360, 2))
        rotated_entries.append(new_entry)
    return rotated_entries


def read_csv(filepath):
    with open(filepath, newline='\n', encoding='utf-8-sig') as csvfile:
        dict_reader = csv.DictReader(csvfile)
        list_of_dict = list(dict_reader)
        return list_of_dict

# Write csv file from list of dictionaries
def write_csv(filepath, list_of_dicts):
    with open(filepath, 'w', newline='') as csvfile:
        fieldnames = list_of_dicts[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for item in list_of_dicts:
            writer.writerow(item)


