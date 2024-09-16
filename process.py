from gerbonara import LayerStack
from pathlib import Path
import os

# Define the directories for input and output
output_dir = Path('./output')

# Load the Gerber files into LayerStacks
stack1 = LayerStack.open('./gerbers/test_module_1')
stack2 = LayerStack.open('./gerbers/test_module_2')

# Apply transformations
# Rotate stack2 by 90 degrees
angle = 90  # degrees
stack2.rotate(angle=angle * (3.14159 / 180))  # Convert to radians

# Offset stack2 by 5mm in both x and y directions
stack2.offset(x=0.005, y=0.005)

# Merge the two stacks
stack1.merge(stack2)

# Save the merged LayerStack to the output directory
stack1.save_to_directory(output_dir)

# Checking the output directory
print("Files saved to:", output_dir)
