import csv
from cpl import iterate_cpl_files, map_cpl_designators
from utils import read_csv, rotate_entries, write_csv


# Read the bom file as csv and convert to list of dictionaries
def read_bom_file(filepath):
    with open(filepath, newline='\n') as csvfile:
        dict_reader = csv.DictReader(csvfile)
        list_of_dict = list(dict_reader)
        return list_of_dict

# Iterate over each BOM file and read the contents
def iterate_bom_files(filepaths):
    # Get the filepaths for the BOM files
    myBomFilepaths = filepaths
    list_of_dicts = []
    for filepath in myBomFilepaths:
        list_of_dicts = list_of_dicts + (read_csv(filepath))
    return list_of_dicts

# Resolve duplicates  
def resolve_duplicates(duplicates):
    
    resolved_duplicates = []
    for d in duplicates:
        # print(f'Resolving duplicates in bom...')
        resolved_duplicate = {}
        count = 0
        for e in duplicates[d]:
            if count == 0:
                resolved_duplicate = e
            else: 
                resolved_duplicate['Designator'] = resolved_duplicate['Designator'] + ',' + str(e['Designator'])  


            if (count != 0):
                resolved_duplicates.append(resolved_duplicate)
            count +=1
        
    
    return resolved_duplicates

def separate_unique_and_duplicates(dict_list, key_to_check):
    # Track occurrences of each key value
    value_count = {}
    for d in dict_list:
        value = str(d[key_to_check])
        value_count[value] = value_count.get(value, 0) + 1

    # Separate into unique and duplicate lists
    unique = [d for d in dict_list if value_count[str(d[key_to_check])] == 1]
    duplicates = [d for d in dict_list if value_count[str(d[key_to_check])] > 1]

    return {
        'unique': unique,
        'duplicates': duplicates
    }


def group_by_attribute(dict_list, attribute):
    grouped_dict = {}
    for d in dict_list:
        key = d.get(attribute)
        if key not in grouped_dict:
            grouped_dict[key] = []
        grouped_dict[key].append(d)
    return grouped_dict


def shake_designators(list_of_dicts):
    # print("\nDesignator mapping decisions:")
    # Initialize variables
    new_list = []
    designator_mapping = {}
    component_counters = {}
    seen_designators = {}  # Track first instance of each designator type
    all_mapping_decisions = []

    # Go through each dictionary in the list
    for item in list_of_dicts:
        new_item = item.copy()
        designators = item['Designator'].split(',')
        new_designators = []

        # Get component type (first letter of designator)
        for designator in designators:
            designator = designator.strip()
            component_type = ''.join(filter(str.isalpha, designator))
            
            # If this is the first instance of this designator type, keep original
            if component_type not in seen_designators:
                seen_designators[component_type] = designator
                new_designator = designator
                component_counters[component_type] = int(''.join(filter(str.isdigit, designator))) + 1
            else:
                # Create new designator for subsequent instances
                if component_type not in component_counters:
                    component_counters[component_type] = 1
                new_designator = f"{component_type}{component_counters[component_type]}"
                component_counters[component_type] += 1
            
            # Print mapping decision
            # print(f"Mapping {designator} -> {new_designator}")
            all_mapping_decisions.append(f"Mapping {designator} -> {new_designator}")
            
            # Store mapping
            designator_mapping[designator] = new_designator
            new_designators.append(new_designator)

        # Update item with new designators and maintain original designator
        new_item['Original Designator'] = item['Designator']
        new_item['Designator'] = ','.join(new_designators)
        new_list.append(new_item)

    return {
        "list": new_list,
        "mapping": designator_mapping,
        "all_mapping_decisions": all_mapping_decisions
    }
   







modules = {
  "board": {
    "name": "MakeDevice",
    "size": { "x": 100, "y": 100 },
    "origin": { "x": 0, "y": 0 }
  },
  "modules": [
    {
      "name": "test_module_1",
      "id": "b237c702-3c29-42c6-aac8-a5b155eae05d",
      "position": { "x": -15, "y": -30 },
      "rotation": 0
    },

    {
      "name": "test_module_1",
      "id": "b237c702-3c29-42c6-aac8-a5b155eae05d",
      "position": { "x": -25, "y": -30 },
      "rotation": 0
    }
  
  ]
}

# Below is a reference for how the bom and cpl functions can be used in the main script
# 
"""
list_of_dicts = iterate_bom_files(modules)
print(*list_of_dicts, sep='\n')
print('\n\n\n\n')

result = separate_unique_and_duplicates(list_of_dicts, 'JLCPCB Part')
grouped_result = group_by_attribute(result['duplicates'], 'JLCPCB Part')
resolved = resolve_duplicates(grouped_result)


# List before designator shaking
print('\n\n\n\n')
print('List before designator shaking')
list_before_designator_shaking = result['unique'] + resolved
print(*list_before_designator_shaking, sep='\n')

# List after designator shaking
after_designator_shaking = shake_designators(list_before_designator_shaking)

print('\n\n\n\n')
#print(list_after_designator_shaking["list"])
print(*after_designator_shaking["list"], sep='\n')
"""
"""
print('\n\n\n\n')
print(after_designator_shaking["mapping"])

print('\n\n\n\n')
print(after_designator_shaking["all_mapping_decisions"])

# Read the cpl file as csv and convert to list of dictionaries
list_of_cpl_dicts = iterate_cpl_files(modules)
print(*list_of_cpl_dicts, sep='\n')
print('\n\n\n\n')
 
mapped_cpl_list = map_cpl_designators(list_of_cpl_dicts, after_designator_shaking['mapping'])
print(*mapped_cpl_list, sep='\n')

# Print length of BOM and CPL lists
print(f"Length of BOM list: {len(list_of_dicts)}")
print(f"Length of CPL list: {len(list_of_cpl_dicts)}")



# Create a new list without the 'Original Designator' column
filtered_bom = [{k: v for k, v in d.items() if k != 'Original Designator'} for d in after_designator_shaking['list']]
write_csv('new_bom.csv', filtered_bom)
write_csv('new_cpl.csv', mapped_cpl_list)

 """