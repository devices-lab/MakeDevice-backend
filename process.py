import shutil
from pathlib import Path
from gerbonara import GerberFile, ExcellonFile
from numpy import pi

def merge_layers(modules, layer_name, board_name, modules_dir='./modules', output_dir='./output'):
    """
    Merges specified layers from multiple module configurations into a single Gerber file.
    Parameters:
        modules (list): A list of dictionaries, each containing:
            - 'name' (str): The name of the module.
            - 'rotation' (float): The rotation angle in degrees.
            - 'position' (dict): A dictionary with 'x' and 'y' keys for the position offset.
        layer_name (str): The name of the layer to merge.
        board_name (str): The name of the output board.
        modules_dir (str, optional): The directory containing module subdirectories. Defaults to './modules'.
        output_dir (str, optional): The directory to save the merged Gerber file. Defaults to './output'.
    Returns:
        GerberFile: The merged Gerber file if any files were processed, otherwise None.
    """
    # Define the directories for input and output
    modules_dir_path = Path(modules_dir)
    output_dir_path = Path(output_dir)

    # Ensure the directory exists
    output_dir_path.mkdir(parents=True, exist_ok=True)

    # Initialize an empty GerberFile for merging
    merged_file = None

    # Process each module configuration
    for module in modules:
        # Path to the module's directory within the /gerbers directory
        module_path = modules_dir_path / module['name']

        # Check if the directory exists
        if not module_path.exists() or not module_path.is_dir():
            print(f"🔴 Directory not found: {module_path}")
            continue

        # Find the first file that includes the specified layer_name in its filename
        file_path = next(module_path.glob(f'*{layer_name}'), None)
        if file_path and file_path.is_file():
            # Load the Gerber file
            current_file = GerberFile.open(file_path)
            
            # Apply transformations 
            rotation_radians = module['rotation'] * (pi / 180)
            current_file.rotate(angle=rotation_radians)
            current_file.offset(dx=module['position']['x'], dy=module['position']['y'])

            # If there's no merged Gerber yet, use the current one
            if merged_file is None:
                merged_file = current_file
            else: 
                merged_file.merge(current_file)
    
    # Save the merged Gerber file to the output directory, if any files were processed
    if merged_file:
        output_file_path = output_dir_path / f'{board_name}-{layer_name}'
        merged_file.save(output_file_path)
        return merged_file
    else:
        print(f"🔴 No files matching '{layer_name}' were processed.")
        return None
                           
def merge_stacks(modules, board_name, modules_dir='./modules', output_dir='./output', generated_dir='./generated'):
    """
    Merges Gerber stacks (sets of files) from multiple modules into a single output directory and applies necessary transformations.
    Parameters:
        modules (list): A list of dictionaries, each containing information about a module.
        board_name (str): The name of the board to be used in the merging process.
        modules_dir (str, optional): The directory where the module directories are located. Defaults to './modules'.
        output_dir (str, optional): The directory where the merged output will be stored. Defaults to './output'.
        generated_dir (str, optional): The directory containing additional generated files to be merged. Defaults to './generated'.
    Returns:
        None
    """
    modules_dir_path = Path(modules_dir)
    output_dir_path = Path(output_dir)
    generated_dir_path = Path(generated_dir)
    
    # Ensure the directory exists
    output_dir_path.mkdir(parents=True, exist_ok=True)

    for module in modules:
        module_path = modules_dir_path / module['name']

        if not module_path.exists() or not module_path.is_dir():
            print(f"🔴 Directory not found: '{module_path}'")
            continue
        
        # Merge each module's Gerber files into the output directory, and apply transformations 
        # by passing the information from each modules 
        merge_directories(output_dir_path, module_path, board_name, module)
        
    # And lastly, merge with the additional generated files from /generated directory
    merge_directories(output_dir_path, generated_dir_path, board_name)

def merge_directories(target_dir_path, source_dir_path, board_name, module=None):
    """
    Merges entire directories of Gerber and Excellon files from a source directory into a 
    target directory, applying optional transformations if the module information is provided.
    Parameters:
        target_dir_path (Path): The path to the target directory where merged files will be saved.
        source_dir_path (Path): The path to the source directory containing files to be merged.
        board_name (str): The name of the board to be used in the new filenames.
        module (dict, optional): A dictionary containing module information for transformations. 
                                Expected keys are 'rotation' (in degrees) and 'position' 
                                (a dictionary with 'x' and 'y' coordinates).
    Returns:
        None
    """
    # Process each Gerber or Excellon file in the module directory
    for source_file_path in source_dir_path.iterdir():
        
        if source_file_path.suffix.upper() not in ['.DRL', '.GTL', '.GBL', '.GTS', '.GBS', '.GTO', '.GBO', '.G2', '.G3', '.GTP', '.GBP']:
            # Omit the mechanical layer (".GM1"), as that gets handled separately 
            print(f"🟠 Skipping file for merging: {source_file_path}")
            continue
        
        # Construct the new target filename by replacing the module name with board_name
        new_file_name = f"{board_name}-{source_file_path.name.split('-', 1)[-1]}"
        target_file_path = target_dir_path / new_file_name

        # Determine the type of file based on the extension
        if source_file_path.suffix.upper() == '.DRL':
            source_file = ExcellonFile.open(source_file_path)
            target_file = ExcellonFile.open(target_file_path) if target_file_path.exists() else None
            
            # The the modules information is provided, apply the rotation and offset
            if module: 
                rotation_radians = module['rotation'] * (pi / 180)
                offset_x = module['position']['x']
                offset_y = module['position']['y']
                source_file.rotate(angle=rotation_radians)
                source_file.offset(x=offset_x, y=offset_y)
            
        else:
            source_file = GerberFile.open(source_file_path)
            target_file = GerberFile.open(target_file_path) if target_file_path.exists() else None
            
            # The the modules information is provided, apply the rotation and offset
            if module:
                rotation_radians = module['rotation'] * (pi / 180)
                offset_x = module['position']['x']
                offset_y = module['position']['y']
                source_file.rotate(angle=rotation_radians)
                source_file.offset(dx=offset_x, dy=offset_y)

        # Merge with the target file or use the source file if no target exists
        if target_file:
            target_file.merge(source_file)
            target_file.save(target_file_path)
            
        else:
            # Save the transformed source file directly if no target file exists
            source_file.save(target_file_path)
            
def clear_directories(output_dir='./output', generated_dir='./generated'):
    """
    Remove the specified output and generated directories if they exist.
    Parameters:
        output_dir (str): The path to the output directory to be cleared. Defaults to './output'.
        generated_dir (str): The path to the generated directory to be cleared. Defaults to './generated'.
    Returns:
        None
    """
    output_dir_path = Path(output_dir)
    generated_dir_path = Path(generated_dir)
   
    if output_dir_path.exists():
        shutil.rmtree(output_dir_path)
    
    if generated_dir_path.exists():
        shutil.rmtree(generated_dir_path)