# Test Suite for metadata-automation

This directory contains tests for the metadata-automation project.

## Test Structure

```
tests/
├── conftest.py                         # Shared pytest fixtures
├── test_cli_shaclplay.py              # Integration tests for shaclplay CLI command
├── test_cli_shacl_from_shaclplay.py   # Integration tests for shacl_from_shaclplay CLI command
├── test_cli_sempyro.py                # Integration tests for sempyro CLI command
├── test_cli_error_handling.py         # Shared CLI error-handling tests across commands
├── test_cli_additional_coverage.py    # Additional edge-case coverage for CLI commands
├── test_coverage_units.py             # Unit tests for utility and helper modules
├── create_test_files.py               # Script to regenerate test input files
├── test_input/                         # Static test input files
│   ├── test_metadata.xlsx             # Standard test with single class
│   ├── bad_metadata.xlsx              # Invalid structure (missing prefixes sheet)
│   ├── multi_metadata.xlsx            # Test with multiple classes
│   ├── invalid_shaclplay.xlsx         # Invalid SHACLPlay structure
│   └── imports.yaml                    # Test-only SeMPyRO imports
└── test_expected/                      # Expected output files for regression testing
    ├── default/                        # Standard output expectations
    │   ├── SHACL-testclass.xlsx      # Expected SHACLPlay Excel output
    │   └── hri/
    │       └── hri-testclass.ttl     # Expected SHACL Turtle output
    ├── namespace_override/             # Output with custom namespace
    │   └── SHACL-testclass.xlsx      # Expected SHACLPlay Excel output
    ├── multi/                          # Multi-class output expectations
    │   ├── SHACL-classa.xlsx         # Expected SHACLPlay Excel output for ClassA
    │   ├── SHACL-classb.xlsx         # Expected SHACLPlay Excel output for ClassB
    │   └── hri/
    │       ├── hri-classa.ttl        # Expected SHACL Turtle output for ClassA
    │       └── hri-classb.ttl        # Expected SHACL Turtle output for ClassB
    ├── linkml/                         # SeMPyRO LinkML expectations
    │   └── hri/
    └── sempyro_classes/                # SeMPyRO class expectations
        └── hri/
```

## Running Tests

The tests are automatically run with coverage from the `pytest-cov` package (see [pyproject.toml](../pyproject.toml#L44))

Run all tests:
```bash
uv run pytest tests/
```

Run specific test file:
```bash
uv run pytest tests/test_cli_shaclplay.py -v
uv run pytest tests/test_cli_shacl_from_shaclplay.py -v
uv run pytest tests/test_cli_sempyro.py -v
```

Run specific test:
```bash
uv run pytest tests/test_cli_shaclplay.py::TestShaclplayCLI::test_shaclplay_success -v
```

## Test Overview

### SHACLPlay CLI tests (`test_cli_shaclplay.py`)

Tests for the `shaclplay` CLI command that converts metadata Excel files to SHACLPlay format.
They cover successful generation (including namespace overrides and multi-class inputs) as well as
basic error handling for missing input files and invalid Excel structures.

### SHACL from SHACLPlay CLI tests (`test_cli_shacl_from_shaclplay.py`)

Tests for the `shacl_from_shaclplay` CLI command that converts SHACLPlay Excel to SHACL Turtle.
These tests validate successful generation, processing multiple input files, preservation of
namespaces and file naming, and error handling for missing input, missing sheets, and subprocess failures.

### SeMPyRO CLI tests (`test_cli_sempyro.py`)

Integration tests for the `sempyro` CLI command that generates LinkML schemas and SeMPyRO
Pydantic classes from metadata. They exercise namespace handling (explicit and auto-detected),
the four-step generation process, expected file outputs, and behavior with multiple classes
and missing/invalid inputs.

### CLI error and edge-case tests (`test_cli_error_handling.py`, `test_cli_additional_coverage.py`)

These files provide focused coverage of error handling and edge cases across all CLI commands.
They cover missing templates/JARs, invalid or empty sheets, missing required columns, namespace
extraction failures, imports/LinkML generation errors, subprocess failures (including stderr/stdout
reporting), and ruff formatting warnings.

### Unit tests for utility modules (`test_coverage_units.py`)

Unit tests target specific utility functions and edge cases in modules such as the LinkML creator,
SeMPyRO helpers, SHACLPlay converter and utilities, and vocabulary mappings. They focus on YAML
loading and mutation, import parsing, validation logic application, RDF model wiring, SHACLPlay
Excel creation, property conversion branches, and custom Pydantic generation.

**Total:** 69 tests (see pytest output)

## Test Fixtures

Shared fixtures are defined in `conftest.py`:

- `tests_dir` - Path to the tests directory
- `test_input_dir` - Path to static test input files
- `test_expected_dir` - Path to static expected output files
- `template_file` - Path to SHACLPlay template (optional)
- `xls2rdf_jar` - Path to xls2rdf JAR (optional)

## Output Comparison Strategy

### Excel Files (SHACLPlay)
- Compared using pandas DataFrames
- Ignores dynamic timestamp columns (ignored during comparison)
- Verifies sheet structure and content equivalence

### Turtle Files (SHACL)
- Compared using semantic equivalence with comment/whitespace normalization
- Uses custom `normalize_turtle()` function to handle variations
- Ensures turtle syntax and structure match without being brittle about formatting

### Python Files (SeMPyRO)
- Compared as full file text against expected outputs
- Uses test-only imports from `tests/test_input/imports.yaml`
- Validates LinkML and SeMPyRO class outputs

## Creating/Updating Test Files

### Regenerate Test Input Files
The `create_test_files.py` script regenerates test input Excel files:
```bash
uv run python tests/create_test_files.py
```

### Regenerate Expected SHACLPlay Output
To update expected SHACLPlay Excel outputs after modifying the conversion logic:
```bash
# Generate default expected output
uv run metadata-automation shaclplay --input-excel tests/test_input/test_metadata.xlsx --output-path tests/test_expected/default

# Generate namespace override expected output
uv run metadata-automation shaclplay --input-excel tests/test_input/test_metadata.xlsx --output-path tests/test_expected/namespace_override --namespace custom

# Generate multi-class expected output
uv run metadata-automation shaclplay --input-excel tests/test_input/multi_metadata.xlsx --output-path tests/test_expected/multi
```

### Regenerate Expected SHACL Turtle Output
To update expected SHACL Turtle outputs after modifying the conversion logic:
```bash
# Generate from default SHACLPlay files
uv run metadata-automation shacl-from-shaclplay --input-path tests/test_expected/default --output-path tests/test_expected/default_ttl

# Generate from multi-class SHACLPlay files
uv run metadata-automation shacl-from-shaclplay --input-path tests/test_expected/multi --output-path tests/test_expected/multi_ttl

# Move generated files to expected locations
mv tests/test_expected/default_ttl/hri/* tests/test_expected/default/hri/
mv tests/test_expected/multi_ttl/hri/* tests/test_expected/multi/hri/
rm -rf tests/test_expected/default_ttl tests/test_expected/multi_ttl
```

## Test Design Principles

- **Static Fixtures**: Test inputs are pre-generated and stored to ensure reproducible results
- **Expected Outputs**: Comparison files allow regression testing and detect unintended changes
- **Semantic Comparison**: Turtle files are compared semantically, not syntactically, to avoid brittle tests
- **Excel Comparison**: DataFrames are compared ignoring dynamic columns like timestamps
- **Java Requirement**: SHACL tests require Java installed (tests fail if unavailable, don't skip)
- **Error Coverage**: Tests cover missing files, invalid structures, and missing directories
- **Logical Organization**: Test files organized by input type → expected output type

## Notes
- SHACL Turtle generation requires Java and the xls2rdf JAR file to be available
- Tests use temporary directories (`tmp_path`) for output to avoid polluting the repository
- All tests are independent and can run in any order
- Coverage reports currently show around 90%+ coverage for the core CLI and converter modules

