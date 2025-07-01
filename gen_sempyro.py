import os

from linkml.generators.pydanticgen import PydanticGenerator
from linkml.generators.pydanticgen.pydanticgen import SplitMode
from linkml.generators.pydanticgen.template import Imports, PydanticModule, PydanticBaseModel
from linkml_runtime.utils.formatutils import camelcase
from linkml_runtime.utils.schemaview import SchemaView

from imports_gen_sempyro import imports_dcat_dataset, imports_dcat_resource

import ast
import yaml
from pathlib import Path
from typing import Set, Tuple
from typing import Dict, Any, List

import tempfile
import shutil


class CustomPydanticGenerator(PydanticGenerator):
    """Custom PydanticGenerator that skips default imports"""

    def render(self) -> PydanticModule:
        """
        Override render to skip DEFAULT_IMPORTS
        """
        sv: SchemaView
        sv = self.schemaview

        # Start with empty imports instead of DEFAULT_IMPORTS
        imports = Imports()

        # Add custom imports if provided
        if self.imports is not None:
            if isinstance(self.imports, Imports):
                imports += self.imports
            else:
                for i in self.imports:
                    imports += i
        if self.split_mode == SplitMode.FULL:
            imports += self._get_imports()

        # injected classes - we'll also need to handle this
        # since DEFAULT_INJECTS might include things that depend on DEFAULT_IMPORTS
        injected_classes = []  # Start with empty instead of DEFAULT_INJECTS
        if self.injected_classes is not None:
            injected_classes += self.injected_classes.copy()

        # enums
        enums = self.before_generate_enums(list(sv.all_enums().values()), sv)
        enums = self.generate_enums({e.name: e for e in enums})

        base_model = PydanticBaseModel(extra_fields=self.extra_fields, fields=self.injected_fields)

        # schema classes
        class_results = []
        source_classes, imported_classes = self._get_classes(sv)
        source_classes = self.sort_classes(source_classes, imported_classes)
        # Don't want to generate classes when class_uri is linkml:Any, will
        # just swap in typing.Any instead down below
        source_classes = [c for c in source_classes if c.class_uri != "linkml:Any"]
        source_classes = self.before_generate_classes(source_classes, sv)
        self.sorted_class_names = [camelcase(c.name) for c in source_classes]
        for cls in source_classes:
            cls = self.before_generate_class(cls, sv)
            result = self.generate_class(cls)
            result = self.after_generate_class(result, sv)
            class_results.append(result)
            if result.imports is not None:
                imports += result.imports
            if result.injected_classes is not None:
                injected_classes.extend(result.injected_classes)

        class_results = self.after_generate_classes(class_results, sv)

        classes = {r.cls.name: r.cls for r in class_results}
        injected_classes = self._clean_injected_classes(injected_classes)

        imports.render_sorted = self.sort_imports

        module = PydanticModule(
            metamodel_version=self.schema.metamodel_version,
            version=self.schema.version,
            python_imports=imports,
            base_model=base_model,
            injected_classes=injected_classes,
            enums=enums,
            classes=classes,
        )
        module = self.include_metadata(module, self.schemaview.schema)
        module = self.before_render_template(module, self.schemaview)
        return module


def extract_local_definitions(yaml_file: Path) -> Set[str]:
    """Extract names of locally defined enums and classes from LinkML YAML."""
    with open(yaml_file, 'r') as f:
        schema = yaml.safe_load(f)

    local_names = set()

    # Extract enum names
    if 'enums' in schema:
        local_names.update(schema['enums'].keys())

    # Extract class names
    if 'classes' in schema:
        local_names.update(schema['classes'].keys())

    return local_names


def find_class_ranges(python_file: Path) -> List[Tuple[str, int, int]]:
    """
    Find all class definitions and their line ranges in the Python file.

    Returns a list of tuples: (class_name, start_line, end_line)
    """
    with open(python_file, 'r') as f:
        source = f.read()
        source_lines = source.splitlines()

    tree = ast.parse(source)

    class_ranges = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            # Start line is straightforward
            start_line = node.lineno - 1  # Convert to 0-based

            # Find the actual end of the class by looking for the last non-empty line
            end_line = node.end_lineno - 1  # Convert to 0-based

            # Extend end_line to include any trailing empty lines that belong to this class
            # Look ahead until we find a non-empty line or reach the end
            actual_end = end_line
            for i in range(end_line + 1, len(source_lines)):
                line = source_lines[i].strip()
                if line:  # Found a non-empty line
                    # Check if it's the start of a new class/function/statement
                    if not line.startswith(' ') and not line.startswith('\t'):
                        actual_end = i - 1
                        break
                    else:
                        # It's indented, so still part of something else
                        break
            else:
                # Reached end of file
                actual_end = len(source_lines) - 1

            class_ranges.append((node.name, start_line, actual_end))

    return class_ranges


def remove_unwanted_classes(python_file: Path, yaml_file: Path, output_file: Path = None) -> None:
    """
    Remove classes that are not locally defined in the YAML file.

    This approach preserves all formatting, imports, logger setup, and other code,
    only removing the unwanted class definitions.

    Args:
        python_file: Path to the generated Python file with all Pydantic classes
        yaml_file: Path to the LinkML YAML schema file
        output_file: Path for the filtered output (defaults to python_file.stem + '_filtered.py')
    """
    if output_file is None:
        output_file = python_file

    # Extract local definitions
    local_definitions = extract_local_definitions(yaml_file)
    print(f"Found local definitions: {local_definitions}")

    # Read all source lines
    with open(python_file, 'r') as f:
        source_lines = f.readlines()

    # Find all class ranges
    class_ranges = find_class_ranges(python_file)

    # Determine which lines to remove
    lines_to_remove = set()
    removed_classes = []

    for class_name, start_line, end_line in class_ranges:
        if class_name not in local_definitions:
            # Mark these lines for removal
            for i in range(start_line, end_line + 1):
                lines_to_remove.add(i)
            removed_classes.append(class_name)

    print(f"Removing classes: {removed_classes}")

    # Filter out the unwanted lines
    output_lines = []
    for i, line in enumerate(source_lines):
        if i not in lines_to_remove:
            output_lines.append(line)

    # Clean up excessive blank lines (optional)
    # This removes cases where we might have 3+ consecutive blank lines
    cleaned_lines = []
    blank_count = 0

    for line in output_lines:
        if line.strip() == '':
            blank_count += 1
            if blank_count <= 2:  # Allow up to 2 consecutive blank lines
                cleaned_lines.append(line)
        else:
            blank_count = 0
            cleaned_lines.append(line)

    # Write the filtered output
    with open(output_file, 'w') as f:
        f.writelines(cleaned_lines)

    print(f"Filtered Pydantic classes written to: {output_file}")
    print(f"Kept {len(local_definitions)} local definitions, removed {len(removed_classes)} imported classes")


def add_rdf_model_to_yaml(link_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Modifies a YAML schema file to add RDFModel imports and inheritance.
    Creates a modified copy in a temporary directory and updates the config_dict.

    Args:
        config_dict: Dictionary containing 'schema_path' and 'add_rdf_model_to_class' keys.
                    The 'schema_path' value will be updated with the new temporary file path.

    Returns:
        str: Path to the new temporary YAML file

    Raises:
        FileNotFoundError: If the YAML file doesn't exist
        KeyError: If required keys are missing from the YAML structure
        yaml.YAMLError: If there's an error parsing the YAML file
    """
    # Check if add_rdf_model_to_class exists and is not None
    if not link_dict.get('add_rdf_model_to_class'):
        return link_dict

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
        return link_dict

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
        temp_yaml_path = yaml_path.parent.parent / 'temp' / yaml_path.name
        os.makedirs(yaml_path.parent.parent / 'temp', exist_ok=True)
        shutil.copy2(yaml_path, temp_yaml_path)

        # Write the modified YAML to the temporary location
        with open(temp_yaml_path, 'w', encoding='utf-8') as file:
            yaml.dump(yaml_data, file, default_flow_style=False, sort_keys=False, indent=2)

        # Update the schema_path in the input dictionary
        link_dict['schema_path'] = str(temp_yaml_path)

    except Exception as e:
        raise IOError(f"Error writing YAML file to temporary directory: {e}")


    print(f"Successfully created updated YAML at: {temp_yaml_path}")
    print(f"Added RDFModel inheritance to {len(class_names) - len(missing_classes)} classes")
    print(f"Updated config_dict['schema_path'] to: {link_dict['schema_path']}")

    return link_dict

def generate_from_linkml(link_dict):
    print(f"Generating from {link_dict['schema_path']}...")
    generator = CustomPydanticGenerator(
        schema=link_dict['schema_path'],
        imports=link_dict['imports'],
        black=True,
        template_dir="./templates/sempyro",
        mergeimports=False
    )

    with open(link_dict['output_path'], 'w') as fname:
        fname.write(generator.serialize())
    print("Done.")

link_dicts = [
    {
        "schema_path": "./linkml-definitions/dcat/dcat_resource.yaml",
        "imports": imports_dcat_resource,
        "output_path": "./sempyro_classes/dcat/dcat_resource.py",
        "add_rdf_model_to_class": ['DCATResource']
    },
    {
        "schema_path": "./linkml-definitions/dcat/dcat_dataset.yaml",
        "imports": imports_dcat_dataset,
        "output_path": "./sempyro_classes/dcat/dcat_dataset.py"
    },
    {
        "schema_path": "./linkml-definitions/vcard/dcat_vcard.yaml",
        "imports": imports_dcat_dataset,
        "output_path": "./sempyro_classes/vcard/dcat_vcard.py",
        "add_rdf_model_to_class": ['DCATVCard']
    },
    {
        "schema_path": "./linkml-definitions/foaf/foaf_agent.yaml",
        "imports": imports_dcat_dataset,
        "output_path": "./sempyro_classes/foaf/foaf_agent.py",
        "add_rdf_model_to_class": ['FOAFAgent']
    },
]

for link_dict in link_dicts:
    link_dict = add_rdf_model_to_yaml(link_dict)
    generate_from_linkml(link_dict)
    remove_unwanted_classes(Path(link_dict['output_path']), Path(link_dict['schema_path']))
    if os.path.exists("./linkml-definitions/temp"):
        shutil.rmtree("./linkml-definitions/temp")


# split_objects = generator.generate_split("./linkml-definitions/dcat/dcat_dataset.yaml",
#                                          output_path="./output.py",
#                                          template_dir="./templates/sempyro",
#                                          black=True,
#                                          imports=imports_dcat_dataset,
#                                          split_pattern=".{{ schema.name }}")
