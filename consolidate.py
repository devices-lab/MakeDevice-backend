import csv
from pathlib import Path
from typing import List, Dict, Tuple
import math

from module import Module

def consolidate_component_files(modules: List[Module], board_name: str, modules_dir='./modules', output_dir='./output') -> None:
    """
    Consolidates BOM files from multiple modules into a single BOM file,
    and updates the corresponding CPL (pick and place) files with adjusted positions.
    Ensures that all reference designators are unique across modules.
    
    Parameters:
        modules (List[Module]): A list of Module objects.
        board_name (str): The name of the output board.
        modules_dir (str, optional): The directory containing module subdirectories. Defaults to './modules'.
        output_dir (str, optional): The directory to save the consolidated BOM file. Defaults to './output'.
    
    Returns:
        None
    """
    # Convert paths to Path objects
    modules_dir_path = Path(modules_dir)
    output_dir_path = Path(output_dir)
    
    # Ensure output directory exists
    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    # Dictionary to store all components with their unique reference designators
    # Key format: "module_index:module_name:original_ref" -> ensures uniqueness across duplicate modules
    all_components = {}
    
    # Dictionary to track reference designator remapping
    # Key: "module_index:module_name:original_ref", Value: "new_unique_ref"
    ref_mapping = {}
    
    # Dictionary to track the CPL data for each component
    cpl_entries = {}
    
    # Track used reference prefixes to avoid duplicates
    used_refs = set()
    
    # First pass: collect all reference designators and assign unique ones
    for module_idx, module in enumerate(modules):
        module_path = modules_dir_path / module.name
        
        # Check if the module directory exists
        if not module_path.exists() or not module_path.is_dir():
            print(f"🔴 Module not found: {module_path}")
            continue
        
        # Find BOM file for this module
        bom_files = list(module_path.glob("BOM_*.csv"))
        if not bom_files:
            print(f"🟠 No BOM file found for module: {module.name}")
            continue
        
        bom_file_path = bom_files[0]  # Use the first BOM file found
        
        # Find CPL file for this module
        cpl_files = list(module_path.glob("CPL_*.csv"))
        if not cpl_files:
            print(f"🟠 No CPL file found for module: {module.name}")
            continue
        
        cpl_file_path = cpl_files[0]  # Use the first CPL file found
        
        # Process BOM file and collect references - using module_idx to ensure uniqueness
        collect_references(bom_file_path, cpl_file_path, module, ref_mapping, all_components, used_refs, module_idx)
    
    # Process component grouping (same value and package get same part number)
    component_groups = group_components(all_components)
    
    # Second pass: Process CPL files with updated reference designators
    for module_idx, module in enumerate(modules):
        module_path = modules_dir_path / module.name
        
        if not module_path.exists() or not module_path.is_dir():
            continue
            
        cpl_files = list(module_path.glob("CPL_*.csv"))
        if not cpl_files:
            continue
            
        cpl_file_path = cpl_files[0]
        
        # Process CPL file with updated references - using module_idx to match with first pass
        process_cpl_file(cpl_file_path, module, ref_mapping, cpl_entries, module_idx)
    
    # Write consolidated BOM to output file
    write_consolidated_bom(component_groups, output_dir_path, board_name)
    
    # Write consolidated CPL to output file
    write_consolidated_cpl(cpl_entries, output_dir_path, board_name)


def collect_references(bom_file_path: Path, cpl_file_path: Path, module: Module, 
                    ref_mapping: Dict, all_components: Dict, used_refs: set, module_idx: int) -> None:
    """
    Collects reference designators from BOM and CPL files and assigns unique identifiers.
    
    Parameters:
        bom_file_path (Path): Path to the BOM file.
        cpl_file_path (Path): Path to the CPL file.
        module (Module): The module object.
        ref_mapping (Dict): Dictionary for mapping original to new references.
        all_components (Dict): Dictionary to store all component data.
        used_refs (set): Set of already used reference designators.
        module_idx (int): Module index for prefix assignment.
        
    Returns:
        None
    """
    try:
        # First, read the CPL file to get a list of actual components placed
        cpl_refs = set()
        cpl_data = {}
        
        with open(cpl_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                designator = row.get("Designator", "").strip()
                if designator:
                    cpl_refs.add(designator)
                    cpl_data[designator] = row
        
        # Now process the BOM file
        with open(bom_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Get the fieldnames to ensure we maintain the original format
            fieldnames = reader.fieldnames
            
            if not fieldnames:
                print(f"🔴 Invalid BOM file format for: {bom_file_path}")
                return
            
            # Process each component
            for row in reader:
                value = row.get("Value", "")
                package = row.get("Package", "")
                lcsc_part = row.get("LCSC Part", "").strip()
                references = row.get("Reference", "").split(',')
                
                # Process each reference designator
                for ref in references:
                    ref = ref.strip()
                    if not ref:
                        continue
                    
                    # Skip if not in CPL (not placed on board)
                    if ref not in cpl_refs:
                        continue
                    
                    # Create a unique key for this specific instance
                    # Include module_idx to handle duplicate modules
                    component_key = f"{module_idx}:{module.name}:{ref}"
                    
                    # Generate a new unique reference designator
                    # Extract the prefix (e.g., "R" from "R1") and number
                    prefix = ''.join(c for c in ref if not c.isdigit())
                    if not prefix:
                        prefix = 'X'  # Fallback if no alphabetic prefix
                    
                    # Find a unique new reference
                    counter = 1
                    while True:
                        new_ref = f"{prefix}{module_idx}{counter}"
                        if new_ref not in used_refs:
                            break
                        counter += 1
                    
                    used_refs.add(new_ref)
                    ref_mapping[component_key] = new_ref
                    
                    # Store component data
                    all_components[component_key] = {
                        "Value": value,
                        "Package": package,
                        "LCSC Part": lcsc_part,
                        "original_reference": ref,
                        "new_reference": new_ref,
                        "module_name": module.name,
                        "module_idx": module_idx,
                        "fieldnames": fieldnames
                    }
    
    except Exception as e:
        print(f"🔴 Error collecting references from files: {e}")


def group_components(all_components: Dict) -> Dict:
    """
    Groups components with the same value and package to ensure consistent part numbers.
    
    Parameters:
        all_components (Dict): Dictionary containing all component data.
        
    Returns:
        Dict: Dictionary of grouped components with consistent part numbers.
    """
    # Dictionary to store component groups
    component_groups = {}
    
    # First, group by value and package
    value_package_groups = {}
    
    for comp_key, comp_data in all_components.items():
        value = comp_data["Value"]
        package = comp_data["Package"]
        
        group_key = f"{value}_{package}"
        
        if group_key not in value_package_groups:
            value_package_groups[group_key] = []
        
        value_package_groups[group_key].append(comp_key)
    
    # For each group, use the first instance's LCSC Part number for all
    for group_key, comp_keys in value_package_groups.items():
        if not comp_keys:
            continue
        
        # Use the first instance's part number
        first_comp = all_components[comp_keys[0]]
        lcsc_part = first_comp["LCSC Part"]
        
        # Create a group entry
        component_groups[group_key] = {
            "Value": first_comp["Value"],
            "Package": first_comp["Package"],
            "LCSC Part": lcsc_part,
            "references": [all_components[key]["new_reference"] for key in comp_keys],
            "fieldnames": first_comp["fieldnames"]
        }
    
    return component_groups


def process_cpl_file(cpl_file_path: Path, module: Module, ref_mapping: Dict, cpl_entries: Dict, module_idx: int) -> None:
    """
    Processes a CPL file and adjusts positions and rotations based on module placement.
    Updates reference designators based on the mapping.
    
    Parameters:
        cpl_file_path (Path): Path to the CPL file.
        module (Module): Module object containing position and rotation information.
        ref_mapping (Dict): Dictionary mapping original to new reference designators.
        cpl_entries (Dict): Dictionary to store processed CPL entries.
        module_idx (int): Module index to match with the correct references.
        
    Returns:
        None
    """
    try:
        with open(cpl_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Get the fieldnames to ensure we maintain the original format
            fieldnames = reader.fieldnames
            
            if not fieldnames:
                print(f"🔴 Invalid CPL file format for: {cpl_file_path}")
                return
            
            # Process each component
            for row in reader:
                # Get the original values
                designator = row.get("Designator", "").strip()
                if not designator:
                    continue
                
                # Generate the component key for lookup
                component_key = f"{module_idx}:{module.name}:{designator}"
                
                # Skip if this component doesn't have a mapped reference
                if component_key not in ref_mapping:
                    continue
                
                # Get the new reference designator
                new_ref = ref_mapping[component_key]
                
                # Get placement data
                mid_x = float(row.get("Mid X", 0))
                mid_y = float(row.get("Mid Y", 0))
                rotation = float(row.get("Rotation", 0))
                
                # Apply module rotation and position offset
                new_x, new_y, new_rotation = transform_coordinates(
                    mid_x, mid_y, rotation, 
                    module.position.x, module.position.y, module.rotation
                )
                
                # Create a new row with transformed data and new designator
                updated_row = row.copy()
                updated_row["Designator"] = new_ref
                updated_row["Mid X"] = f"{new_x:.6f}"
                updated_row["Mid Y"] = f"{new_y:.6f}"
                updated_row["Rotation"] = f"{new_rotation:.6f}"
                
                # Store the CPL entry with the new reference as the key
                cpl_entries[new_ref] = {
                    "row": updated_row,
                    "fieldnames": fieldnames
                }
    
    except Exception as e:
        print(f"🔴 Error processing CPL file {cpl_file_path}: {e}")


def transform_coordinates(x: float, y: float, rotation: float, offset_x: float, offset_y: float, module_rotation: float) -> Tuple[float, float, float]:
    """
    Transforms coordinates based on module position and rotation.
    Components are rotated around the module's center point.
    
    Parameters:
        x (float): Original X coordinate relative to module's center.
        y (float): Original Y coordinate relative to module's center.
        rotation (float): Original rotation in degrees.
        offset_x (float): X offset for module position.
        offset_y (float): Y offset for module position.
        module_rotation (float): Module rotation in degrees.
    
    Returns:
        Tuple[float, float, float]: Transformed X, Y, and rotation.
    """
    # Convert rotation to radians
    module_rotation_rad = math.radians(-module_rotation)  # Negative to reverse rotation direction
    
    # Rotate the component position around origin (module's center)
    # Using negative rotation angle to reverse the direction
    rotated_x = x * math.cos(module_rotation_rad) - y * math.sin(module_rotation_rad)
    rotated_y = x * math.sin(module_rotation_rad) + y * math.cos(module_rotation_rad)
    
    # Add the module's position offset
    new_x = rotated_x + offset_x
    new_y = rotated_y + offset_y
    
    # Update the component's rotation by adding module rotation
    # Keep within 0-360 degree range
    new_rotation = (rotation + module_rotation) % 360
    
    return new_x, new_y, new_rotation


def write_consolidated_bom(component_groups: Dict, output_dir_path: Path, board_name: str) -> None:
    """
    Writes the consolidated BOM components to a CSV file.
    
    Parameters:
        component_groups (Dict): Dictionary of grouped components.
        output_dir_path (Path): Output directory path.
        board_name (str): Name of the output board.
    
    Returns:
        None
    """
    if not component_groups:
        print("🟠 No components to write to consolidated BOM file.")
        return
    
    # Get the fieldnames from the first component to ensure consistent format
    first_component = next(iter(component_groups.values()))
    fieldnames = first_component.get("fieldnames", ["Value", "Reference", "Package", "LCSC Part"])
    
    output_file_path = output_dir_path / f"BOM_{board_name}.csv"
    
    try:
        with open(output_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for component_key, component in component_groups.items():
                # Create a row for this component
                row = {}
                for field in fieldnames:
                    if field == "Reference":
                        # For Reference field, join the new unique references
                        row[field] = ','.join(component["references"])
                    elif field in component:
                        row[field] = component[field]
                    else:
                        row[field] = ""
                
                writer.writerow(row)
        
        print(f"🟢 Consolidated BOM written to: {output_file_path}")
    
    except Exception as e:
        print(f"🔴 Error writing consolidated BOM file: {e}")


def write_consolidated_cpl(cpl_entries: Dict, output_dir_path: Path, board_name: str) -> None:
    """
    Writes the consolidated CPL data to a CSV file.
    
    Parameters:
        cpl_entries (Dict): Dictionary of CPL entries with new reference designators as keys.
        output_dir_path (Path): Output directory path.
        board_name (str): Name of the output board.
    
    Returns:
        None
    """
    if not cpl_entries:
        print("🟠 No CPL data to write to consolidated CPL file.")
        return
    
    # Get the fieldnames from the first entry to ensure consistent format
    first_entry = next(iter(cpl_entries.values()))
    fieldnames = first_entry.get("fieldnames", ["Designator", "Val", "Package", "Mid X", "Mid Y", "Rotation", "Layer"])
    
    output_file_path = output_dir_path / f"CPL_{board_name}-top-pos.csv"
    
    try:
        with open(output_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for _, entry in cpl_entries.items():
                # Write the row data
                writer.writerow(entry["row"])
        
        print(f"🟢 Consolidated CPL written to: {output_file_path}")
    
    except Exception as e:
        print(f"🔴 Error writing consolidated CPL file: {e}")