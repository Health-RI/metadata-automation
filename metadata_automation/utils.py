import os
import shutil
from pathlib import Path
from typing import Dict, Any

TEMP_FOLDER = Path("./linkml-definitions/temp")

def copy_temp_types() -> None:
    try:
        linkml_definitions_path = Path("./linkml-definitions")
        TEMP_FOLDER.mkdir(parents=True, exist_ok=True)

        shutil.copy2(linkml_definitions_path / 'types.yaml',
                     TEMP_FOLDER / 'types.yaml')

    except Exception as e:
        raise IOError(f"Error writing YAML file to temporary directory: {e}")

    return None


def create_temp_definition(link_dict: Dict[str, Any]) -> Dict[str, Any]:
    yaml_path = Path(link_dict['schema_path'])
    try:
        # Get the relative path from linkml-definitions to preserve folder structure
        linkml_definitions_path = Path("./linkml-definitions")
        relative_path = yaml_path.relative_to(linkml_definitions_path)
        
        # Create the temp path preserving the original folder structure
        temp_yaml_path = TEMP_FOLDER / relative_path
        
        # Create the directory structure if it doesn't exist
        temp_yaml_path.parent.mkdir(parents=True, exist_ok=True)
        
        shutil.copy2(yaml_path, temp_yaml_path)

        # Update the schema_path in the input dictionary
        link_dict['schema_path'] = str(temp_yaml_path)

    except Exception as e:
        raise IOError(f"Error writing YAML file to temporary directory: {e}")

    return link_dict

def remove_temp_definitions() -> None:
    if os.path.exists(TEMP_FOLDER):
        shutil.rmtree(TEMP_FOLDER)
    return None
