"""Script to generate test input and expected output files."""

from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

# Create test_input directory
test_input_dir = Path(__file__).parent / "test_input"
test_input_dir.mkdir(exist_ok=True)

# 1. Create test_metadata.xlsx - standard test file with all sheets
excel_path = test_input_dir / "test_metadata.xlsx"
prefixes_df = pd.DataFrame(
    {
        "prefix": ["hri", "dct", "dcat", "custom", "dash", "sh"],
        "namespace": [
            "http://data.health-ri.nl/core/p2#",
            "http://purl.org/dc/terms/",
            "https://www.w3.org/ns/dcat#",
            "http://example.com/custom#",
            "http://datashapes.org/dash#",
            "http://www.w3.org/ns/shacl#",
        ],
    }
)

classes_df = pd.DataFrame(
    {
        "sheet_name": ["TestClass"],
        "class_URI": ["hri:TestClass"],
        "SHACL_target_ontology_name": ["dcat:TestClass"],
        "description": ["A test class"],
        "SeMPyRO_annotations_ontology": ["http://example.com/ontology"],
        "SeMPyRO_annotations_IRI": ["http://example.com/TestClass"],
        "SeMPyRO_add_rdf_model": ["TRUE"],
    }
)

testclass_df = pd.DataFrame(
    {
        "Property label": ["title", "description"],
        "Definition": ["The title", "The description"],
        "Property URI": ["dct:title", "dct:description"],
        "Controlled vocabulary (if applicable)": ["", ""],
        "Usage note": ["Provide a unique title", "Provide a brief description"],
        "Range": ["rdfs:Literal", "rdfs:Literal"],
        "Cardinality": ["1..n", "1..n"],
        "SHACL_dash:viewer": ["dash:LiteralViewer", "dash:LiteralViewer"],
        "SHACL_dash:editor": ["dash:TextFieldEditor", "dash:TextFieldEditor"],
        "SHACL_sh:node": ["", ""],
        "SHACL_sh:uniqueLang": ["TRUE", "TRUE"],
        "SHACL_pattern": ["", ""],
        "SHACL_default_value": ["", ""],
        "SeMPyRO_rdf_term": ["DCTERMS.title", "DCTERMS.description"],
        "SeMPyRO_rdf_type": ["rdfs_literal", "rdfs_literal"],
        "SeMPyRO_range": ["LiteralField, str", "LiteralField, str"],
    }
)

with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
    prefixes_df.to_excel(writer, sheet_name="prefixes", index=False)
    classes_df.to_excel(writer, sheet_name="classes", index=False)
    testclass_df.to_excel(writer, sheet_name="TestClass", index=False)

print(f"✓ Created {excel_path}")

# 2. Create bad_metadata.xlsx - Excel without prefixes sheet
bad_excel_path = test_input_dir / "bad_metadata.xlsx"
bad_classes_df = pd.DataFrame(
    {"sheet_name": ["TestClass"], "class_URI": ["hri:TestClass"], "SHACL_target_ontology_name": ["dcat:TestClass"]}
)

with pd.ExcelWriter(bad_excel_path, engine="openpyxl") as writer:
    bad_classes_df.to_excel(writer, sheet_name="classes", index=False)

print(f"✓ Created {bad_excel_path}")

# 3. Create multi_metadata.xlsx - Excel with multiple classes
multi_excel_path = test_input_dir / "multi_metadata.xlsx"
multi_prefixes_df = prefixes_df

multi_classes_df = pd.DataFrame(
    {
        "sheet_name": ["ClassA", "ClassB"],
        "class_URI": ["hri:ClassA", "hri:ClassB"],
        "SHACL_target_ontology_name": ["dcat:ClassA", "dcat:ClassB"],
        "description": ["Class A", "Class B"],
        "SeMPyRO_annotations_ontology": ["http://example.com/ontology", "http://example.com/ontology"],
        "SeMPyRO_annotations_IRI": ["http://example.com/ClassA", "http://example.com/ClassB"],
        "SeMPyRO_add_rdf_model": ["TRUE", "TRUE"],
    }
)

multi_props_df = pd.DataFrame(
    {
        "Property label": ["title"],
        "Definition": ["The title"],
        "Property URI": ["dct:title"],
        "Controlled vocabulary (if applicable)": [""],
        "Usage note": [""],
        "Range": ["rdfs:Literal"],
        "Cardinality": ["1"],
        "SHACL_dash:viewer": ["dash:LiteralViewer"],
        "SHACL_dash:editor": ["dash:TextFieldEditor"],
        "SHACL_sh:node": [""],
        "SHACL_sh:uniqueLang": ["TRUE"],
        "SHACL_pattern": [""],
        "SHACL_default_value": [""],
        "SeMPyRO_rdf_term": ["DCTERMS.title"],
        "SeMPyRO_rdf_type": ["rdfs_literal"],
        "SeMPyRO_range": ["LiteralField, str"],
    }
)

with pd.ExcelWriter(multi_excel_path, engine="openpyxl") as writer:
    multi_prefixes_df.to_excel(writer, sheet_name="prefixes", index=False)
    multi_classes_df.to_excel(writer, sheet_name="classes", index=False)
    multi_props_df.to_excel(writer, sheet_name="ClassA", index=False)
    multi_props_df.to_excel(writer, sheet_name="ClassB", index=False)

print(f"✓ Created {multi_excel_path}")

# 4. Create invalid_shaclplay.xlsx - Invalid SHACL Excel with wrong sheet name
invalid_shaclplay_path = test_input_dir / "invalid_shaclplay.xlsx"
invalid_df = pd.DataFrame({"data": ["invalid sheet name"]})

with pd.ExcelWriter(invalid_shaclplay_path, engine="openpyxl") as writer:
    invalid_df.to_excel(writer, sheet_name="WrongSheet", index=False)

print(f"✓ Created {invalid_shaclplay_path}")

# 5. Create imports.yaml - SeMPyRO imports configuration
imports_yaml_path = test_input_dir / "imports.yaml"
imports_yaml_content = """hri-TestClass: |
    import logging
    from typing import Union

    from pydantic import ConfigDict, Field
    from rdflib.namespace import DCTERMS
    from sempyro import LiteralField, RDFModel

hri-ClassA: |
    import logging
    from typing import Union

    from pydantic import ConfigDict, Field
    from rdflib.namespace import DCTERMS
    from sempyro import LiteralField, RDFModel

hri-ClassB: |
    import logging
    from typing import Union

    from pydantic import ConfigDict, Field
    from rdflib.namespace import DCTERMS
    from sempyro import LiteralField, RDFModel
"""

with open(imports_yaml_path, "w") as f:
    f.write(imports_yaml_content)

print(f"✓ Created {imports_yaml_path}")


# 6. Create plain_metadata.xlsx - an enriched model Excel with the pipeline additions stripped
def strip_pipeline_additions(src: Path, dst: Path) -> None:
    """Drop the prefixes, classes and Resource sheets and all SHACL_*/SeMPyRO_* columns."""
    wb = load_workbook(src)
    for name in ("prefixes", "classes", "Resource"):
        if name in wb.sheetnames:
            del wb[name]
    for ws in wb.worksheets:
        pipeline_cols = [
            c.column for c in ws[1] if isinstance(c.value, str) and c.value.startswith(("SHACL_", "SeMPyRO_"))
        ]
        for col in reversed(pipeline_cols):
            ws.delete_cols(col)
    wb.save(dst)


enriched_path = Path(__file__).parent.parent / "inputs" / "Health-RI_v2.1.0.xlsx"
plain_path = test_input_dir / "plain_metadata.xlsx"
if enriched_path.exists():
    strip_pipeline_additions(enriched_path, plain_path)
    print(f"✓ Created {plain_path}")
else:
    print(f"! Skipped {plain_path}: {enriched_path} not found")

# 7. Create plain_small.xlsx - small plain model Excel for end-to-end preparation tests
plain_small_path = test_input_dir / "plain_small.xlsx"
plain_columns = [
    "Property label",
    "Definition",
    "Property URI",
    "Controlled vocabulary (if applicable)",
    "Usage note",
    "Range",
    "Cardinality",
]
plain_sheets = {
    "Catalog": [
        ("title", "Catalog title", "dct:title", "", "", "rdfs:Literal", "1..n"),
        ("dataset", "Datasets in the catalog", "dcat:dataset", "", "", "dcat:Dataset", "1..n"),
        ("publisher", "Publisher", "dct:publisher", "", "", "foaf:Agent", "1"),
        ("license", "License", "dct:license", "", "", "dct:LicenseDocument", "0..1"),
        ("modification date", "Last modified", "dct:modified", "", "", "xsd:dateTime", "0..1"),
        ("description", "Catalog description", "dct:description", "", "", "rdfs:Literal", "0..n"),
    ],
    "Dataset": [
        ("title", "Dataset title", "dct:title", "", "", "rdfs:Literal", "1..n"),
        ("distribution", "Distributions", "dcat:distribution", "", "", "dcat:Distribution", "1..n"),
        ("creator", "Creator", "dct:creator", "", "", "foaf:Agent", "1..n"),
        ("theme", "Theme", "dcat:theme", "", "", "skos:Concept (IRI)", "1..n"),
        ("release date", "Issued", "dct:issued", "", "", "xsd:dateTime", "0..1"),
    ],
    "Agent": [
        ("name", "Agent name", "foaf:name", "", "", "rdfs:Literal", "1..n"),
        ("type", "Agent type", "dct:type", "", "", "skos:Concept", "0..1"),
    ],
    "Distribution": [
        ("title", "Distribution title", "dct:title", "", "", "rdfs:Literal", "0..n"),
        ("access URL", "Access URL", "dcat:accessURL", "", "", "rdfs:Resource (IRI)", "1..n"),
    ],
}

with pd.ExcelWriter(plain_small_path, engine="openpyxl") as writer:
    pd.DataFrame({"Info": ["Plain test model"]}).to_excel(writer, sheet_name="Info", index=False)
    for sheet, rows in plain_sheets.items():
        pd.DataFrame(rows, columns=plain_columns).to_excel(writer, sheet_name=sheet, index=False)

print(f"✓ Created {plain_small_path}")

print("\n✓ All test input files created successfully!")
