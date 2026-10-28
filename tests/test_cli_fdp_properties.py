import pandas as pd
import pytest
import yaml

from metadata_automation.cli import fdp_properties

CLASSES = pd.DataFrame(
    {
        "sheet_name": ["Resource", "Dataset", "DatasetSeries", "Agent", "Kind", "Unused"],
        "class_URI": ["hri:Resource", "hri:Dataset", "hri:DatasetSeries", "hri:Agent", "hri:Kind", "hri:Unused"],
        "SHACL_target_ontology_name": [
            "dcat:Resource",
            "dcat:Dataset",
            "dcat:DatasetSeries",
            "foaf:Agent",
            "vcard:Kind",
            "ex:Unused",
        ],
        "SHACL_independent_class": [True, True, True, False, None, False],
    }
)


def _write(path, sheets):
    with pd.ExcelWriter(path) as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name, index=False)
    return path


@pytest.fixture
def sheets():
    """Dataset -> Agent -> Kind via sh:node; Dataset links to DatasetSeries as an FDP resource."""
    return {
        "prefixes": pd.DataFrame({"prefix": ["dcat"], "namespace": ["http://www.w3.org/ns/dcat#"]}),
        "classes": CLASSES,
        "Resource": pd.DataFrame({"Property URI": ["dct:title"]}),
        "Dataset": pd.DataFrame(
            {
                "Property URI": ["dct:creator", "dcat:inSeries", "dct:publisher"],
                "Range": ["foaf:Agent", "dcat:DatasetSeries (IRI)", "foaf:Agent"],
                # sh:node to the independent DatasetSeries must not pull in its file.
                "SHACL_sh:node": ["hri:AgentShape", "hri:DatasetSeriesShape", "hri:AgentShape"],
                "FDP_resources": [None, "Dataset Series", None],
            }
        ),
        "DatasetSeries": pd.DataFrame({"SHACL_sh:node": [None]}),
        "Agent": pd.DataFrame({"SHACL_sh:node": ["hrishapes:KindShape"]}),
        "Kind": pd.DataFrame({"Property URI": ["vcard:fn"]}),
        "Unused": pd.DataFrame({"SHACL_sh:node": [None]}),
    }


@pytest.fixture
def base_yaml(tmp_path):
    path = tmp_path / "base.yaml"
    path.write_text(yaml.safe_dump({"schemas": {}, "parentChild": {"Resource": ["Dataset"]}, "schemaVersion": "1.0.0"}))
    return path


def _run(runner, excel, base_yaml, output, *args):
    return runner.invoke(fdp_properties, ["-i", str(excel), "-b", str(base_yaml), "-o", str(output), *args])


def test_generates_derived_sections(runner, sheets, base_yaml, tmp_path):
    output = tmp_path / "Properties.yaml"
    result = _run(runner, _write(tmp_path / "model.xlsx", sheets), base_yaml, output)

    assert result.exit_code == 0, result.output
    properties = yaml.safe_load(output.read_text())
    assert properties["schemasToPublish"] == ["Resource", "Dataset", "Dataset Series"]
    assert properties["schemas"] == {
        "Resource": ["hri-resource.ttl"],
        "Dataset": ["hri-dataset.ttl", "hri-agent.ttl", "hri-kind.ttl"],
        "Dataset Series": ["hri-datasetseries.ttl"],
    }
    assert properties["resources"] == {
        "Dataset Series": {
            "parentResource": "Dataset",
            "parentRelationIri": "http://www.w3.org/ns/dcat#inSeries",
            "schema": "Dataset Series",
        }
    }
    assert properties["parentChild"] == {"Resource": ["Dataset"]}
    assert properties["schemaVersion"] == "1.0.0"


def test_parents_are_published_first(runner, sheets, tmp_path):
    base = tmp_path / "base.yaml"
    base.write_text(yaml.safe_dump({"parentChild": {"Dataset Series": ["Dataset"]}}))
    output = tmp_path / "Properties.yaml"
    result = _run(runner, _write(tmp_path / "model.xlsx", sheets), base, output)

    assert result.exit_code == 0, result.output
    assert yaml.safe_load(output.read_text())["schemasToPublish"][0] == "Dataset Series"


def test_namespace_and_version_override(runner, sheets, base_yaml, tmp_path):
    output = tmp_path / "Properties.yaml"
    excel = _write(tmp_path / "model.xlsx", sheets)
    result = _run(runner, excel, base_yaml, output, "--namespace", "ns", "--schema-version", "2.1.0")

    assert result.exit_code == 0, result.output
    properties = yaml.safe_load(output.read_text())
    assert properties["schemas"]["Dataset Series"] == ["ns-datasetseries.ttl"]
    assert properties["schemaVersion"] == "2.1.0"


def test_missing_independent_column_fails(runner, sheets, base_yaml, tmp_path):
    sheets["classes"] = CLASSES.drop(columns="SHACL_independent_class")
    result = _run(runner, _write(tmp_path / "model.xlsx", sheets), base_yaml, tmp_path / "out.yaml")

    assert result.exit_code == 1
    assert "SHACL_independent_class" in result.output


def test_resource_to_dependent_class_fails(runner, sheets, base_yaml, tmp_path):
    sheets["Dataset"].loc[0, "FDP_resources"] = "Creator"
    result = _run(runner, _write(tmp_path / "model.xlsx", sheets), base_yaml, tmp_path / "out.yaml")

    assert result.exit_code == 1
    assert "'Agent' is not an independent class" in result.output


@pytest.mark.parametrize(
    "sheet, column",
    [("classes", "class_URI"), ("prefixes", "namespace"), ("Dataset", "Range")],
)
def test_missing_required_column_fails(runner, sheets, base_yaml, tmp_path, sheet, column):
    sheets[sheet] = sheets[sheet].drop(columns=column)
    result = _run(runner, _write(tmp_path / "model.xlsx", sheets), base_yaml, tmp_path / "out.yaml")

    assert result.exit_code == 1
    assert f"Sheet '{sheet}' is missing column(s): {column}" in result.output


def test_missing_prefixes_sheet_fails(runner, sheets, base_yaml, tmp_path):
    del sheets["prefixes"]
    result = _run(runner, _write(tmp_path / "model.xlsx", sheets), base_yaml, tmp_path / "out.yaml")

    assert result.exit_code == 1
    assert "Missing sheet(s): prefixes" in result.output


def test_class_without_sheet_fails(runner, sheets, base_yaml, tmp_path):
    del sheets["Unused"]
    result = _run(runner, _write(tmp_path / "model.xlsx", sheets), base_yaml, tmp_path / "out.yaml")

    assert result.exit_code == 1
    assert "Sheet(s) listed in classes not found: Unused" in result.output
