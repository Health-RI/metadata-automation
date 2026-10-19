"""Generate a FairDataPointSchemaTool Properties.yaml from the metadata model Excel.

Derived from the Excel:

- ``schemasToPublish``: classes with ``SHACL_independent_class`` TRUE, parents
  from ``parentChild`` first;
- ``schemas``: per schema its own SHACL file plus the files of every class it
  reaches through ``SHACL_sh:node``;
- ``resources``: properties with an ``FDP_resources`` name, linking the sheet's
  class (parent) to the range class (child) through the property.

All other settings come from a base Properties.yaml.
"""

import re
from pathlib import Path

import pandas as pd
import yaml

from metadata_automation.excel_prep.prefix_check import expand
from metadata_automation.excel_prep.workbook import parse_bool

NODE_COLUMN = "SHACL_sh:node"
INDEPENDENT_COLUMN = "SHACL_independent_class"
RESOURCES_COLUMN = "FDP_resources"


def _local_name(curie: str) -> str:
    return str(curie).strip().split(":")[-1]


def schema_name(class_uri: str) -> str:
    """FDP schema name for a class, e.g. ``hri:DatasetSeries`` -> ``Dataset Series``."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", _local_name(class_uri))


class Model:
    """Classes, sheets and prefixes of the metadata model Excel."""

    def __init__(self, excel_path: Path):
        # object dtype keeps TRUE/FALSE as booleans in columns with blanks.
        self.sheets = pd.read_excel(excel_path, sheet_name=None, dtype=object)
        self.classes = self.sheets["classes"].dropna(subset=["sheet_name", "class_URI"])
        self.namespaces = {
            row.prefix: row.namespace for row in self.sheets["prefixes"].dropna().itertuples() if row.prefix
        }
        self.sheet_by_class = {_local_name(row.class_URI): row.sheet_name for row in self.classes.itertuples()}
        self.schema_by_sheet = {row.sheet_name: schema_name(row.class_URI) for row in self.classes.itertuples()}
        # Ranges use either the target ontology class or the model class.
        self.schema_by_range = {
            str(row.class_URI).strip(): schema_name(row.class_URI) for row in self.classes.itertuples()
        }
        if "SHACL_target_ontology_name" in self.classes.columns:
            for row in self.classes.dropna(subset=["SHACL_target_ontology_name"]).itertuples():
                self.schema_by_range[str(row.SHACL_target_ontology_name).strip()] = schema_name(row.class_URI)

    def sheet(self, name: str) -> pd.DataFrame:
        return self.sheets.get(name, pd.DataFrame())


def independent_schemas(model: Model, parents: list[str]) -> list[str]:
    """Schema names of independent classes, with ``parents`` first (the FDP needs parents published first)."""
    if INDEPENDENT_COLUMN not in model.classes.columns:
        raise ValueError(f"Column '{INDEPENDENT_COLUMN}' not found in the classes sheet")
    names = [
        model.schema_by_sheet[row.sheet_name]
        for row in model.classes.itertuples()
        if parse_bool(getattr(row, INDEPENDENT_COLUMN))
    ]
    if not names:
        raise ValueError(f"No class has {INDEPENDENT_COLUMN} TRUE")
    return sorted(names, key=lambda name: name not in parents)


def _node_refs(sheet: pd.DataFrame, sheet_by_class: dict[str, str]) -> list[str]:
    """Sheet names referenced by ``SHACL_sh:node`` in a class sheet, in order of first use."""
    if NODE_COLUMN not in sheet.columns:
        return []
    refs = []
    for node in sheet[NODE_COLUMN].dropna():
        local = _local_name(node).removesuffix("Shape")
        if local not in sheet_by_class:
            raise ValueError(f"sh:node {node} does not match any class_URI in the classes sheet")
        if sheet_by_class[local] not in refs:
            refs.append(sheet_by_class[local])
    return refs


def build_schemas(model: Model, schema_names: list[str], namespace: str | None = None) -> dict[str, list[str]]:
    """Map each FDP schema name to its SHACL file and the files it depends on.

    sh:node refs to independent classes are skipped: those are separate schemas, referenced by IRI in the FDP.
    """
    sheet_by_schema = {schema: sheet for sheet, schema in model.schema_by_sheet.items()}
    independent = {sheet_by_schema[name] for name in schema_names}
    prefixes = {row.sheet_name: namespace or str(row.class_URI).split(":")[0] for row in model.classes.itertuples()}
    schemas = {}
    for name in schema_names:
        order = [sheet_by_schema[name]]
        for sheet_name in order:
            refs = _node_refs(model.sheet(sheet_name), model.sheet_by_class)
            order.extend(ref for ref in refs if ref not in order and ref not in independent)
        schemas[name] = [f"{prefixes[s]}-{s.lower()}.ttl" for s in order]
    return schemas


def build_resources(model: Model, schema_names: list[str]) -> dict[str, dict[str, str]]:
    """FDP child resources from properties with an ``FDP_resources`` name."""
    resources = {}
    for sheet_name, parent in model.schema_by_sheet.items():
        sheet = model.sheet(sheet_name)
        if RESOURCES_COLUMN not in sheet.columns:
            continue
        for _, values in sheet.dropna(subset=[RESOURCES_COLUMN]).iterrows():
            name = str(values[RESOURCES_COLUMN]).strip()
            prop = str(values["Property URI"]).strip()
            where = f"{sheet_name} / {prop}"
            child = model.schema_by_range.get(str(values["Range"]).replace("(IRI)", "").strip())
            if child is None:
                raise ValueError(f"{where}: range {values['Range']!r} is not a class of this model")
            for schema in (parent, child):
                if schema not in schema_names:
                    raise ValueError(f"{where}: '{schema}' is not an independent class")
            if name in resources:
                raise ValueError(f"{where}: resource '{name}' is defined twice")
            resources[name] = {
                "parentResource": parent,
                "parentRelationIri": expand(prop, model.namespaces) or prop,
                "schema": child,
            }
    return resources


def generate_properties(
    excel_path: Path,
    base_path: Path,
    output_path: Path,
    namespace: str | None = None,
    schema_version: str | None = None,
) -> dict:
    """Write a Properties.yaml with the derived sections from the Excel and the rest from the base file."""
    properties = yaml.safe_load(base_path.read_text()) or {}
    model = Model(excel_path)

    schema_names = independent_schemas(model, list(properties.get("parentChild") or {}))
    properties["schemas"] = build_schemas(model, schema_names, namespace)
    properties["resources"] = build_resources(model, schema_names)
    properties["schemasToPublish"] = schema_names
    if schema_version:
        properties["schemaVersion"] = schema_version

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("---\n" + yaml.safe_dump(properties, sort_keys=False, allow_unicode=True))
    return properties
