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

### Generating LinkML
```bash
python 0_gen_linkml.py
```
Besides the direct-to-artifact pipelines, this script generates the LinkML files designed for the SHACL generation.
The output directory is currently hardcoded to './temp-linkml'. 
The creation of LinkML is done using methods of the class `LinkMLCreator()`, in `metadata_automation/linkml/creator`.
For SHACLs the methods `build_base_class` and `build_shacl_class` are used.

### Generating SHACL shapes
```bash
python gen_shacls.py
```

The creation of LinkML is done using methods of the class `LinkMLCreator()`, in `metadata_automation/linkml/creator`.
For SHACLs the methods `build_base_class` and `build_shacl_class` are used.

If the key and/or value in a class or property/slot under 'annotations' contains ':' , it will be parsed as an URI.

The SHACLs are currently generated with all properties 'inline', which matches HealthDCAT-AP. The previous
Health-RI v2 SHACLs had the properties separately.

After generating the SHACLs with the LinkML SHACL generator, a number of corrections are made to try to match it 
with the Health-RI SHACLs or just to get it to work:
- `remove_redundant_constraints`: Removes all class stubs needed to define the range of some properties. Importing the real classes from other LinkML definitions did not work due to an overlap in properties. Removes `sh:class` and `sh:nodeKind` if `sh:node` is defined. `sh:node` is added during the creation of the LinkML when the range points to another class, e.g., `hri:Agent`.
- `fix_uri_node_kinds`: If `sh:datatype` is `xsd:anyURI`, `sh:nodeKind` is replaced with `sh:IRI`.
- `remove_ignored_properties`: By default the predicate `sh:ignoredProperties ( rdf:type )` is added on the class level; this seemed to interfere when using it in the FDP, so it is removed.
- `remove_closed_properties`: By default the predicate `sh:closed` is added on the class level. This is removed to try to get the SHACLs to match.
- `remove_anyuri_datatype`: Removes the `sh:datatype xsd:anyURI` statement from the properties. Also to get it to work in the FDP/match it to the current SHACLs.
- `remove_empty_node`: Removing the class stubs caused empty nodes to appear in the SHACLs. This step removes these. 

In the Health-RI SHACLs, for the Distribution class, there is a property `dcat:accessService`:
```
<http://data.health-ri.nl/core/p2/DistributionShape#dcat:accessService> sh:path dcat:accessService;
  sh:name "access service"@en;
  sh:maxCount 1;
  sh:class dcat:DataService .
```
This follows a different structure to the other properties. The generation of this property needs to be incorporated in the pipeline.

In the current version of the pipeline creates an empty Turtle file for the Resource class, since there are no properties defined.
To test the SHACLs, the SHACL of Health-RI is used.

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
