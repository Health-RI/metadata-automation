"""Merge SHACL pieces into FairDataPoint and validation shapes.

Python port of FairDataPointSchemaTool's ``template`` command: each FDP schema
becomes one shape file, and all used pieces are merged into a single
validation shapes file.
"""

from pathlib import Path

from rdflib import Graph

from metadata_automation.fdp.properties import Model, build_schemas, independent_schemas

PIECES_DIR = "PiecesShape"
FDP_DIR = "FairDataPointShape"
VALIDATION_DIR = "ValidationShape"
VALIDATION_FILE = "HRI-Datamodel-shapes.ttl"


def merge_turtle(files: list[Path], output_path: Path) -> None:
    """Parse the Turtle files into one graph and write it to ``output_path``."""
    graph = Graph()
    for file in files:
        graph.parse(file, format="turtle")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(output_path, format="turtle")


def merge_fdp_shapes(excel_path: Path, namespace: str, pieces: dict[str, Path], output_dir: Path) -> list[Path]:
    """Write FDP and validation shapes for the independent classes in the Excel.

    ``pieces`` maps SHACL file names to their paths. Returns the written files.
    """
    model = Model(excel_path)
    schemas = build_schemas(model, independent_schemas(model, []), namespace)

    missing = sorted({f for files in schemas.values() for f in files} - pieces.keys())
    if missing:
        raise ValueError(f"SHACL files needed for the FDP schemas were not generated: {', '.join(missing)}")

    written = []
    for name, files in schemas.items():
        path = output_dir / FDP_DIR / f"{name.replace(' ', '')}.ttl"
        merge_turtle([pieces[f] for f in files], path)
        written.append(path)

    used = list(dict.fromkeys(f for files in schemas.values() for f in files))
    path = output_dir / VALIDATION_DIR / VALIDATION_FILE
    merge_turtle([pieces[f] for f in used], path)
    written.append(path)
    return written
