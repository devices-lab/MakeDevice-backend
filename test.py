from gerber_writer import (DataLayer, Path, set_generation_software)
import os
    
set_generation_software('Karel Tavernier', 'gerber_writer_example_outline.py', '2022.06')    
profile_layer = DataLayer('Profile,NP')    
profile = Path()
profile.moveto((0, 0))
profile.lineto((150, 0))
profile.arcto((160, 10), (160, 0), '-')
profile.lineto((170, 10))
profile.lineto((170, 90))
profile.lineto((160, 90))
profile.arcto((150, 100), (160, 100), '-')
profile.lineto((0, 100))
profile.lineto((0, 0))
profile_layer.add_traces_path(profile, 0.5, 'Profile')

# Generate the filename for the outline Gerber file
file_path = os.path.join("./", "bob.gm1")

# Write the Gerber content to the file
with open(file_path, 'w') as file:
    file.write(profile_layer.dumps_gerber())