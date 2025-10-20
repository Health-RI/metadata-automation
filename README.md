# LinkML to Metadata Pipeline

This repository contains a pipeline for generating SHACLs, UMLs and Sempyro Pydantic classes from LinkML schema definitions, specifically designed for DCAT and related semantic web vocabularies.

## Repository Structure

```
.
├── metadata_automation/            # Code for this repository
│   ├── sempyro/templates/          # Custom Jinja templates for Pydantic generation
│   │   └── ...
│   └── ...
├── linkml-definitions/             # LinkML YAML schema definitions, organized by namespace
│   ├── dcat/
│   │   ├── dcat_resource.yaml
│   │   └── dcat_dataset.yaml
│   └── ...
├── inputs/                         # Additional inputs besides the LinkML definitions
├── outputs/
│   ├── sempyro_classes/            # Generated Python files with Sempyro Pydantic classes
│   │   ├── dcat/
│   │   │   ├── dcat_resource.py
│   │   │   └── dcat_dataset.py
│   │   └── ...
│   ├── shacl_shapes/               # Generated Turtle files with SHACL shapes
│   └── ...
├── gen_sempyro.py                 # Generator script with custom import definitions
└── README.md
```

## Usage

The input Excel file is currently stored under `./inputs`. 
This is a duplicate of https://github.com/Health-RI/health-ri-metadata/blob/v2.0.0/Documents/Metadata_CoreGenericHealth_v2.xlsx with additional columns.
It can be that some columns are hidden when it is opened in Excel.

In the Excel file there are three types of sheets:
- prefixes: Links prefixes with namespaces
- classes: Links the sheets of the separate classes to class-level metadata
- sheet per class, e.g., 'Dataset', 'Agent' etc.: Contains properties of the classes.

The direct-to-artifact pipelines take this Excel, creates LinkML definitions specific for the type of artifact on the fly, and then creates the artifact.

### Generating SHACLPlay Excel files
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

Output files are written to `./outputs/shaclplay/SHACL-{classname}.xlsx`

**Controlled Vocabulary Mappings:**
The converter includes a mapping system for controlled vocabularies in `metadata_automation/shaclplay/vocab_mappings.py`. Currently mapped:
- `access-right` → `( eu:PUBLIC eu:RESTRICTED eu:NON_PUBLIC )`

Additional vocabulary mappings can be added by extending the `VOCAB_MAPPINGS` dictionary.

### Converting SHACLPlay Excel to SHACL Turtle files
```bash
python gen_shacls_from_shaclplay.py
```

This script converts the SHACLPlay Excel files to SHACL Turtle format using the xls2rdf tool. It:
- Finds all SHACLPlay Excel files in `./outputs/shaclplay/`
- Converts each to Turtle format using `xls2rdf-app-3.2.1-onejar.jar`
- Outputs SHACL files to `./outputs/shacl_shapes/{namespace}/{namespace}-{classname}.ttl`

**Requirements:**
- Java must be installed and available in your PATH
- The xls2rdf JAR file must be at `./inputs/shacls/xls2rdf-app-3.2.1-onejar.jar` (https://github.com/sparna-git/xls2rdf)

**Complete Pipeline:**
```bash
# Step 1: Generate SHACLPlay Excel files from source
python gen_shaclplay.py

# Step 2: Convert SHACLPlay Excel to SHACL Turtle
python gen_shacls_from_shaclplay.py
```

### Generating UML diagrams
```bash
gen-plantuml ./linkml-definitions/dcat/dcat_dataset.yaml --classes DCATDataset --classes DCATResource --directory ./tmp --classes FOAFAgent --classes DCATVCard
```

### Generating Sempyro Classes

Run the generation script to convert LinkML definitions to Sempyro Pydantic classes:

```bash
python gen_sempyro.py
```

This will:
1. Read LinkML YAML files from `./linkml-definitions/`
2. Adds a link to `../rdf_model` where necessary. The RDFModel class is only relevant for Sempyro, not for the SHACLs or UML.
3. Adds validation logic from `./inputs/sempyro/validation_logic.yaml` to the relevant classes.
4. Apply custom Jinja templates from `./templates/sempyro/`
5. Generate Python classes in `./sempyro_classes/`

### Custom Templates

The Pydantic generation uses adapted Jinja templates located in `./templates/sempyro/`. These templates are necessary to:
- Handle Sempyro-specific class generation
- Customize output formatting

## Known Issues & Limitations 

### Sempyro: Enum Generation Problems
- **Issue**: LinkML's Pydantic generator doesn't handle the `meaning` property correctly for enums
- **Workaround**: We misuse the `description` property to generate proper enum values
- **Example**: 
  ```yaml
  Status:
    permissible_values:
      Completed:
        meaning: ADMSStatus.Completed
        description: ADMSStatus.Completed  # Used for actual enum value
  ```

## Future Work 
- LinkML generation: Find a way to keep the single source of truth as clean as possible.
- LinkML generation: Integrate DCAT-AP and HealthDCAT-AP, either through defining it in the Single source of truth, or directly in LinkML.
- Sempyro generation: Per slot, swap 'range' with 'annotations/sempyro_range' so the right types are defined in the Sempyro classes.
- SHACL & Sempyro: Fix enums so they are compatible with the SHACLs and Sempyro
- Sempyro: Agree on a workflow to update Sempyro based on the Single source of truth.
- UML generation: Implement UML generation
- Generate CKAN properties (https://github.com/ckan/ckanext-dcat/tree/master/ckanext/dcat)
- Generate Discovery service mappings (https://github.com/GenomicDataInfrastructure/gdi-userportal-dataset-discovery-service) 
  - https://github.com/GenomicDataInfrastructure/gdi-userportal-dataset-discovery-service/pull/212 
- Generate HTML tables for Bikeshed

### Priority Items

1. **Single Source of Truth Integration**
   - Investigate generating LinkML YAMLs from our canonical data models
   - Establish automated pipeline from source models to LinkML definitions

2. **SHACL Validation**
   - Verify that SHACLs generated from these LinkML schemas match our requirements
   - Test round-trip compatibility: LinkML → SHACL → validation

### Bonus Objectives

3. **HealthDCAT-AP Integration**
   - Convert existing HealthDCAT-AP SHACL constraints to LinkML format
   - Generate Sempyro classes directly from HealthDCAT-AP specifications

## Development Notes

### Custom Import Configuration

The `gen_sempyro.py` script defines custom imports to ensure generated classes have the correct Sempyro dependencies:

```python
imports_dcat_resource = (
    Imports() +
    Import(module="sempyro", objects=[ObjectImport(name="LiteralField"), ObjectImport(name="RDFModel")]) +
    Import(module="sempyro.foaf", objects=[ObjectImport(name="Agent")]) +
    # ... more imports
)
```

### Template Customization

Templates in `./templates/sempyro/` override default LinkML behavior to:
- Use Sempyro base classes instead of standard Pydantic
- Include RDF-specific annotations
- Handle semantic web type mappings

## Contributing

When adding new LinkML definitions:

1. Place YAML files in appropriate namespace folders under `./linkml-definitions/`
2. Update `gen_sempyro.py` with any new import requirements
3. Test generation and verify output in `./sempyro_classes/`
4. Document any new issues or workarounds in this README

### Wishlist
- Generate CKAN fields (https://github.com/ckan/ckanext-dcat/tree/master/ckanext/dcat) from the LinkML definitions
- Generate OpenAPI/Discovery service specification from the LinkML definitions
