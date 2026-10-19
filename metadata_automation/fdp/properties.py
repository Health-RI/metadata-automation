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
REQUIRED_COLUMNS = {"classes": ["sheet_name", "class_URI"], "prefixes": ["prefix", "namespace"]}


def _require_columns(sheet: pd.DataFrame, columns: list[str], sheet_name: str) -> None:
    """Raise a ValueError naming the ``columns`` missing from ``sheet``."""
    missing = [column for column in columns if column not in sheet.columns]
    if missing:
        raise ValueError(f"Sheet '{sheet_name}' is missing column(s): {', '.join(missing)}")


def _local_name(curie: str) -> str:
    return str(curie).strip().split(":")[-1]


def schema_name(class_uri: str) -> str:
    """FDP schema name for a class, e.g. ``hri:DatasetSeries`` -> ``Dataset Series``."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", _local_name(class_uri))


class Model:
    """Classes, sheets and prefixes of the metadata model Excel."""

    def __init__(self, excel_path: Path):
        # All sheets by name, e.g. {"classes": DataFrame, "Dataset": DataFrame}; source for every lookup below.
        # object dtype keeps TRUE/FALSE as booleans in columns with blanks.
        self.sheets = pd.read_excel(excel_path, sheet_name=None, dtype=object)
        missing = [name for name in REQUIRED_COLUMNS if name not in self.sheets]
        if missing:
            raise ValueError(f"Missing sheet(s): {', '.join(missing)}")
        for name, columns in REQUIRED_COLUMNS.items():
            _require_columns(self.sheets[name], columns, name)
        # Rows of the classes sheet with a sheet and URI, e.g. (Dataset, hri:Dataset); one row per model class.
        self.classes = self.sheets["classes"].dropna(subset=["sheet_name", "class_URI"])
        # Every class needs its sheet; shaclplay generates a SHACL file per class sheet.
        missing = [name for name in self.classes.sheet_name if name not in self.sheets]
        if missing:
            raise ValueError(f"Sheet(s) listed in classes not found: {', '.join(missing)}")
        # Prefix -> namespace, e.g. {"dcat": "https://www.w3.org/ns/dcat#"}; expands CURIEs to full IRIs.
        self.namespaces = {
            row.prefix: row.namespace for row in self.sheets["prefixes"].dropna().itertuples() if row.prefix
        }
        # Class local name -> sheet, e.g. {"Catalog": "Catalogue"}; resolves sh:node refs to sheets.
        self.sheet_by_class = {_local_name(row.class_URI): row.sheet_name for row in self.classes.itertuples()}
        # Sheet -> FDP schema name, e.g. {"Catalogue": "Catalog"}; names schemas and resource parents.
        self.schema_by_sheet = {row.sheet_name: schema_name(row.class_URI) for row in self.classes.itertuples()}
        # Range -> FDP schema name, e.g. {"hri:Dataset": "Dataset", "dcat:Dataset": "Dataset"}; finds resource children.
        # Ranges use either the target ontology class or the model class.
        self.schema_by_range = {
            str(row.class_URI).strip(): schema_name(row.class_URI) for row in self.classes.itertuples()
        }
        if "SHACL_target_ontology_name" in self.classes.columns:
            for row in self.classes.dropna(subset=["SHACL_target_ontology_name"]).itertuples():
                self.schema_by_range[str(row.SHACL_target_ontology_name).strip()] = schema_name(row.class_URI)

    def sheet(self, name: str) -> pd.DataFrame:
        return self.sheets[name]


def independent_schemas(model: Model, parents: list[str]) -> list[str]:
    """Schema names of independent classes, with ``parents`` first (the FDP needs parents published first).

    Empty when the classes sheet has no ``SHACL_independent_class`` column or no class is TRUE.
    """
    if INDEPENDENT_COLUMN not in model.classes.columns:
        return []
    names = [
        model.schema_by_sheet[row.sheet_name]
        for row in model.classes.itertuples()
        if parse_bool(getattr(row, INDEPENDENT_COLUMN))
    ]
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


def schema_sheets(model: Model, schema_names: list[str]) -> dict[str, list[str]]:
    """Map each FDP schema name to its class sheet and the sheets it reaches through ``SHACL_sh:node``.

    sh:node refs to independent classes are skipped: those are separate schemas, referenced by IRI in the FDP.
    """
    # Inverse of schema_by_sheet, e.g. {"Catalog": "Catalogue"}.
    sheet_by_schema = {schema: sheet for sheet, schema in model.schema_by_sheet.items()}
    # Sheets of independent classes; these are never inlined as dependencies.
    independent = {sheet_by_schema[name] for name in schema_names}
    schemas = {}
    for name in schema_names:
        # Start with the schema's own sheet; the loop appends to it, walking sh:node refs breadth-first.
        order = [sheet_by_schema[name]]
        for sheet_name in order:
            refs = _node_refs(model.sheet(sheet_name), model.sheet_by_class)
            # Add unseen, non-independent dependencies.
            order.extend(ref for ref in refs if ref not in order and ref not in independent)
        # Schema to its sheets, e.g. "Dataset": ["Dataset", "Agent"].
        schemas[name] = order
    return schemas


def build_schemas(model: Model, schema_names: list[str], namespace: str | None = None) -> dict[str, list[str]]:
    """Map each FDP schema name to its SHACL file and the files it depends on."""
    prefixes = {row.sheet_name: namespace or str(row.class_URI).split(":")[0] for row in model.classes.itertuples()}
    return {
        name: [f"{prefixes[s]}-{s.lower()}.ttl" for s in sheets]
        for name, sheets in schema_sheets(model, schema_names).items()
    }


def build_resources(model: Model, schema_names: list[str]) -> dict[str, dict[str, str]]:
    """FDP child resources from properties with an ``FDP_resources`` name."""
    resources = {}
    # Each class sheet is a potential parent resource.
    for sheet_name, parent in model.schema_by_sheet.items():
        sheet = model.sheet(sheet_name)
        if RESOURCES_COLUMN not in sheet.columns:
            continue
        _require_columns(sheet, ["Property URI", "Range"], sheet_name)
        # Only properties with an FDP_resources name define a child resource.
        for _, values in sheet.dropna(subset=[RESOURCES_COLUMN]).iterrows():
            name = str(values[RESOURCES_COLUMN]).strip()
            prop = str(values["Property URI"]).strip()
            # Location prefix for error messages, e.g. "Catalogue / dcat:dataset".
            where = f"{sheet_name} / {prop}"
            # Child schema from the property range, e.g. "dcat:Dataset (IRI)" -> "Dataset".
            child = model.schema_by_range.get(str(values["Range"]).replace("(IRI)", "").strip())
            if child is None:
                raise ValueError(f"{where}: range {values['Range']!r} is not a class of this model")
            # Parent and child must both be published schemas.
            for schema in (parent, child):
                if schema not in schema_names:
                    raise ValueError(f"{where}: '{schema}' is not an independent class")
            # Resource names must be unique across the model.
            if name in resources:
                raise ValueError(f"{where}: resource '{name}' is defined twice")
            # e.g. "Dataset": {parentResource: Catalog, parentRelationIri: dcat:dataset expanded, schema: Dataset}.
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
    if not schema_names:
        raise ValueError(f"No class has {INDEPENDENT_COLUMN} TRUE in the classes sheet")
    properties["schemas"] = build_schemas(model, schema_names, namespace)
    properties["resources"] = build_resources(model, schema_names)
    properties["schemasToPublish"] = schema_names
    if schema_version:
        properties["schemaVersion"] = schema_version

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("---\n" + yaml.safe_dump(properties, sort_keys=False, allow_unicode=True))
    return properties
