# Generate metadata artifacts from a single source of truth

This repository contains a pipeline for generating metadata-related artifacts, such as SHACLs and [SeMPyRO](https://github.com/Health-RI/SeMPyRO) Pydantic classes.

## Repository Structure

```
.
├── metadata_automation/            # Code for this repository; a folder per artifact type.
├── inputs/                         # Additional inputs 
├── outputs/                        # Resulting artifacts; a folder per artifact type.
└── README.md
```

## Installation

Dependencies are managed via `pyproject.toml` (and `uv.lock` when using uv).

### Option 1: Using UV (Recommended)

UV is a fast, modern Python package manager. Install the CLI globally in an isolated environment:

```bash
# Install uv (if not installed already)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install a supported Python version (3.13 shown as an example)
# Tested with Python 3.10-3.13; 3.14+ is currently blocked by older pydantic-core version used by SeMPyRo.
uv python install 3.13

# Install metadata-automation CLI
cd /path/to/metadata-automation
uv tool install . --python 3.13  # add --editable argument if editable mode is wanted
```

After installation, the CLI is available globally:

```bash
metadata-automation --help
```

### Option 2: Using pip with Virtual Environment

Use Python's built-in virtual environment with pip:

```bash
# Create a virtual environment (3.13 shown as an example)
# Tested with Python 3.10-3.13; 3.14+ is currently blocked by older pydantic-core version used by SeMPyRo.
cd /path/to/metadata-automation
python3.13 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .
```

The inheritance inspector resolves external SeMPyRO parent classes from the
installed `sempyro` package. Installing the project from `pyproject.toml` or
`requirements.txt` will install the pinned `sempyro` dependency automatically.

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

### `prepare-excel`: Preparing a plain metadata Excel

```bash
metadata-automation prepare-excel -i ./inputs/plain_model.xlsx --init
metadata-automation prepare-excel -i ./inputs/plain_model.xlsx -o ./outputs/prepared/model_prepared.xlsx
```

#### Command Options

- `-i, --input-excel`: Path to the plain metadata Excel file (required). Only modified with `--init`.
- `-o, --output-excel`: Path for the prepared Excel (default: `./outputs/prepared/{input}_prepared.xlsx`). Not allowed with `--init`.
- `-n, --namespace`: Namespace prefix used to derive empty `class_URI` values as `{namespace}:{local name of SHACL_target_ontology_name}`. Without it, `class_URI` is left empty and reported.
- `--init`: Update the input in place with the general steps only (no FDP rules).
- `--overwrite`: Replace an existing output file. Without it, an existing output is refused. Not used with `--init`.

Drawings (text boxes, shapes, images), which openpyxl drops on save, are copied back from the input. With `--init`, an input that has drawings is first copied to `{input}.bak`; an input without drawings gets no backup.

Other content openpyxl does not support is lost without warning, e.g. form controls, macros (VBA) and some data validation or conditional formatting. Keep a copy of the input when it uses these.

#### Description

Adds what `shaclplay` and `sempyro` need on top of a plain model Excel, using only information in the Excel itself.
Every sheet except `Info`, `User Guide`, `prefixes` and `classes` is a class sheet. These names are matched regardless of case, and a variant such as `Classes` is renamed.
A duplicate `sheet_name` or `SHACL_target_ontology_name` in `classes` stops the run before anything is written.

General steps (always):
- Adds the `prefixes` and `classes` sheets if missing, a `classes` row per class sheet, and all `SHACL_*` and `SeMPyRO_*` columns.
- Adds every prefix used in the workbook to `prefixes`; unknown namespaces are left empty.
- Once every class has a `SHACL_target_ontology_name`:
  - A range that is a class of the model and not suffixed `(IRI)` gets its shape (`{class_URI}Shape`) in `SHACL_sh:node`, e.g. `hri:AgentShape`; a differing value is overwritten. This needs the class's `class_URI` (filled in, or derived with `-n`); without it `SHACL_sh:node` stays empty and no DASH values are set for the range.
  - Any other range that is a prefixed name (CURIE) and not a literal (`rdfs:Literal` or an `xsd` datatype) gets `(IRI)` appended. Values without a prefix and full IRIs are left as they are; the prefix check reports values without a prefix and full IRIs that could be a CURIE.
  - `SHACL_dash:viewer` / `SHACL_dash:editor` are derived (first matching rule). Empty cells are filled; a differing existing value is kept and reported.
    - Range ends in `(IRI)`, is an outside class (not a model class or `rdfs:Resource`) and has a `Controlled vocabulary (if applicable)` value (text or hyperlink) with a known mapping (see 'Controlled Vocabulary Mappings'): `dash:LabelViewer` / `dash:URIEditor`. A class sheet without this column is reported.
    - Any other range ending in `(IRI)`: `dash:URIViewer` / `dash:URIEditor`
    - `SHACL_sh:node` filled: `dash:DetailsViewer` / `dash:BlankNodeEditor`
    - `xsd:dateTime`: `dash:LiteralViewer` / `dash:DateTimePickerEditor`
    - `dct:description` with a literal range: `dash:LiteralViewer` / `dash:TextAreaEditor`
    - Any other `xsd:*` or `rdfs:Literal`: `dash:LiteralViewer` / `dash:TextFieldEditor`

FDP steps (without `--init`; the result is written to a new file):
- Adds the `Resource` sheet if missing.
- The range rules replace the general ones:
  - A range that is the target of a class with `SHACL_independent_class` `TRUE` (a class that exists on its own in the FDP) gets `(IRI)` appended, a non-required cardinality, e.g. `1..n` → `0..n`, an empty `SHACL_sh:node`, and `dash:URIViewer` / `dash:URIEditor` (overwriting other values).
  - A range that is the target of a class with `SHACL_independent_class` `FALSE` (or not set) gets its shape in `SHACL_sh:node` when that class has a `class_URI`; a differing value is overwritten. A range ending in `(IRI)` is reported.
- Reports an independent class without a `dct:title` property.

It then prints a report with:
- the changes made;
- issues, e.g. a dependent class referenced as `(IRI)` or a differing DASH value;
- a prefix check: used prefixes without a namespace, duplicate or aliased prefixes, case variants, full IRIs that could be CURIEs, and values with no prefix or stray whitespace in `Property URI` and `Range`;
- every sheet, column and row that still has to be filled in by hand, plus a summary of empty optional columns (including `SHACL_independent_class`).

Changes, issues and prefix findings on a class sheet row also show its `Property URI`, e.g. `Catalog / Cardinality / row 3 (dcat:dataset)`.

#### `SHACL_independent_class`

Set per class in the `classes` sheet. It decides how other classes refer to this class in the FDP, and is only used without `--init`:
- `TRUE`: the class is a resource of its own in the FDP, e.g. `dcat:Dataset` or `dcat:Distribution`. A property with this class as range points to it by IRI: the range gets `(IRI)`, the property becomes optional, `SHACL_sh:node` is emptied, and the URI viewer and editor are used. The class needs a `dct:title` property; a missing one is reported.
- `FALSE`: the class only exists inside another resource, e.g. `foaf:Agent` as a publisher. Its properties are nested through `SHACL_sh:node` and edited in place.
- Empty: treated as `FALSE`. The report lists the column among the empty optional cells, so check it for every class before the FDP run.

`TRUE`/`FALSE`, `yes`/`no` and `1`/`0` are accepted (any case); an empty or any other value is treated as `FALSE`. The value of every class, and how it is treated, is listed under issues so it can be checked.

**Workflow:**
1. Run `prepare-excel --init` on the plain Excel.
2. Fill in `class_URI`, `SHACL_target_ontology_name` and, for FDP, `SHACL_independent_class` in the `classes` sheet.
3. Run `prepare-excel --init` again to set `SHACL_sh:node` and DASH values.
4. For the FDP, run `prepare-excel` without `--init` to write a new Excel with the FDP rules applied.
5. Fill in the remaining reported cells, then run `shaclplay` and `sempyro`.

### `shaclplay`: Generating SHACLPlay Excel files

```bash
metadata-automation shaclplay -i ./inputs/source_excel.xlsx -o ./outputs/shaclplay/default
```

#### Command Options

- `-i, --input-excel`: Path to source metadata Excel file (required)
- `-o, --output-path`: Output directory for SHACLPlay Excel files (default: `./outputs/shaclplay/default`)
- `-n, --namespace`: Namespace prefix to override all class and property namespaces (optional)

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
  - `class_URI`: Name of the class with the corresponding namespace, formatted `{namespace}:{class_name}`, e.g., `hri:Dataset`.
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

A cell matches a mapping via its Excel hyperlink, its full text, or any URL contained in the text
(scheme and trailing slash are ignored). Additional vocabulary mappings can be added by extending the `VOCAB_MAPPINGS` dictionary.

**Template:**\
For the generation of SHACLPlay Excel files, an empty template file is needed. In this repository there is one in 
`./inputs/shacls/shaclplay-template.xlsx`.

#### Outputs

SHACLPlay Excel files are generated in the specified output directory.

### `shacl_from_shaclplay`: Converting SHACLPlay Excel to SHACL Turtle files

```bash
metadata-automation shacl-from-shaclplay -i ./outputs/shaclplay/default -o ./outputs/shacl_shapes -e ./inputs/Health-RI_v2.1.0.xlsx
```

#### Command Options

- `-i, --input-path`: Path to directory containing SHACLPlay Excel files (required)
- `-o, --output-path`: Output directory for SHACL Turtle files (default: `./outputs/shacl_shapes`)
- `-e, --input-excel`: Metadata model Excel the SHACLPlay files were generated from; defines the FDP schemas (required)

#### Description

This command converts the SHACLPlay Excel files to SHACL Turtle format using the xls2rdf tool. 
It converts each to Turtle format using `xls2rdf-app-3.2.1-onejar.jar`, (https://github.com/sparna-git/xls2rdf) provided in `./inputs/shacls/`.

**Requirements:**
- Java must be installed and available in your PATH

#### Inputs

**SHACLPlay Excel files:**\
The command processes all SHACLPlay Excel files from the input directory. These files are typically generated by the `shaclplay` command.

**Namespace detection:**\
The namespace is auto-detected from each Excel file's NodeShapes sheet and used to construct output file paths:
`{output-path}/PiecesShape/{namespace}-{classname}.ttl`

**Model Excel:**\
The FDP schemas are the classes with `SHACL_independent_class` `TRUE`, as in `fdp-properties`. Without that column (or no `TRUE` values) the FDP shapes are skipped.

#### Outputs

The command writes the same output as FairDataPointSchemaTool's `template` command:

| Folder | Content |
|---|---|
| `{output-path}/PiecesShape/` | One SHACL per class: `{namespace}-{classname}.ttl` |
| `{output-path}/FairDataPointShape/` | One SHACL per FDP schema (`{Schema}.ttl`, spaces removed), merged with the classes it reaches through `SHACL_sh:node` (independent classes skipped) |
| `{output-path}/ValidationShape/` | The SHACLs used by the FDP schemas (all SHACLs without FDP schemas), merged into `{namespace}-shapes.ttl`, or `Validation-shapes.ttl` when the classes have different namespaces |

### `fdp-properties`: Generating a FairDataPointSchemaTool Properties.yaml

```bash
metadata-automation fdp-properties -i ./inputs/Health-RI_v2.1.0.xlsx --schema-version 2.1.0
```

#### Command Options

- `-i, --input-excel`: Path to the metadata model Excel file (required)
- `-b, --base-properties`: Properties.yaml supplying the non-derived settings (default: `./inputs/fdp/Properties-base.yaml`)
- `-o, --output-path`: Output file (default: `./outputs/fdp/Properties.yaml`)
- `--namespace`: Prefix of the SHACL file names (default: the `class_URI` prefix); use the same value as for `shaclplay`
- `--schema-version`: Override `schemaVersion` from the base file

#### Description

Builds a [FairDataPointSchemaTool](https://github.com/Health-RI/FairDataPointSchemaTool) Properties.yaml. Derived from the Excel:

- `schemasToPublish`: classes with `SHACL_independent_class` `TRUE` in the `classes` sheet, named after their `class_URI` (`hri:DatasetSeries` → `Dataset Series`). Parents listed in the base `parentChild` come first.
- `schemas`: per schema its own SHACL file plus the files of all classes it reaches through `SHACL_sh:node`, skipping independent classes (separate schemas). File names follow the `shacl-from-shaclplay` output (`{namespace}-{sheet_name}.ttl`).
- `resources`: every property with a name in the `FDP_resources` column of a class sheet becomes a child resource. The sheet's class is `parentResource`, the expanded `Property URI` is `parentRelationIri` and the `Range` class is `schema`. Both classes must be independent.

Everything else (`parentChild`, `inputDir`, directories) comes from the base file. Point `inputDir` to where the SHACL files are hosted.

### `sempyro`: Generating SeMPyRo Classes

```bash
metadata-automation sempyro -i ./inputs/source_excel.xlsx -n hri
```

#### Command Options

- `-i, --input-excel`: Path to source metadata Excel file (required)
- `-n, --namespace`: Namespace prefix (optional)
  - If not provided, automatically detected from the Excel file's `class_URI` column in the `classes` sheet
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
  - `class_URI`: Name of the class with the corresponding namespace, formatted `{namespace}:{class_name}`, e.g., `hri:Dataset`.
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
This name is constructed by taking the `class_URI`, e.g., 'dcat:Dataset' following the `{namespace}:{class_name}` format, 
and creating the Pydantic class name by making the `namespace` all caps and concatenating it with the `class_name`, i.e.,
`{namespace.upper()}{class_name}`, resulting in `DCATDataset`.

**Imports:**\
The generated SeMPyRO Pydantic classes are in the form of Python code, for which imports should be defined. 
This can be done in `./inputs/sempyro/imports.yaml`. The imports are automatically linked to classes based on the naming convention `{namespace}-{ClassName}`, e.g., `hri-Dataset`.

#### Outputs

Python files are generated in `./outputs/sempyro_classes/{namespace}/` and automatically formatted with ruff.
LinkML schemas are generated in `./outputs/linkml/{namespace}/`.

### `inspect_inheritance`: Analyzing SeMPyRO Class Inheritance Overlap

```bash
metadata-automation inspect-inheritance -i ./outputs/sempyro_classes/hri/ [-o report.txt]
```

#### Command Options

- `-i, --input-dir`: Directory containing generated SeMPyRO Python class files (required)
- `-o, --output-file`: Optional path to write the report to a text file

#### Description

This command analyzes generated SeMPyRO Pydantic classes to identify properties that are redefined in subclasses but already exist in ancestor classes. This is useful for cleaning up generated code by removing redundant property definitions that are already inherited.

The inspector:
- Parses each generated class file using AST (Abstract Syntax Tree) and does not import or execute the analyzed class files
- Walks the full ancestor chain to find where each overlapping field originates
- Compares field metadata (`description`, `rdf_term`, `rdf_type`) between child and parent
- Reports whether overlapping fields are identical or differ (and how they differ)
- Can inspect class files without `sempyro` installed, but resolving external parent classes is more complete when `sempyro` is installed

#### Outputs

The report is printed to stdout in a human-readable format. Example output:

```
================================================================================
HRIDataset  (inherits from: DCATDataset → DCATResource → RDFModel)

Overlapping properties: 12 of 47 direct fields are also defined in an ancestor class

  dct_title
    found in    : DCATDataset  (1 level up)
    description : SAME    → A name given to the resource.
    rdf_term    : SAME    → DCTERMS.title
    rdf_type    : SAME    → rdfs_literal
    [IDENTICAL – can be removed]

  dcat_contact_point
    found in    : DCATResource  (2 levels up)
    rdf_type    : DIFFERENT
                   child  : uri
                  parent : rdfs_literal
    [DIFFERS – review before removing]

  Summary: 8 identical, 4 different
```

**Notes:**
- **IDENTICAL**: The field definition is identical in both child and parent. It can safely be removed from the subclass.
- **DIFFERS**: The field exists in both but with different metadata. Review before removing to ensure the child definition is not intentionally specialized.
- **found in**: Shows which ancestor class originally defines the field and how many inheritance levels up it is (1 = direct parent, 2 = grandparent, etc.)

When using `--output-file`, the same report is also written to the specified file.

## GitHub Action

The repository doubles as a composite GitHub Action that generates the SHACL Turtle files from the source Excel file
(`shaclplay` followed by `shacl-from-shaclplay`). It does not commit anything; callers decide whether to compare or commit the result.

```yaml
- uses: Health-RI/metadata-automation@v1.1.0
  with:
    excel-path: Documents/Health-RI_v2.1.0-for-FDP.xlsx
    output-path: Formalisation(shacl)/Core/PiecesShape
    fdp-output-path: Formalisation(shacl)/Core/FairDataPointShape
    validation-output-path: Formalisation(shacl)/Core/ValidationShape
    validation-file-name: HRI-Datamodel-shapes.ttl
    namespace: hrishapes
```

| Input | Required | Description |
|---|---|---|
| `excel-path` | yes | Source metadata Excel file. |
| `output-path` | yes | Folder for the per-class SHACLs, written flat as `{namespace}-{class}.ttl`. Existing `{namespace}-*.ttl` files in it are replaced. |
| `fdp-output-path` | no | Folder for the FDP SHACLs (one file per independent class). Existing `*.ttl` files in it are replaced. When given and no FDP SHACLs are generated (no class has `SHACL_independent_class` `TRUE`), the action fails. Without it the FDP SHACLs are not written. |
| `validation-output-path` | no | Folder for the joined validation SHACL. Existing `*.ttl` files in it are replaced. Without it the validation SHACL is not written. |
| `validation-file-name` | no | Name of the validation SHACL in `validation-output-path` (default: the generated `{namespace}-shapes.ttl`). |
| `namespace` | no | Overrides the namespace given in the Excel file (like `-n` on the CLI). |

The Excel file is also passed to `shacl-from-shaclplay` as `-e`, so the FDP and validation SHACLs follow its `SHACL_independent_class` column.
Always reference an exact release (e.g. `@v1.1.0`) so the generated output stays reproducible.

### Releasing

Releases follow [semantic versioning](https://semver.org/). Bump `version` in `pyproject.toml` (and the
`metadata-automation` entry in `uv.lock`), merge, then push a matching tag, e.g. `git tag v1.0.1 && git push origin v1.0.1`.
The `Release` workflow checks that the tag equals the package version and creates the GitHub release.

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
uv run pytest tests/test_cli_inheritance_inspector.py -v
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

(None currently planned.)

