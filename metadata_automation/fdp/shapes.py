"""Merge SHACL pieces into FairDataPoint and validation shapes.

Python port of FairDataPointSchemaTool's ``template`` command: each FDP schema
becomes one shape file, and all used pieces are merged into a single
validation shapes file.
"""

from pathlib import Path

from rdflib import Graph

from metadata_automation.fdp.properties import Model, independent_schemas, schema_sheets

PIECES_DIR = "PiecesShape"
FDP_DIR = "FairDataPointShape"
VALIDATION_DIR = "ValidationShape"


def merge_turtle(files: list[Path], output_path: Path) -> None:
    """Parse the Turtle files into one graph and write it to ``output_path``."""
    graph = Graph()
    for file in files:
        graph.parse(file, format="turtle")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(output_path, format="turtle")


def validation_filename(namespaces: set[str]) -> str:
    """``{namespace}-shapes.ttl`` when all pieces share one namespace, else ``Validation-shapes.ttl``."""
    return f"{next(iter(namespaces))}-shapes.ttl" if len(namespaces) == 1 else "Validation-shapes.ttl"


def fdp_schema_classes(excel_path: Path) -> dict[str, list[str]]:
    """Map each FDP schema in the Excel to the class names whose SHACL pieces it merges.

    Class names are lowercased sheet names, matching the SHACLPlay file names
    (``shaclplay`` writes ``SHACL-{sheet.lower()}.xlsx``). Empty without independent classes.
    """
    model = Model(excel_path)
    return {
        name: [sheet.lower() for sheet in sheets]
        for name, sheets in schema_sheets(model, independent_schemas(model, [])).items()
    }


def missing_pieces(schemas: dict[str, list[str]], class_names: set[str]) -> list[str]:
    """Class names the FDP schemas need that are not in ``class_names`` (compared case-insensitively)."""
    available = {name.lower() for name in class_names}
    return sorted({c for classes in schemas.values() for c in classes} - available)


def merge_fdp_shapes(
    schemas: dict[str, list[str]], pieces: dict[str, Path], namespaces: set[str], output_dir: Path
) -> list[Path]:
    """Write FDP and validation shapes for the ``schemas`` from ``fdp_schema_classes``.

    ``pieces`` maps class names (SHACLPlay file name without ``SHACL-``) to their
    SHACL files. Without schemas, the FDP shapes are skipped and the validation
    shape merges all pieces. Returns the written files.
    """
    pieces = {name.lower(): path for name, path in pieces.items()}
    validation_path = output_dir / VALIDATION_DIR / validation_filename(namespaces)
    if not schemas:
        merge_turtle(list(pieces.values()), validation_path)
        return [validation_path]

    missing = missing_pieces(schemas, set(pieces))
    if missing:
        raise ValueError(f"SHACLPlay files needed for the FDP schemas were not found: {', '.join(missing)}")

    written = []
    for name, classes in schemas.items():
        path = output_dir / FDP_DIR / f"{name.replace(' ', '')}.ttl"
        merge_turtle([pieces[c] for c in classes], path)
        written.append(path)

    used = list(dict.fromkeys(c for classes in schemas.values() for c in classes))
    merge_turtle([pieces[c] for c in used], validation_path)
    written.append(validation_path)
    return written
