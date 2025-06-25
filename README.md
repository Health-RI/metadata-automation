# LinkML to Sempyro Pipeline

This repository contains a pipeline for generating Sempyro Pydantic classes from LinkML schema definitions, specifically designed for DCAT and related semantic web vocabularies.

## Repository Structure

```
.
├── linkml-definitions/          # LinkML YAML schema definitions, organized by namespace
│   ├── dcat/
│   │   ├── dcat_resource.yaml
│   │   └── dcat_dataset.yaml
│   └── ...
├── sempyro_classes/            # Generated Python files with Sempyro Pydantic classes
│   ├── dcat/
│   │   ├── dcat_resource.py
│   │   └── dcat_dataset.py
│   └── ...
├── templates/sempyro/          # Custom Jinja templates for Pydantic generation
├── gen_sempyro.py             # Generator script with custom import definitions
└── README.md
```

## Usage

### Generating Sempyro Classes

Run the generation script to convert LinkML definitions to Sempyro Pydantic classes:

```bash
python gen_sempyro.py
```

This will:
1. Read LinkML YAML files from `./linkml-definitions/`
2. Apply custom Jinja templates from `./templates/sempyro/`
3. Generate Python classes in `./sempyro_classes/`

### Custom Templates

The Pydantic generation uses adapted Jinja templates located in `./templates/sempyro/`. These templates are necessary to:
- Handle Sempyro-specific class generation
- Customize output formatting

## Known Issues and Limitations

### 1. Default Python Imports
- **Issue**: During Pydantic code generation, LinkML adds default Python imports alongside our custom imports defined in `gen_sempyro.py`
- **Impact**: Results in superfluous (but harmless) import statements in generated files
- **Status**: Unclear how to completely eliminate these default imports
- **Workaround**: The extra imports don't break functionality, just create visual clutter

### 2. Enum Generation Problems
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

### 3. Enum Inheritance
- **Issue**: When creating inherited classes (e.g., `DCATDataset` inheriting from `DCATResource`), all enums from parent schemas get duplicated in the child class
- **Impact**: Results in redundant enum definitions in generated Python files
- **Status**: No clean solution identified yet

## Next Steps

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

4. **Organization and Structure**
   - Design optimal folder structure for LinkML YAMLs across namespaces
   - Implement automated organization of generated Python files
   - Create namespace-aware generation that respects package hierarchies

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
