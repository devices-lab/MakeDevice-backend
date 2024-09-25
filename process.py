import shutil
from pathlib import Path
from gerbonara import GerberFile, LayerStack, ExcellonFile
from numpy import pi

def merge_gerber_layers(modules, layer_name, gerber_dir_path='./modules', output_dir_path='./generated'):
    # Define the directories for input and output
    gerber_dir = Path(gerber_dir_path)
    output_dir = Path(output_dir_path)

    # Clear the output directory before saving new files
    # TODO: this might not be necessary, and also saving the Jacdac Bus layer 
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize an empty GerberFile for merging
    merged_gerber = None

    # Process each module configuration
    for module in modules:
        # Path to the module's directory within the /gerbers directory
        module_path = gerber_dir / module['name']

        # Check if the directory exists
        if not module_path.exists() or not module_path.is_dir():
            print(f"Directory not found: {module_path}")
            continue

        # Find files that end with the specified layer_name
        layer_files = list(module_path.glob(f'*{layer_name}.gbr'))
        for file_path in layer_files:
            if file_path.is_file():
                # Load the Gerber file
                gerber = GerberFile.open(file_path)
                
                # Apply transformations and rotate
                rotation_radians = module['rotation'] * (pi / 180)
                gerber.rotate(angle=rotation_radians)
                gerber.offset(dx=module['position']['x'], dy=module['position']['y'])

                # If there's no merged Gerber yet, use the current one
                if merged_gerber is None:
                    merged_gerber = gerber
                else:
                    # Merge the current Gerber into the merged Gerber
                    merged_gerber.merge(gerber)

    # Save the merged Gerber file to the output directory, if any files were processed
    if merged_gerber:
        output_file_path = output_dir / f'{layer_name}.gbr'
        merged_gerber.save(output_file_path)
        return merged_gerber
    else:
        print(f"No '{layer_name}.gbr' files were processed.")
        return None

def merge_gerber_stacks(modules, gerber_dir_path='./modules', output_dir_path='./output', additional_dir='./generated'):
    """
    Merges Gerber files from specified modules and an additional directory into a single LayerStack.
    
    Args:
        modules (list): List of dictionaries containing module configurations.
        gerber_dir_path (str): Path to the directory containing module Gerber files.
        output_dir_path (str): Path to the directory where the merged Gerber files will be saved.
        additional_dir (str): Path to the directory containing additional Gerber files to be merged.
    """
    # Define the directories for the input Gerber files and the output directory
    modules_dir = Path(gerber_dir_path)
    output_dir = Path(output_dir_path)
    additional_dir_path = Path(additional_dir)

    # Remove the output directory if it exists
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize an empty LayerStack for merging
    output_stack = None
    
    # Regex and overrides to handle special layer names
    overrides = {
        # r'.*?Jacdac_Bus\.gbr$': ('other unknown'),
        # r'.*?In1_Cu\.g2$': ('inner_1 copper'),
        # r'.*?In2_Cu\.g3$': ('inner_2 copper')
    }

    # Process each module configuration
    for module in modules:
        module_path = modules_dir / module['name']
        print(module_path)

        if not module_path.exists() or not module_path.is_dir():
            print(f"Directory not found: {module_path}")
            continue
    
        current_stack = LayerStack.open_dir(module_path, overrides=overrides) # Can add regex and overrides here
        apply_transformations(current_stack, module)
        output_stack = merge_into_stack(output_stack, current_stack)

    # Also process the additional directory containing other Gerber files
    # if additional_dir_path.exists() and additional_dir_path.is_dir():
    #     additional_stack = LayerStack.open_dir(additional_dir_path)
    #     output_stack = merge_into_stack(output_stack, additional_stack)

    # Save the merged LayerStack to the output directory, if any files were processed
    if output_stack:
        output_stack.save_to_directory(output_dir)
        print(f"Merged files saved to {output_dir}")
    else:
        print("No files were processed.")

def apply_transformations(layer_stack, module):
    rotation_radians = module['rotation'] * (pi / 180)
    layer_stack.rotate(angle=rotation_radians)
    layer_stack.offset(x=module['position']['x'], y=module['position']['y'])

def merge_into_stack(main_stack, stack_to_merge):
    if main_stack is None:
        return stack_to_merge
    else:
        # main_stack.merge(stack_to_merge)
        return main_stack
    
def merge_gerber_stacks_old(modules, gerber_dir='./modules', output_dir='./output'):

    # Define the directories for the input Gerber files and the output directory
    modules_dir_path = Path(gerber_dir)
    output_dir_path = Path(output_dir)

    # Remove the output directory if it exists
    if output_dir_path.exists():
        shutil.rmtree(output_dir_path)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    # Initialize an empty LayerStack for merging
    merged_stack = None

    # Regex and overrides to handle special layer names
    overrides = {
        r'.*?-Jacdac_Bus\.gbr$': ('other unknown')  # This regex matches any filename ending with -Jacdac_Bus.gbr
    }

    # Process each module configuration
    for module in modules:
        # Path to the module's directory within the /gerbers directory
        module_path = modules_dir_path / module['name']
        print("🐸 Module", module)

        # Check if the directory exists
        if not module_path.exists() or not module_path.is_dir():
            print(f"Directory not found: {module_path}")
            continue

        # Load all Gerber files in the directory into a single LayerStack
        # Can add overrides to handle special layer names
        current_stack = LayerStack.open_dir(module_path, overrides=overrides)

        # Apply transformations and rotate
        rotation_radians = module['rotation'] * (pi / 180)
        current_stack.rotate(angle=rotation_radians)
        current_stack.offset(x=module['position']['x'], y=module['position']['y'])

        # Merge into the main stack
        if merged_stack is None:
            merged_stack = current_stack
            print("🐸 First call, so returning")
        else:
            merged_stack.merge(current_stack, )
            print("🐸 Merged stack with another stack", merged_stack)

    # Save the merged LayerStack to the output directory, if any files were processed
    if merged_stack:
        
        merged_stack.save_to_directory(output_dir_path)
    else:
        print("No files were processed.")
    
def debug_merge(modules, modules_dir='./modules', output_dir='./output'):
    # Define the directories for the input Gerber files and the output directory
    modules_dir_path = Path(modules_dir)
    output_dir_path = Path(output_dir)

    # Remove the output directory if it exists
    if output_dir_path.exists():
        shutil.rmtree(output_dir_path)
    output_dir_path.mkdir(parents=True, exist_ok=True)