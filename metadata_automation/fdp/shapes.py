"""Merge SHACL pieces into FairDataPoint and validation shapes.

Python port of FairDataPointSchemaTool's ``template`` command: each schema in
Properties.yaml becomes one FDP shape file, and all used pieces are merged
into a single validation shapes file.
"""

from pathlib import Path

import yaml
from rdflib import Graph

VALIDATION_FILE = "HRI-Datamodel-shapes.ttl"


def merge_turtle(files: list[Path], output_path: Path) -> None:
    """Parse the Turtle files into one graph and write it to ``output_path``."""
    graph = Graph()
    for file in files:
        graph.parse(file, format="turtle")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(output_path, format="turtle")


def merge_fdp_shapes(properties_path: Path, pieces: dict[str, Path], output_dir: Path) -> list[Path]:
    """Write FDP and validation shapes for the schemas in Properties.yaml.

    ``pieces`` maps SHACL file names (as listed in ``schemas``) to their paths.
    Returns the written files.
    """
    properties = yaml.safe_load(properties_path.read_text()) or {}
    schemas = properties.get("schemas") or {}
    if not schemas:
        raise ValueError(f"No schemas found in {properties_path}")

    missing = sorted({f for files in schemas.values() for f in files} - pieces.keys())
    if missing:
        raise ValueError(f"SHACL files listed in {properties_path} were not generated: {', '.join(missing)}")

    fdp_dir = output_dir / properties.get("fairDataPointDir", "FairDataPointShape")
    written = []
    for name, files in schemas.items():
        path = fdp_dir / f"{name.replace(' ', '')}.ttl"
        merge_turtle([pieces[f] for f in files], path)
        written.append(path)

    used = list(dict.fromkeys(f for files in schemas.values() for f in files))
    path = output_dir / properties.get("validationDir", "ValidationShape") / VALIDATION_FILE
    merge_turtle([pieces[f] for f in used], path)
    written.append(path)
    return written
