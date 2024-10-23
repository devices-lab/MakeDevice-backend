import shutil
from pathlib import Path
from gerbonara import GerberFile, ExcellonFile, LayerStack
from numpy import pi

def merge_gerber_layers(modules, layer_name, modules_dir='./modules', output_dir='./output'):
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
            print(f"Directory not found: {module_path}")
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
        output_file_path = output_dir_path / f'{layer_name}'
        merged_file.save(output_file_path)
        return merged_file
    else:
        print(f"No files matching '{layer_name}' were processed.")
        return None
                           
def merge_gerber_stacks(modules, board_name, modules_dir='./modules', output_dir='./output', additional_dir='./generated'):
    modules_dir_path = Path(modules_dir)
    output_dir_path = Path(output_dir)
    additional_dir_path = Path(additional_dir)
    
    # Define patterns to recognize inner layer files
    inner_layers = ['In1_Cu.g2', 'In2_Cu.g3']  

    # Ensure the directory exists
    output_dir_path.mkdir(parents=True, exist_ok=True)

    merged_stack = None
    
    for module in modules:
        module_path = modules_dir_path / module['name']

        if not module_path.exists() or not module_path.is_dir():
            print(f"Directory not found: {module_path}")
            continue

        # Exclude inner layer files when opening LayerStack
        standard_layers = [f for f in module_path.iterdir() if not any(f.name.endswith(layer) for layer in inner_layers)]
        
        current_stack = LayerStack.from_files(standard_layers)
        
        # Apply transformations
        rotation_radians = module['rotation'] * (pi / 180)
        current_stack.rotate(angle=rotation_radians)
        current_stack.offset(x=module['position']['x'], y=module['position']['y'])
    
        # Merge non-inner layers into the main stack
        if merged_stack is None:
            merged_stack = current_stack
        else:
            merged_stack.merge(current_stack)

    if merged_stack:
        merged_stack.save_to_directory(output_dir)
    else:
        print("No standard files were processed.")
        
    # Handle inner layers separately
    for layer in inner_layers:
        merge_gerber_layers(modules, layer)
        
    # Rename the files in the output directory
    rename_files(output_dir, board_name)
    
    # And lastly, merge with the additional generated files
    merge_directories(output_dir_path, additional_dir_path)
    
def merge_directories(target_dir_path, source_dir_path):
    """
    Merges files from the source directory into the target directory.
    This function iterates over all files in the source directory and merges them into the corresponding files in the target directory. 
    If a file in the source directory has the same name as a file in the target directory, the function will merge the contents of the source file into the target file. 
    The type of file (Excellon or Gerber) is determined based on the file extension.
    Args:
        target_dir_path (Path): The path to the target directory where files will be merged.
        source_dir_path (Path): The path to the source directory containing files to be merged.
    """
    for source_file_path in source_dir_path.iterdir():
        if source_file_path.is_file():
            # Construct the corresponding file path in the target directory
            target_file_path = target_dir_path / source_file_path.name

            # Check if the corresponding file exists in the target directory
            if target_file_path.exists():
                # Determine the type of file based on the extension and process accordingly
                if source_file_path.suffix.upper() in ['.DRL',]:
                    # Process as Excellon files
                    source_file = ExcellonFile.open(source_file_path)
                    target_file = ExcellonFile.open(target_file_path)
                else:
                    # Process as Gerber files
                    source_file = GerberFile.open(source_file_path)
                    target_file = GerberFile.open(target_file_path)

                print("🏀 Target file: ", target_file)
                print("⚽️ Source file: ", source_file)
                
                # Merge the source Gerber file into the target Gerber file
                target_file.merge(source_file)

                # Save the merged Gerber file back to the target directory
                target_file.save(target_file_path)
                print(f"Merged '{source_file_path.name}' into '{target_file_path.name}'")

def rename_files(directory, base_name):
    """
    Renames files in the specified directory by removing any characters before and including a hyphen "-"
    and appending the remaining part of the filename to a new base name provided.

    Parameters:
    - directory (str): The directory where the files are located.
    - base_name (str): The base name to prepend to the remaining part of the filename.
    """
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        print(f"Directory not found: {directory}")
        return

    for file_path in dir_path.iterdir():
        if file_path.is_file():
            # Extract the part after the last hyphen
            parts = file_path.name.split('-')
            if len(parts) > 1:
                # Construct the new filename using the base name and the part after the last hyphen
                new_name = f"{base_name}-{parts[-1]}"
            else:
                # If no hyphen is present, use the base name directly with the original filename
                new_name = f"{base_name}-{file_path.name}"

            new_file_path = file_path.parent / new_name
            file_path.rename(new_file_path) 
            
def clear_directories(output_dir='./output', generated_dir='./generated'):
    output_dir_path = Path(output_dir)
    generated_dir_path = Path(generated_dir)
   
    if output_dir_path.exists():
        shutil.rmtree(output_dir_path)
    
    if generated_dir_path.exists():
        shutil.rmtree(generated_dir_path)
        
def remove_drill_plating_info(drill_file):
    return