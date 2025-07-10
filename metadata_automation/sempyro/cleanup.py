import ast
from typing import Set, List, Tuple
from pathlib import Path

import yaml

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
