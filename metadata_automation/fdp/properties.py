"""Generate a FairDataPointSchemaTool Properties.yaml from the metadata model Excel.

Only the ``schemas`` section is derived from the Excel: each FDP schema gets
its own SHACL file plus the files of every class it reaches through
``SHACL_sh:node``. All other settings come from a base Properties.yaml.
"""

import re
from pathlib import Path

import pandas as pd
import yaml

NODE_COLUMN = "SHACL_sh:node"


def _local_name(curie: str) -> str:
    return str(curie).strip().split(":")[-1]


def schema_name(class_uri: str) -> str:
    """FDP schema name for a class, e.g. ``hri:DatasetSeries`` -> ``Dataset Series``."""
    return re.sub(r"(?<=[a-z])(?=[A-Z])", " ", _local_name(class_uri))


def _node_refs(sheet: pd.DataFrame, sheets_by_class: dict[str, str]) -> list[str]:
    """Sheet names referenced by ``SHACL_sh:node`` in a class sheet, in order of first use."""
    if NODE_COLUMN not in sheet.columns:
        return []
    refs = []
    for node in sheet[NODE_COLUMN].dropna():
        local = _local_name(node).removesuffix("Shape")
        if local not in sheets_by_class:
            raise ValueError(f"sh:node {node} does not match any class_URI in the classes sheet")
        if sheets_by_class[local] not in refs:
            refs.append(sheets_by_class[local])
    return refs


def build_schemas(excel_path: Path, schema_names: list[str], namespace: str | None = None) -> dict[str, list[str]]:
    """Map each FDP schema name to its SHACL file and the files it depends on."""
    workbook = pd.read_excel(excel_path, sheet_name=None)
    classes = workbook["classes"].dropna(subset=["sheet_name", "class_URI"])
    sheets_by_class = {_local_name(row.class_URI): row.sheet_name for row in classes.itertuples()}
    sheets_by_schema = {schema_name(row.class_URI): row.sheet_name for row in classes.itertuples()}
    prefixes = {row.sheet_name: namespace or str(row.class_URI).split(":")[0] for row in classes.itertuples()}

    schemas = {}
    for name in schema_names:
        if name not in sheets_by_schema:
            raise ValueError(f"Schema '{name}' does not match any class_URI in the classes sheet")
        order = [sheets_by_schema[name]]
        for sheet_name in order:
            refs = _node_refs(workbook.get(sheet_name, pd.DataFrame()), sheets_by_class)
            order.extend(ref for ref in refs if ref not in order)
        schemas[name] = [f"{prefixes[s]}-{s.lower()}.ttl" for s in order]
    return schemas


def generate_properties(
    excel_path: Path,
    base_path: Path,
    output_path: Path,
    namespace: str | None = None,
    schema_version: str | None = None,
) -> dict:
    """Write a Properties.yaml with ``schemas`` built from the Excel and the rest from the base file."""
    properties = yaml.safe_load(base_path.read_text()) or {}
    schema_names = properties.get("schemasToPublish") or list(properties.get("schemas") or {})
    if not schema_names:
        raise ValueError(f"No schemasToPublish found in {base_path}")

    properties["schemas"] = build_schemas(excel_path, schema_names, namespace)
    if schema_version:
        properties["schemaVersion"] = schema_version

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("---\n" + yaml.safe_dump(properties, sort_keys=False, allow_unicode=True))
    return properties
