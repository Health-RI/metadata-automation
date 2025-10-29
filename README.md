# Generate metadata artifacts from a single source of truth

This repository contains a pipeline for generating metadata-related artifacts, such as SHACLs and [SeMPyRO](github.com/Health-RI/SeMPyRO) Pydantic classes.

## Repository Structure

```
.
├── metadata_automation/            # Code for this repository; a folder per artifact type.
├── inputs/                         # Additional inputs 
├── outputs/                        # Resulting artifacts; a folder per artifact type.
├── gen_*.py                        # Generator scripts per artifact type
└── README.md
```

## Installation and usage

To use the scripts in this repository, install the requirements:

```bash
pip install -r requirements.txt
```

After this the generator scripts can be run, for example:

```bash
python gen_shaclplay.py
```

## Usage

The core source of information is the input Excel file. An example for the Health-RI v2 metadata model is given in `./inputs`.
This is based on **v2.0.0** of the Health-RI metadata model.
This is a duplicate of the Excel file from the [Health-RI metadata Github repository](https://github.com/Health-RI/health-ri-metadata/blob/v2.0.0/Documents/Metadata_CoreGenericHealth_v2.xlsx) 
with additional columns.
Other inputs can also be required per generator script. See the sections below for more information on that.

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


### `gen_shaclplay.py`: Generating SHACLPlay Excel files
```bash
python gen_shaclplay.py
```

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

#### Inputs:
**Source Excel file**:

In the Excel file, besides the general columns, information is needed in the following columns:
- `classes` sheet: 
  - `ontology_name`: Name of the class with the corresponding namespace, formatted `{namespace}:{class_name}`, e.g., `hri:Dataset`.
  - `target_ontology_name`: Name of the target class of this model, formatted `{namespace}:{class_name}`, e.g., `dcat:Dataset`.
- Sheet per class:
  - `Controlled vocabulary (if applicable)`: Terms in this column can be mapped to vocabularies using the system described in 'Controlled Vocabulary Mappings' below.
  - `Range`: If the range is another class, not `rdfs:Literal` or an `xsd` datatype, but an IRI should be supplied instead of the complete contents of that class, provide `(IRI)` at the end of the range, e.g., `dpv:LegalBasis (IRI)`.
  - `sh:node`: If the range is another class that should be integrated, e.g., when using `hri:Agent` for `dct:creator`, use this column to provide the node shape. In this case `hri:AgentShape`.
  - `dash.viewer` and `dash.editor`: Entries for `dash:viewer` and `dash:editor` needed for 
  - `Pattern`: Regular expressions pattern that the property value should adhere to.
  - `Default value`: Default value for the property.

To allow for a drop-in replacement of the current Health-RI SHACLs, properties for hri:Dataset are based on the 'Property label',
for all other classes they are based on 'Property URI'.

**Controlled Vocabulary Mappings**:

The converter includes a mapping system for controlled vocabularies in `metadata_automation/shaclplay/vocab_mappings.py`. Currently mapped:
- `access-right` → `( eu:PUBLIC eu:RESTRICTED eu:NON_PUBLIC )`

Additional vocabulary mappings can be added by extending the `VOCAB_MAPPINGS` dictionary.

**Template**:

For the generation of SHACLPlay Excel files, an empty template file is needed. In this repository there is one in 
`./inputs/shacls/shaclplay-template.xlsx`.

#### Outputs:
This generator script produces SHACLPlay Excel files in the folder `FOLDER_NAME`, in the folder `OUTPUT_PATH` as 
defined in `gen_shaclplay.py`.

### `gen_shacls_from_shaclplay.py`: Converting SHACLPlay Excel to SHACL Turtle files

This script converts the SHACLPlay Excel files to SHACL Turtle format using the xls2rdf tool. 
It converts each to Turtle format using `xls2rdf-app-3.2.1-onejar.jar`, (https://github.com/sparna-git/xls2rdf) provided in `./inputs/shacls/`.

**Requirements:**
- Java must be installed and available in your PATH

#### Inputs:

There are no additional inputs besides the SHACLPlay Excel files provided in `SHACLPLAY_INPUT_DIR`.

#### Outputs:

The resulting SHACLs are written to `{SHACL_OUTPUT_BASE_DIR}/{namespace}/{namespace}-{classname}.ttl`.

### `gen_sempyro.py`: Generating Sempyro Classes

This generator script converts the initial Excel file to LinkML YAML files, and subsequently to SeMPyRO Pydantic classes.

The Pydantic generation uses adapted Jinja templates located in `./templates/sempyro/`. These templates are necessary to:
- Handle Sempyro-specific class generation
- Customize output formatting

#### Inputs:
**Source Excel file**:

In the Excel file, besides the general columns, information is needed in the following columns:
- `classes` sheet:
    - `ontology_name`: Name of the class with the corresponding namespace, formatted `{namespace}:{class_name}`, e.g., `hri:Dataset`.
    - `inherits_from`: Class from which this class inherits from. 
    - `annotations_ontology`: URL of the ontology.
    - `annotations_IRI`: IRI to the class. This can be a URL or link to a Python variable. 
    - `target_ontology_name`: This value will be split on the `:` sign; the first part, the namespace part, will be used for the `$prefix` variable in the SeMPyRO class, and in all caps for the `$namespace` variable.
    - `Sempyro_add_rdf_model`: If this model does not inherit from another class, it should inherit the `RDFModel` class. In that case, mark this row as `TRUE`.
- Sheet per class:
    - `Sempyro range`: Comma separated list of the types in the range of this property. 

Any namespace objects and Enums are not created in this automation pipeline. If you want to use them, they should 
be defined separately and imported using the imports, explained below.

**SeMPyRO types**:

All types in the `Sempyro range` column should be known in the list in `./inputs/sempyro/sempyro_types.yaml`. 

**Validation logic**:

If any validators should be included in the resulting SeMPyRO Pydantic classes, add them in `./inputs/sempyro/validation_logic.yaml`.
These code snippets will be linked to the corresponding classes on the class name used in the final Pydantic class. 
This name is constructed by taking the `ontology_name`, e.g., 'dcat:Dataset' following the `{namespace}:{class_name}` format, 
and creating the Pydantic class name by making the `namespace` all caps and concatenating it with the `class_name`, i.e.,
`{namespace.upper()}{class_name}`, resulting in `DCATDataset`.

**Imports**:

The generated SeMPyRO Pydantic classes are in the form of Python code, for which imports should be defined. 
This can be done in `./inputs/sempyro/imports.yaml`. These imports are linked to the classes using the list of dictionaries
`link_dicts` in `gen_sempyro.py`.

#### Outputs:
This generator script produces Python files in the path `output_path` in each of the dictionaries in `link_dicts`.

## Future work

### SeMPyro inheritance
The generated SeMPyRO classes currently present all properties that are defined in the Excel file, 
without dealing with inheritance from superclasses. The properties of the newly generated classes should be removed 
if they already exist in a superclass, given that they have identical names and behaviour.

### Command line interface
Currently the submiting input files is done through changing variables in the scripts. This is not user friendly and 
should be changed into a CLI.

### Reducing manual work
For example in `gen_sempyro.py` it is currently required to specify an input path, an imports text and an output path
per class, while they follow a specific structure. This can be simplified, resulting in less manual work.

