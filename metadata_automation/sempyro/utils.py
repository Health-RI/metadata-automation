import os
import shutil
from pathlib import Path
from typing import Dict, Any

import yaml

from metadata_automation.sempyro.sempyro_generator import CustomPydanticGenerator

def create_temp_definition(link_dict: Dict[str, Any]) -> Dict[str, Any]:
    yaml_path = Path(link_dict['schema_path'])
    try:
        temp_yaml_path = yaml_path.parent.parent / 'temp' / yaml_path.name
        if not (yaml_path.parent.parent / 'temp').exists():
            os.makedirs(yaml_path.parent.parent / 'temp')
        shutil.copy2(yaml_path, temp_yaml_path)

        # Update the schema_path in the input dictionary
        link_dict['schema_path'] = str(temp_yaml_path)

    except Exception as e:
        raise IOError(f"Error writing YAML file to temporary directory: {e}")

    return link_dict


def add_validation_logic_to_schema(link_dict: Dict[str, Any]) -> None:
    validation_logic_path = Path("./inputs/sempyro/validation_logic.yaml")
    
    if not validation_logic_path.exists():
        return None

    schema_path = link_dict['schema_path']
        
    try:
        # Read original schema
        with open(schema_path, 'r', encoding='utf-8') as file:
            schema_data = yaml.safe_load(file)

        # Read validation logic
        with open(validation_logic_path, 'r', encoding='utf-8') as file:
            validation_logic = yaml.safe_load(file)
        
        # Apply validation logic
        if 'classes' not in schema_data or 'classes' not in validation_logic:
            return schema_data

        for class_name, class_config in validation_logic['classes'].items():
            # Only modify if class already exists in schema_data
            if class_name in schema_data['classes'] and 'annotations' in class_config:
                # Initialize class as dict if needed
                if 'annotations' not in schema_data['classes'][class_name]:
                    schema_data['classes'][class_name]['annotations'] = {}

                # Apply validation logic annotations
                for annotation_key, annotation_value in class_config['annotations'].items():
                    schema_data['classes'][class_name]['annotations'][annotation_key] = annotation_value

        with open(schema_path, 'w', encoding='utf-8') as file:
            yaml.dump(schema_data, file, default_flow_style=False, sort_keys=False, indent=2)
        
        print(f"Applied validation logic to {schema_path}")

    except Exception as e:
        print(f"Warning: Could not apply validation logic: {e}")
    return None


def add_rdf_model_to_yaml(link_dict: Dict[str, Any]) -> None:
    """
    Modifies a YAML schema file to add RDFModel imports and inheritance.

    Args:
        config_dict: Dictionary containing 'schema_path' and 'add_rdf_model_to_class' keys.
                    The 'schema_path' value will be updated with the new temporary file path.

    Returns:
        None

    Raises:
        FileNotFoundError: If the YAML file doesn't exist
        KeyError: If required keys are missing from the YAML structure
        yaml.YAMLError: If there's an error parsing the YAML file
    """
    # Check if add_rdf_model_to_class exists and is not None
    if not link_dict.get('add_rdf_model_to_class'):
        return None

    schema_path = link_dict.get('schema_path')
    class_names = link_dict['add_rdf_model_to_class']

    # Read the YAML file
    yaml_path = Path(schema_path)
    if not yaml_path.exists():
        raise FileNotFoundError(f"YAML file not found: {schema_path}")

    try:
        with open(yaml_path, 'r', encoding='utf-8') as file:
            yaml_data = yaml.safe_load(file)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Error parsing YAML file: {e}")
    

    # Add '../rdf_model' to imports if not already present
    rdf_import = '../rdf_model'
    if rdf_import not in yaml_data['imports']:
        yaml_data['imports'].append(rdf_import)

    # Check if 'classes' key exists
    if 'classes' not in yaml_data:
        return None

    # Add 'is_a: RDFModel' to specified classes
    classes_dict = yaml_data['classes']
    missing_classes = []

    for class_name in class_names:
        if class_name in classes_dict:
            if not isinstance(classes_dict[class_name], dict):
                classes_dict[class_name] = {}
            classes_dict[class_name]['is_a'] = 'RDFModel'
        else:
            missing_classes.append(class_name)

    # Log warning for missing classes (optional)
    if missing_classes:
        print(f"Warning: The following classes were not found in the YAML file: {missing_classes}")

    try:
        # Write the modified YAML to the temporary location
        with open(yaml_path, 'w', encoding='utf-8') as file:
            yaml.dump(yaml_data, file, default_flow_style=False, sort_keys=False, indent=2)
    except Exception as e:
        raise IOError(f"Error writing YAML file to temporary directory: {e}")

    print(f"Added RDFModel inheritance to {len(class_names) - len(missing_classes)} classes")
    print(f"Updated config_dict['schema_path'] to: {link_dict['schema_path']}")

    return None


def generate_from_linkml(link_dict):
    print(f"Generating from {link_dict['schema_path']}...")
    
    generator = CustomPydanticGenerator(
        schema=link_dict['schema_path'],
        imports=link_dict['imports'],
        black=True,
        template_dir="metadata_automation/sempyro/templates",
        mergeimports=False
    )

    with open(link_dict['output_path'], 'w') as fname:
        fname.write(generator.serialize())
    print("Done.")
