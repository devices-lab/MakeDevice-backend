
# Read the cpl file as csv and convert to list of dictionaries
import csv
from utils import read_csv, rotate_entries


# Iterate over each CPL file and read the contents
def iterate_cpl_files(modules, filepaths):
    
        # Get the filepaths for the CPL files
        myCplFilepaths = filepaths
        list_of_dicts = []
        print('Reading CPL files...')
        for module in modules:
            currentDict = read_csv(filepaths[modules.index(module)])
            
            # test rotation of components using the rotate_list_around_centroid function
            # Convert Mid X and Mid Y values from strings to floats, removing 'mm'
            for item in currentDict:
                item['Mid X'] = float(item['Mid X'].replace('mm', ''))
                item['Mid Y'] = float(item['Mid Y'].replace('mm', ''))
                

            # Rotate the components before offsetting their position
            # TODO: Add rotation to the module object
            currentDict = rotate_entries(currentDict, 0, 0, 90)
            
            # Convert back to strings with 'mm'
            for item in currentDict:
                item['Mid X'] = str(round(item['Mid X'], 4)) + 'mm'
                item['Mid Y'] = str(round(item['Mid Y'], 4)) + 'mm'
            
            # before adding the current_dict to list_of_dicts, offset the Mid X and Mid Y values by the position values of the module
            for item in currentDict:
                
                item['Mid X'] = str(round(float(item['Mid X'].replace('mm', '')) + module['position']['x'], 4)) + 'mm'
                item['Mid Y'] = str(round(float(item['Mid Y'].replace('mm', '')) + module['position']['y'], 4)) + 'mm'
        
            
            
            
            list_of_dicts = list_of_dicts + (currentDict)
        return list_of_dicts




# Map all the designators in the CPL to their new values
def map_cpl_designators(cpl_list, designator_mapping):
    print('returned: ' + str(cpl_list))
    mapped_list = []
    seen_designators = set()
    
    for item in cpl_list:
        new_item = item.copy()
        designator = item['Designator'].strip()
        
        if designator not in seen_designators:
            seen_designators.add(designator)
            mapped_list.append(new_item)
        else:
            if designator in designator_mapping:
                new_item['Designator'] = designator_mapping[designator]
            mapped_list.append(new_item)
            
    return mapped_list