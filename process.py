import json
import shutil
from pathlib import Path
from gerbonara import GerberFile, LayerStack
from numpy import pi


def merge_gerber_layers(module_details, layer_name, gerber_dir_path='./gerbers', output_dir_path='./output'):
    # Load the configuration from JSON (use this for now, later this will replaced with fetch from the frontend)
    with open(module_details, 'r') as file:
        modules = json.load(file)

    # Define the directories for input and output
    gerber_dir = Path(gerber_dir_path)
    output_dir = Path(output_dir_path)

    # Clear the output directory before saving new files
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
        output_file_path = output_dir / f'merged_{layer_name}.gbr'
        merged_gerber.save(output_file_path)
        return merged_gerber
    else:
        print(f"No '{layer_name}.gbr' files were processed.")
        return None



def merge_gerber_stacks(module_details, gerber_dir_path='./gerbers', output_dir_path='./output'):
    # Load the configuration from JSON
    with open(module_details, 'r') as file:
        modules = json.load(file)
        
    # Define the directories for the input Gerber files and the output directory
    gerber_dir = Path(gerber_dir_path)
    output_dir = Path(output_dir_path)

    # Remove the output directory if it exists
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize an empty LayerStack for merging
    merged_stack = None

    # Regex and overrides to handle special layer names
    # overrides = {
    #     r'.*?-Jacdac_Bus\.gbr$': ('other unknown')  # This regex matches any filename ending with -Jacdac_Bus.gbr
    # }

    # Process each module configuration
    for module in modules:
        # Path to the module's directory within the /gerbers directory
        module_path = gerber_dir / module['name']

        # Check if the directory exists
        if not module_path.exists() or not module_path.is_dir():
            print(f"Directory not found: {module_path}")
            continue

        # Load all Gerber files in the directory into a single LayerStack
        # Can add overrides to handle special layer names
        current_stack = LayerStack.open_dir(module_path)

        # Apply transformations and rotate
        rotation_radians = module['rotation'] * (pi / 180)
        current_stack.rotate(angle=rotation_radians)
        current_stack.offset(x=module['position']['x'], y=module['position']['y'])

        # Merge into the main stack
        if merged_stack is None:
            merged_stack = current_stack
        else:
            merged_stack.merge(current_stack)


    # Save the merged LayerStack to the output directory, if any files were processed
    if merged_stack:
        
        merged_stack.save_to_directory(output_dir)
    else:
        print("No files were processed.")
        
# Main function for now
if __name__ == '__main__':
    merge_gerber_layers('input.json', 'Jacdac_Bus')