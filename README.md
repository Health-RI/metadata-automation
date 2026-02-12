# Generate metadata artifacts from a single source of truth

This repository contains a pipeline for generating metadata-related artifacts, such as SHACLs and [SeMPyRO](github.com/Health-RI/SeMPyRO) Pydantic classes.

## Repository Structure

```
.
├── metadata_automation/            # Code for this repository; a folder per artifact type.
├── inputs/                         # Additional inputs 
├── outputs/                        # Resulting artifacts; a folder per artifact type.
└── README.md
```

## Installation

### Option 1: Using UV (Recommended)

UV is a fast, modern Python package manager. Install the CLI globally in an isolated environment:

```bash
# Install uv (if not installed already)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install metadata-automation CLI
cd /path/to/metadata-automation
uv tool install . # add --editable argument if editable mode is wanted
```

After installation, the CLI is available globally:

```bash
metadata-automation --help
```

### Option 2: Using pip with Virtual Environment

Use Python's built-in virtual environment with pip:

```bash
# Create a virtual environment
cd /path/to/metadata-automation
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .
```

After installation, the CLI is available in the activated virtual environment:
```bash
source .venv/bin/activate
metadata-automation --help
```

## Usage

View all available commands:

```bash
metadata-automation --help
```

The core source of information is the input Excel file. An example for the Health-RI v2 metadata model is given in `./inputs`.
This is based on **v2.0.2** of the Health-RI metadata model.
This is a duplicate of the Excel file from the [Health-RI metadata Github repository](https://github.com/Health-RI/health-ri-metadata/blob/v2.0.0/Documents/Metadata_CoreGenericHealth_v2.xlsx) 
with additional columns.
Other inputs can also be required per command. See the sections below for more information on that.

In the Excel file there are three types of sheets:
- prefixes: Links prefixes with namespaces
- classes: Links the sheets of the separate classes to class-level metadata
  - `sheet_name`: Name of the sheet corresponding to the class.
  - `description`: Description of the class.
- sheet per class, e.g., 'Dataset', 'Agent' etc.: Contains properties of the classes.
  - `Property label`: Name of the property.
  - `Definition`: Definition of the property.
  - `Property URI`: URI of the property, e.g., `dct:title`.
  - `Usage note`: Description of how to interpret the property.
  - `Range`: Data type of the property
  - `Cardinality`: Cardinality of the property, e.g., `1..n`.

### `shaclplay`: Generating SHACLPlay Excel files

```bash
metadata-automation shaclplay -i ./inputs/source_excel.xlsx -o ./outputs/shaclplay/default
```

#### Command Options

- `-i, --input-excel`: Path to source metadata Excel file (required)
- `-t, --template-path`: Path to SHACLPlay template Excel file (default: `./inputs/shacls/shaclplay-template.xlsx`)
- `-o, --output-path`: Output directory for SHACLPlay Excel files (default: `./outputs/shaclplay/default`)

#### Description

This script converts the Health-RI metadata Excel file directly to SHACLPlay-compatible Excel format without going through LinkML. The generated files can be imported into [SHACLPlay](https://shacl-play.sparna.fr/) for visual SHACL shape editing and validation.

The conversion process:
- Reads prefixes from the 'prefixes' sheet and converts them to SHACLPlay format
- Reads class configuration from the 'classes' sheet in the input Excel
- For each class, converts properties to SHACLPlay PropertyShapes format
- Handles cardinality parsing (e.g., "0..n" → minCount=0, maxCount=unbounded)
- Converts SHACL ranges to appropriate sh:nodeKind or sh:datatype
- Infers sh:node references for complex object types
- Maps controlled vocabulary URLs to sh:in value lists (where configured)
- Generates properly formatted 3-sheet Excel files (prefixes, NodeShapes, PropertyShapes)

#### Inputs
**Source Excel file**:\
In the Excel file, besides the general columns, information is needed in the following columns:
- `classes` sheet: 
  - `class_uri`: Name of the class with the corresponding namespace, formatted `{namespace}:{class_name}`, e.g., `hri:Dataset`.
  - `SHACL_target_ontology_name`: Name of the target class of this model, formatted `{namespace}:{class_name}`, e.g., `dcat:Dataset`.
- Sheet per class:
  - `Controlled vocabulary (if applicable)`: Terms in this column can be mapped to vocabularies using the system described in 'Controlled Vocabulary Mappings' below.
  - `Range`: If the range is another class, not `rdfs:Literal` or an `xsd` datatype, but an IRI should be supplied instead of the complete contents of that class, provide `(IRI)` at the end of the range, e.g., `dpv:LegalBasis (IRI)`.
  - `SHACL_sh:node`: If the range is another class that should be integrated, e.g., when using `hri:Agent` for `dct:creator`, use this column to provide the node shape. In this case `hri:AgentShape`.
  - `SHACL_dash:viewer` and `SHACL_dash:editor`: Entries for `dash:viewer` and `dash:editor` for UI customization in SHACLPlay.
  - `SHACL_pattern`: Regular expressions pattern that the property value should adhere to.
  - `SHACL_default_value`: Default value for the property.

To allow for a drop-in replacement of the current Health-RI SHACLs, properties for hri:Dataset are based on the 'Property label',
for all other classes they are based on 'Property URI'.

**Controlled Vocabulary Mappings:**\
The converter includes a mapping system for controlled vocabularies in `metadata_automation/shaclplay/vocab_mappings.py`. Currently mapped:
- `access-right` → `( eu:PUBLIC eu:RESTRICTED eu:NON_PUBLIC )`

Additional vocabulary mappings can be added by extending the `VOCAB_MAPPINGS` dictionary.

**Template:**\
For the generation of SHACLPlay Excel files, an empty template file is needed. In this repository there is one in 
`./inputs/shacls/shaclplay-template.xlsx`.

#### Outputs

SHACLPlay Excel files are generated in the specified output directory.

### `shacl_from_shaclplay`: Converting SHACLPlay Excel to SHACL Turtle files

```bash
metadata-automation shacl_from_shaclplay -i ./outputs/shaclplay/default -o ./outputs/shacl_shapes
```

#### Command Options

- `-i, --input-path`: Path to directory containing SHACLPlay Excel files (required)
- `-o, --output-path`: Output directory for SHACL Turtle files (default: `./outputs/shacl_shapes`)
- `-n, --namespace`: Namespace prefix for output files (optional, auto-detected from Excel if not provided)

#### Description

This command converts the SHACLPlay Excel files to SHACL Turtle format using the xls2rdf tool. 
It converts each to Turtle format using `xls2rdf-app-3.2.1-onejar.jar`, (https://github.com/sparna-git/xls2rdf) provided in `./inputs/shacls/`.

**Requirements:**
- Java must be installed and available in your PATH

#### Inputs

**SHACLPlay Excel files:**\
The command processes all SHACLPlay Excel files from the input directory. These files are typically generated by the `shaclplay` command.

**Namespace parameter:**\
The namespace is used to determine the output file naming and can be:
- **Auto-detected** from the Excel file's NodeShapes sheet (if not provided with `-n`)
- **Explicitly specified** with the `-n, --namespace` option to override auto-detection
- Used to construct output file paths: `{output-path}/{namespace}/{namespace}-{classname}.ttl`

#### Outputs

The resulting SHACLs are written to `{output-path}/{namespace}/{namespace}-{classname}.ttl`.

### `sempyro`: Generating SeMPyRo Classes

```bash
metadata-automation sempyro -i ./inputs/source_excel.xlsx -n hri
```

#### Command Options

- `-i, --input-excel`: Path to source metadata Excel file (required)
- `-n, --namespace`: Namespace prefix (optional)
  - If not provided, automatically detected from the Excel file's `class_uri` column in the `classes` sheet
  - Used to organize output classes: `{namespace}-{ClassName}`, e.g., `hri-Dataset`
  - Used for LinkML schema and SeMPyRO class organization
- `--linkml-output-path`: Output directory for LinkML schemas (default: `./outputs/linkml`)
- `--sempyro-output-path`: Output directory for SeMPyRO Pydantic classes (default: `./outputs/sempyro_classes`)
- `--imports-path`: Path to imports configuration YAML file (default: `./inputs/sempyro/imports.yaml`)

#### Description

This command converts the initial Excel file to LinkML YAML files, and subsequently to SeMPyRO Pydantic classes.

The Pydantic generation uses adapted Jinja templates located in `./metadata_automation/sempyro/templates/`. These templates are necessary to:
- Handle SeMPyRO-specific class generation
- Customize output formatting

#### Inputs

**Source Excel file:**\
In the Excel file, besides the general columns, information is needed in the following columns:
- `classes` sheet:
    - `class_uri`: Name of the class with the corresponding namespace, formatted `{namespace}:{class_name}`, e.g., `hri:Dataset`.
    - `SeMPyRO_inherits_from`: Class from which this class inherits from. 
    - `SeMPyRO_annotations_ontology`: URL of the ontology.
    - `SeMPyRO_annotations_IRI`: IRI to the class. This can be a URL or link to a Python variable. 
    - `SeMPyRO_add_rdf_model`: If this model does not inherit from another class, it should inherit the `RDFModel` class. In that case, mark this row as `TRUE`.
- Sheet per class:
    - `SeMPyRO_range`: Comma separated list of the types in the range of this property. 

Any namespace objects and Enums are not created in this automation pipeline. If you want to use them, they should 
be defined separately and imported using the imports, explained below.

**SeMPyRO types:**\
All types in the `SeMPyRO_range` column should be known in the list in `./inputs/sempyro/sempyro_types.yaml`. 

**Validation logic:**\
If any validators should be included in the resulting SeMPyRO Pydantic classes, add them in `./inputs/sempyro/validation_logic.yaml`.
These code snippets will be linked to the corresponding classes on the class name used in the final Pydantic class. 
This name is constructed by taking the `class_uri`, e.g., 'dcat:Dataset' following the `{namespace}:{class_name}` format, 
and creating the Pydantic class name by making the `namespace` all caps and concatenating it with the `class_name`, i.e.,
`{namespace.upper()}{class_name}`, resulting in `DCATDataset`.

**Imports:**\
The generated SeMPyRO Pydantic classes are in the form of Python code, for which imports should be defined. 
This can be done in `./inputs/sempyro/imports.yaml`. The imports are automatically linked to classes based on the naming convention `{namespace}-{ClassName}`, e.g., `hri-Dataset`.

#### Outputs

Python files are generated in `./outputs/sempyro_classes/{namespace}/` and automatically formatted with ruff.
LinkML schemas are generated in `./outputs/linkml/{namespace}/`.

## Testing

The repository includes comprehensive integration and unit tests for all CLI commands and utility modules. Tests use pre-generated input files in `tests/test_input/` and compare outputs against expected results in `tests/test_expected/` to ensure regression testing.

Run all tests:
```bash
uv run pytest tests/
```

Run specific test files:
```bash
uv run pytest tests/test_cli_shaclplay.py -v
uv run pytest tests/test_cli_sempyro.py -v
```

**Note:** SHACL Turtle generation tests require Java to be installed.

**Regenerating test files:**
- Test inputs: `uv run python tests/create_test_files.py`
- Expected outputs: 
  First run the code below and after check if the files in the `tests/test_expected` directory are correct
  ```bash
  metadata-automation shaclplay -i tests/test_input/test_metadata.xlsx -o tests/test_expected/default/
  
  metadata-automation shaclplay -i tests/test_input/test_metadata.xlsx -o tests/test_expected/namespace_override/ --namespace custom
  
  metadata-automation shaclplay -i tests/test_input/multi_metadata.xlsx -o tests/test_expected/multi/
  
  metadata-automation shacl-from-shaclplay -i tests/test_expected/default/ -o tests/test_expected/default/
  
  metadata-automation shacl-from-shaclplay -i tests/test_expected/multi/ -o tests/test_expected/multi/
  
  metadata-automation sempyro -i tests/test_input/test_metadata.xlsx --namespace hri --linkml-output-path tests/test_expected/linkml/ --sempyro-output-path tests/test_expected/sempyro_classes/ --imports-path tests/test_input/imports.yaml
  
  metadata-automation sempyro -i tests/test_input/multi_metadata.xlsx --namespace hri --linkml-output-path tests/test_expected/linkml/ --sempyro-output-path tests/test_expected/sempyro_classes/ --imports-path tests/test_input/imports.yaml
  ```

## Future work

### SeMPyro inheritance
The generated SeMPyRO classes currently present all properties that are defined in the Excel file, 
without dealing with inheritance from superclasses. The properties of the newly generated classes should be removed 
if they already exist in a superclass, given that they have identical names and behaviour.

