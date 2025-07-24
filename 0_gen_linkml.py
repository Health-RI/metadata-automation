# Load Excel file
from pathlib import Path

import pandas as pd
import yaml
from typing import List, Optional, Dict, Any

def load_excel_file(file_path: str, exclude_sheets: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Load an Excel file and return a dictionary of sheet data.
    
    Args:
        file_path: Path to the Excel file
        exclude_sheets: List of sheet names to exclude from the result
        
    Returns:
        Dictionary with sheet names as keys and DataFrame objects as values
    """
    if exclude_sheets is None:
        exclude_sheets = []
    
    # Read all sheets from the Excel file
    all_sheets = pd.read_excel(file_path, sheet_name=None)
    
    # Filter out excluded sheets
    filtered_sheets = {
        sheet_name: sheet_data 
        for sheet_name, sheet_data in all_sheets.items() 
        if sheet_name not in exclude_sheets
    }
    
    return filtered_sheets

excel_file_path = "./inputs/Health-RI-Metadata_CoreGenericHealth_v2-0-0.xlsx"
exclude_sheets = ['Info', 'User Guide']
# linkml_base_path = Path("./linkml-definitions")
linkml_base_path = Path("./temp-linkml")

excel_tables = load_excel_file(excel_file_path, exclude_sheets)

# Sheet with prefixes: 'prefixes'
table_prefixes = excel_tables['prefixes']
dict_prefixes = dict(zip(table_prefixes['prefix'], table_prefixes['namespace']))
# Output: {'linkml': 'https://w3id.org/linkml/', ...}

# Sheet with a table 'classes'
# sheet_name, ontology_name, inherits_from
# Dataset, dcat:Dataset, dcat:Resource
# Ontology names should also reflect application profiles. E.g., Health-RI Dataset should be hri:Dataset
table_classes = excel_tables['classes']


# Iterate over the rows in table_settings.
for index, row in table_classes.iterrows():
    sheet_name = row['sheet_name']
    ontology_name = row['ontology_name']
    inherits_from = row.get('inherits_from')
    class_description = str(row.get('description'))

    ontology = ontology_name.split(':')[0]
    ontology_class = ontology_name.split(':')[1]

    annotations = {
        'ontology': row['annotations_ontology'],
        'IRI': row['annotations_IRI'],
        'namespace': ontology.upper(),
        'prefix': ontology
    }

    class_sheet = excel_tables[sheet_name]
    class_slots = []

    slots = {}
    for index, row in class_sheet.iterrows():
        slot_name = row['Property label'].replace(' ','_')
        class_slots.append(slot_name)
        slots[slot_name] = {
            'description': row['Definition'],
            'slot_uri': row['Property URI'],
            'range': row['SHACL range'],
            'annotations': {
                'rdf_term': row['rdf_term'],
                'rdf_type': row['rdf_type'],
                'dash.viewer': row['dash.viewer'],
                'dash.editor': row['dash.editor'],
                'sempyro_range': row['Sempyro range']
            },
            'required': (str(row['Cardinality']) == '1' or str(row['Cardinality']) == '1..n'),
            'multivalued': (str(row['Cardinality']) == '0..n' or str(row['Cardinality']) == '1..n')
        }


    linkml_data = {}
    linkml_path = linkml_base_path / ontology / f"{ontology}-{ontology_class}.yaml"
    linkml_data['id'] = f"{dict_prefixes[ontology]}{ontology_class}"
    linkml_data['title'] = ontology_name.replace(':', '-')
    linkml_data['description'] = ontology_name.replace(':', '-')

    linkml_data['prefixes'] = dict_prefixes

    linkml_data['imports'] = ['linkml:types']
    
    # Handle imports for inheritance
    if inherits_from and str(inherits_from) != 'nan':
        inherits_ontology = inherits_from.split(':')[0]
        inherits_class = inherits_from.split(':')[1]
        
        if inherits_ontology == ontology:
            # Same ontology - import from same folder
            import_path = f"{inherits_ontology}-{inherits_class}"
        else:
            # Different ontology - go up one folder and into the other ontology folder
            import_path = f"../{inherits_ontology}/{inherits_ontology}-{inherits_class}"
        
        linkml_data['imports'].append(import_path)

    linkml_data['classes'] = {
        f"{ontology.upper()}{ontology_class.capitalize()}" : {
            'class_uri': ontology_name,
            'annotations': annotations,
            'slots': class_slots
        }
    }
    if class_description and class_description != 'nan':
        linkml_data['classes'][f"{ontology.upper()}{ontology_class.capitalize()}"]['description'] = class_description

    linkml_data['slots'] = slots

    # Create directories if they don't exist
    linkml_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write linkml_data as YAML to linkml_path
    with open(linkml_path, 'w') as f:
        yaml.dump(linkml_data, f, default_flow_style=False, sort_keys=False)
    
    print(f"Written {linkml_path}")
