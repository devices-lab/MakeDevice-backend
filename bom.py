import csv
import os


filepaths = [
    'BOMtest_1.csv',
    'BOMtest_2.csv',
    'BOMtest_3.csv'
]

# Read the BOM file and return a list of dictionaries
def read_bom_file(filepath):
    with open(filepath, newline='\n') as csvfile:
        dict_reader = csv.DictReader(csvfile)
        list_of_dict = list(dict_reader)
        return list_of_dict

# Iterate over each BOM file and read the contents
def iterate_files(filepaths):
    list_of_dicts = []
    print('Reading BOM files...')
    for filepath in filepaths:
        read_bom_file(filepath)
        list_of_dicts = list_of_dicts + (read_bom_file(filepath))
    return list_of_dicts

# Resolve duplicates  
def resolve_duplicates(duplicates):
    
    resolved_duplicates = []
    for d in duplicates:
        print(f'Resolving duplicates: {duplicates[d]}')
        resolved_duplicate = {}
        count = 0;
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

# Get all unique
def shake_designators(list_of_dicts):
    pass;

# Use for designator shaking...
def get_designator_pattern(designators):
    print('get_designator_pattern')
    print
    pass



# Test the functions
list_of_dicts = iterate_files(filepaths)
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
list_after_designator_shaking = get_designator_pattern(list_before_designator_shaking);

