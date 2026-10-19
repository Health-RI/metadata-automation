from pathlib import Path

import pandas as pd
import pytest
import yaml

from metadata_automation.cli import fdp_properties


@pytest.fixture
def model_excel(tmp_path):
    """Workbook where Dataset -> Agent -> Kind via sh:node, plus an unreferenced class."""
    path = tmp_path / "model.xlsx"
    sheets = {
        "classes": pd.DataFrame(
            {
                "sheet_name": ["Dataset", "DatasetSeries", "Agent", "Kind", "Unused"],
                "class_URI": ["hri:Dataset", "hri:DatasetSeries", "hri:Agent", "hri:Kind", "hri:Unused"],
            }
        ),
        "Dataset": pd.DataFrame({"SHACL_sh:node": ["hri:AgentShape", None, "hri:AgentShape"]}),
        "DatasetSeries": pd.DataFrame({"SHACL_sh:node": [None]}),
        "Agent": pd.DataFrame({"SHACL_sh:node": ["hrishapes:KindShape"]}),
        "Kind": pd.DataFrame({"Property URI": ["vcard:fn"]}),
        "Unused": pd.DataFrame({"SHACL_sh:node": [None]}),
    }
    with pd.ExcelWriter(path) as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return path


@pytest.fixture
def base_yaml(tmp_path):
    path = tmp_path / "base.yaml"
    path.write_text(
        yaml.safe_dump({"schemas": {}, "schemasToPublish": ["Dataset", "Dataset Series"], "schemaVersion": "1.0.0"})
    )
    return path


def _run(runner, model_excel, base_yaml, output, *args):
    return runner.invoke(fdp_properties, ["-i", str(model_excel), "-b", str(base_yaml), "-o", str(output), *args])


def test_schemas_follow_sh_node_transitively(runner, model_excel, base_yaml, tmp_path):
    output = tmp_path / "Properties.yaml"
    result = _run(runner, model_excel, base_yaml, output)

    assert result.exit_code == 0, result.output
    properties = yaml.safe_load(output.read_text())
    assert properties["schemas"] == {
        "Dataset": ["hri-dataset.ttl", "hri-agent.ttl", "hri-kind.ttl"],
        "Dataset Series": ["hri-datasetseries.ttl"],
    }
    assert properties["schemaVersion"] == "1.0.0"


def test_namespace_and_version_override(runner, model_excel, base_yaml, tmp_path):
    output = tmp_path / "Properties.yaml"
    result = _run(runner, model_excel, base_yaml, output, "--namespace", "ns", "--schema-version", "2.1.0")

    assert result.exit_code == 0, result.output
    properties = yaml.safe_load(output.read_text())
    assert properties["schemas"]["Dataset Series"] == ["ns-datasetseries.ttl"]
    assert properties["schemaVersion"] == "2.1.0"


def test_unknown_schema_fails(runner, model_excel, tmp_path):
    base = tmp_path / "base.yaml"
    base.write_text(yaml.safe_dump({"schemasToPublish": ["Catalog"]}))
    result = _run(runner, model_excel, base, tmp_path / "out.yaml")

    assert result.exit_code == 1
    assert "Catalog" in result.output


def test_default_base_matches_health_ri_model(runner, tmp_path):
    excel = Path(__file__).resolve().parent.parent / "inputs" / "HealthRI_v2.0.2.xlsx"
    output = tmp_path / "Properties.yaml"
    result = runner.invoke(fdp_properties, ["-i", str(excel), "-o", str(output)])

    assert result.exit_code == 0, result.output
    schemas = yaml.safe_load(output.read_text())["schemas"]
    assert list(schemas) == ["Resource", "Catalog", "Dataset", "Dataset Series", "Distribution", "Data Service"]
    assert schemas["Catalog"][0] == "hri-catalogue.ttl"
