"""Unit tests to test utility modules."""

from pathlib import Path

import pandas as pd
import pytest
import yaml
from freezegun import freeze_time
from linkml.generators.pydanticgen.pydanticgen import SplitMode

from metadata_automation.linkml.creator import LinkMLCreator
from metadata_automation.sempyro.cleanup import remove_unwanted_classes
from metadata_automation.sempyro.sempyro_generator import CustomPydanticGenerator
from metadata_automation.sempyro.utils import (
    add_rdf_model_to_yaml,
    add_validation_logic_to_schema,
    load_yaml,
    parse_import_statements,
)
from metadata_automation.shaclplay.converter import SHACLPlayConverter
from metadata_automation.shaclplay.utils import (
    get_current_datetime_iso,
    parse_cardinality,
    slugify_property_label,
    write_shaclplay_excel,
)
from metadata_automation.shaclplay.vocab_mappings import (
    get_vocab_mapping,
    has_vocab_mapping,
)


def test_load_yaml_errors(tmp_path: Path):
    missing_path = tmp_path / "missing.yaml"
    with pytest.raises(FileNotFoundError):
        load_yaml(missing_path)

    invalid_yaml = tmp_path / "invalid.yaml"
    invalid_yaml.write_text("not: [valid", encoding="utf-8")
    with pytest.raises(yaml.YAMLError):
        load_yaml(invalid_yaml)


def test_parse_import_statements():
    imports = parse_import_statements(
        "import os\nimport numpy as np\nfrom typing import List as L, Optional\n# comment"
    )

    assert len(imports.imports) == 3
    assert imports.imports[0].module == "os"
    assert imports.imports[1].module == "numpy"
    assert imports.imports[1].alias == "np"
    assert imports.imports[2].module == "typing"
    assert imports.imports[2].objects[0].name == "List"
    assert imports.imports[2].objects[0].alias == "L"


def test_add_validation_logic_to_schema(tmp_path: Path):
    schema_path = tmp_path / "schema.yaml"
    schema_data = {"classes": {"HRIDataset": {"annotations": {"existing": "value"}}}}
    schema_path.write_text(yaml.safe_dump(schema_data), encoding="utf-8")

    add_validation_logic_to_schema({"schema_path": schema_path})

    updated = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    annotations = updated["classes"]["HRIDataset"]["annotations"]
    assert "validator_logic" in annotations


def test_add_rdf_model_to_yaml(tmp_path: Path):
    schema_path = tmp_path / "schema.yaml"
    schema_data = {
        "imports": ["linkml:types"],
        "classes": {"HRITest": {}},
    }
    schema_path.write_text(yaml.safe_dump(schema_data), encoding="utf-8")

    add_rdf_model_to_yaml(
        {
            "schema_path": schema_path,
            "add_rdf_model_to_class": ["HRITest", "MissingClass"],
        }
    )

    updated = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    assert "../rdf_model" in updated["imports"]
    assert updated["classes"]["HRITest"]["is_a"] == "RDFModel"


def test_remove_unwanted_classes(tmp_path: Path):
    yaml_path = tmp_path / "schema.yaml"
    yaml_path.write_text(yaml.safe_dump({"classes": {"KeepMe": {}}}), encoding="utf-8")

    python_path = tmp_path / "model.py"
    python_path.write_text(
        "class KeepMe:\n    pass\n\n\nclass RemoveMe:\n    pass\n",
        encoding="utf-8",
    )

    remove_unwanted_classes(python_path, yaml_path)
    contents = python_path.read_text(encoding="utf-8")
    assert "class KeepMe" in contents
    assert "class RemoveMe" not in contents


def test_linkml_creator_build_and_write(tmp_path: Path):
    creator = LinkMLCreator(tmp_path)
    creator.prefixes = {"hri": "http://example.com/"}

    class_sheet = pd.DataFrame(
        [
            {
                "Property label": "title",
                "Definition": "Title",
                "Property URI": "dct:title",
                "SeMPyRO_rdf_term": "DCTERMS.title",
                "SeMPyRO_rdf_type": "rdfs_literal",
                "Cardinality": "1..n",
                "SeMPyRO_range": "LiteralField, str",
            },
            {"Property label": "nan"},
        ]
    )

    creator.filtered_sheets = {"TestSheet": class_sheet}
    row = pd.Series(
        {
            "sheet_name": "TestSheet",
            "class_URI": "hri:TestClass",
            "SeMPyRO_inherits_from": "nan",
            "description": "Test class",
            "SeMPyRO_import_classes": "hri:Other",
            "SeMPyRO_add_rdf_model": "yes",
            "SeMPyRO_annotations_ontology": "http://example.com/ontology",
            "SeMPyRO_annotations_IRI": "http://example.com/TestClass",
        }
    )

    creator.build_base_class(row)
    creator.build_sempyro_class(row)

    linkml_id = "http://example.com/TestClass"
    class_data = creator.linkml_data[linkml_id]["data"]["classes"]["HRITestclass"]
    slot_data = creator.linkml_data[linkml_id]["data"]["slots"]["title"]

    assert "../rdf_model" in creator.linkml_data[linkml_id]["data"]["imports"]
    assert class_data["is_a"] == "RDFModel"
    assert "any_of" in slot_data

    creator.write_to_file()
    assert (tmp_path / "rdf_model.yaml").exists()
    assert (tmp_path / "sempyro_types.yaml").exists()


def test_slugify_property_label():
    assert slugify_property_label("Access Rights!") == "access-rights"
    assert slugify_property_label("Title") == "title"


def test_parse_cardinality():
    assert parse_cardinality("1") == (1, 1)
    assert parse_cardinality("0..n") == (None, None)
    assert parse_cardinality("1..n") == (1, None)
    assert parse_cardinality("0..1") == (None, 1)
    assert parse_cardinality("") == (None, None)


@freeze_time("2026-02-11 12:34:56")
def test_get_current_datetime_iso():
    result = get_current_datetime_iso()
    assert result == "2026-02-11 12:34:56"


def test_write_shaclplay_excel(tmp_path: Path):
    prefixes_df = pd.DataFrame([[None, None, None], ["PREFIX", "hri", "http://example.com/"]])
    nodeshapes_df = pd.DataFrame([[None, None], ["hri:TestShape", "Test"]])
    propertyshapes_df = pd.DataFrame([[None, None], ["hri:TestShape#title", "title"]])

    output_path = tmp_path / "shaclplay.xlsx"
    write_shaclplay_excel(prefixes_df, nodeshapes_df, propertyshapes_df, output_path)

    assert output_path.exists()
    sheets = pd.ExcelFile(output_path).sheet_names
    assert "prefixes" in sheets
    assert "NodeShapes (classes)" in sheets
    assert "PropertyShapes (properties)" in sheets


def test_vocab_mappings():
    url = "http://publications.europa.eu/resource/authority/access-right"
    mapping = get_vocab_mapping(url)
    assert mapping["editor"] == "dash:EnumSelectEditor"
    assert has_vocab_mapping(url) is True
    assert has_vocab_mapping("https://example.com/unknown") is False


def test_shaclplay_converter_branches(template_file: Path, test_input_dir: Path):
    converter = SHACLPlayConverter(template_file, test_input_dir / "test_metadata.xlsx")

    with pytest.raises(KeyError):
        converter._get_namespace_url("missing")

    nodeshapes = converter._build_nodeshapes(
        class_name="TestClass",
        class_uri="hri:TestClass",
        target_class="dcat:Dataset",
        description=None,
    )
    assert "excel template for testclass" in str(nodeshapes.iat[4, 1]).lower()

    base_row = {
        "Property label": "title",
        "Property URI": "dct:title",
        "Definition": "The title",
        "Usage note": "",
        "Cardinality": "1",
        "SHACL_sh:node": "hri:KindShape",
        "SHACL_pattern": "[A-Za-z]+",
        "Controlled vocabluary (if applicable)": "http://publications.europa.eu/resource/authority/access-right",
        "SHACL_sh:uniqueLang": "true",
        "SHACL_default_value": "default",
        "SHACL_dash:viewer": "dash:TextFieldViewer",
        "SHACL_dash:editor": "dash:TextFieldEditor",
    }

    row_iri = pd.Series({**base_row, "Range": "dcat:Dataset (IRI)"})
    iri_out = converter._convert_property_to_shaclplay(row_iri, "TestClass", "hri:TestClass", "hri")
    assert iri_out[8] == "sh:IRI"

    row_literal = pd.Series({**base_row, "Range": "rdfs:Literal"})
    literal_out = converter._convert_property_to_shaclplay(row_literal, "TestClass", "hri:TestClass", "hri")
    assert literal_out[8] == "sh:Literal"

    row_node = pd.Series({**base_row, "Range": "hri:Kind"})
    node_out = converter._convert_property_to_shaclplay(row_node, "TestClass", "hri:TestClass", "hri")
    assert "KindShape" in str(node_out[10])

    row_xsd = pd.Series(
        {
            **base_row,
            "Range": "xsd:dateTime",
            "SHACL_sh:node": "nan",
        }
    )
    xsd_out = converter._convert_property_to_shaclplay(row_xsd, "TestClass", "hri:TestClass", "hri")
    assert xsd_out[8] == "sh:Literal"
    assert xsd_out[9] == "xsd:dateTime"
    assert xsd_out[15] == "[A-Za-z]+"
    assert xsd_out[17]
    assert xsd_out[22] == "dash:TextFieldViewer"
    assert xsd_out[23] == "dash:EnumSelectEditor"


def test_custom_pydantic_generator_branches(tmp_path: Path):
    schema_path = tmp_path / "schema.yaml"
    schema_path.write_text(
        """
        id: http://example.com/schema
        name: test
        prefixes:
          ex: http://example.com/
        imports:
          - linkml:types
        classes:
          TestClass:
            class_uri: ex:TestClass
            slots:
              - name
        slots:
          name:
            range: string
        """,
        encoding="utf-8",
    )

    generator = CustomPydanticGenerator(
        schema=schema_path,
        imports=[parse_import_statements("import os")],
        split_mode=SplitMode.FULL,
        injected_classes=[],
    )

    module = generator.render()
    assert module is not None
