"""Command line interface for metadata-automation.

Provides CLI commands for generating metadata artifacts from source
Excel files. Supports generation of SHACL shapes, SHACLPlay Excel files,
and SeMPyRO Pydantic classes.
"""

import subprocess
import sys
import traceback
from pathlib import Path

import click
import pandas as pd

from metadata_automation.excel_prep.apply import apply_plan as apply_plan_to_workbook
from metadata_automation.excel_prep.check import DEFAULT_HINT, format_check
from metadata_automation.excel_prep.columns import VOCAB_COLUMN
from metadata_automation.excel_prep.fdp import derive_fdp_workbook
from metadata_automation.excel_prep.plan import compute_plan, default_plan_path, read_plan, write_plan
from metadata_automation.excel_prep.preparer import prepare_workbook
from metadata_automation.fdp.properties import INDEPENDENT_COLUMN, generate_properties
from metadata_automation.fdp.shapes import FDP_DIR, PIECES_DIR, fdp_schema_classes, merge_fdp_shapes, missing_pieces
from metadata_automation.linkml.creator import LinkMLCreator
from metadata_automation.sempyro.cleanup import remove_unwanted_classes
from metadata_automation.sempyro.inheritance_inspector import format_report, inspect_file
from metadata_automation.sempyro.utils import generate_from_linkml, load_yaml
from metadata_automation.shaclplay.converter import SHACLPlayConverter
from metadata_automation.shaclplay.utils import (
    VOCAB_HYPERLINK_COLUMN,
    read_column_hyperlinks,
    write_shaclplay_excel,
)


@click.group()
def main() -> None:
    """Metadata automation pipeline CLI.

    Generate metadata artifacts (SHACL shapes, SHACLPlay Excel, Pydantic
    classes) from a single source Excel file.
    """
    pass


@main.command()
@click.option(
    "-i",
    "--input-excel",
    type=click.Path(exists=True),
    required=True,
    help="Path to source metadata Excel file.",
)
@click.option(
    "-o",
    "--output-path",
    type=click.Path(),
    default="./outputs/shaclplay/",
    help="Output directory for SHACLPlay Excel files.",
)
@click.option(
    "-n",
    "--namespace",
    type=str,
    default=None,
    help="Namespace prefix to override all class and property namespaces.",
)
def shaclplay(
    input_excel: str,
    output_path: str,
    namespace: str,
) -> None:
    """
    Generate SHACLPlay Excel files from metadata.

    Converts a metadata Excel file to SHACLPlay-compatible Excel format
    that can be imported into SHACLPlay for visual SHACL shape editing.

    \b
    The Excel file must contain:
    - A 'prefixes' sheet with prefix and namespace mappings
    - A 'classes' sheet with class configuration
    - One sheet per class with property definitions
    """
    try:
        excel_path = Path(input_excel)
        template_p = Path(__file__).parent.parent.resolve() / "inputs/shacls/shaclplay-template.xlsx"
        output_dir = Path(output_path)

        click.echo("=" * 80)
        click.echo("SHACLPlay Excel Generator")
        click.echo("=" * 80)
        click.echo()

        # Validate prerequisites before creating output directory
        click.echo("Validating prerequisites...")

        if not template_p.exists():
            click.echo(
                f"Error: SHACLPlay template not found at {template_p}",
                err=True,
            )
            exit(1)
        click.echo(f"  ✓ Template found: {template_p}")

        if not excel_path.exists():
            click.echo(f"Error: Input Excel file not found at {excel_path}", err=True)
            exit(1)
        click.echo(f"  ✓ Input Excel found: {excel_path}")

        try:
            prefixes_df = pd.read_excel(excel_path, sheet_name="prefixes")
            click.echo(f"  ✓ Prefixes sheet found with {len(prefixes_df)} entries")
        except ValueError:
            click.echo(f"Error: 'prefixes' sheet not found in {excel_path}", err=True)
            exit(1)
        except Exception as e:
            click.echo(f"Error: Failed to read prefixes sheet: {e}", err=True)
            exit(1)

        try:
            classes_df = pd.read_excel(excel_path, sheet_name="classes")
            click.echo(f"  ✓ Classes sheet found with {len(classes_df)} entries")
        except ValueError:
            click.echo(f"Error: 'classes' sheet not found in {excel_path}", err=True)
            exit(1)
        except Exception as e:
            click.echo(f"Error: Failed to read classes sheet: {e}", err=True)
            exit(1)

        if len(classes_df) == 0:
            click.echo("Error: 'classes' sheet is empty", err=True)
            exit(1)

        click.echo()

        # Now that all prerequisites are validated, create output directory
        click.echo("Initializing converter...")
        output_dir.mkdir(parents=True, exist_ok=True)

        try:
            click.echo(f"Loading template from {template_p}...")
            converter = SHACLPlayConverter(template_p, excel_path)
        except Exception as e:
            click.echo(f"Error: Failed to initialize converter: {e}", err=True)
            exit(1)

        click.echo(f"Found {len(classes_df)} classes to process")
        click.echo()

        for idx, class_row in classes_df.iterrows():
            try:
                sheet_name = class_row["sheet_name"]
                class_uri = class_row["class_URI"]
                target_class = class_row["SHACL_target_ontology_name"]
                description = class_row.get("description", None)

                if pd.isna(sheet_name):
                    click.echo(
                        f"Error: Row {idx} missing 'sheet_name' column",
                        err=True,
                    )
                    exit(1)
                if pd.isna(class_uri):
                    click.echo(
                        f"Error: Row {idx} missing 'class_URI' column",
                        err=True,
                    )
                    exit(1)
                if pd.isna(target_class):
                    click.echo(
                        f"Error: Row {idx} missing 'SHACL_target_ontology_name' column",
                        err=True,
                    )
                    exit(1)

                if pd.isna(description):
                    description = None

                # Override namespace if provided (only for class_uri)
                if namespace:
                    class_name_only = class_uri.split(":")[-1]
                    class_uri = f"{namespace}:{class_name_only}"

                click.echo(f"Processing {sheet_name} class...")
                click.echo(f"  Ontology: {class_uri}")
                click.echo(f"  Target: {target_class}")

                try:
                    class_df = pd.read_excel(excel_path, sheet_name=sheet_name)
                except ValueError:
                    click.echo(
                        f"Error: Sheet '{sheet_name}' not found in {excel_path}",
                        err=True,
                    )
                    exit(1)
                except Exception as e:
                    click.echo(
                        f"Error: Failed to read sheet '{sheet_name}': {e}",
                        err=True,
                    )
                    exit(1)

                click.echo(f"  Loaded {len(class_df)} properties")

                # Hyperlink targets let vocab mapping match cells that show a label instead of a URL
                class_df[VOCAB_HYPERLINK_COLUMN] = read_column_hyperlinks(
                    excel_path, sheet_name, VOCAB_COLUMN, len(class_df)
                )

                # Extract class name from class_uri
                # (e.g., "hri:Dataset" -> "Dataset")
                class_name = class_uri.split(":")[-1]

                # Convert to SHACLPlay format
                (
                    nodeshapes_df,
                    propertyshapes_df,
                ) = converter.convert_class_sheet(
                    class_sheet_df=class_df,
                    class_name=class_name,
                    class_uri=class_uri,
                    target_class=target_class,
                    description=description,
                    namespace_override=namespace,
                )

                # Get prefixes
                prefixes_df = converter.get_prefixes_dataframe()

                # Write to output file
                output_file = output_dir / f"SHACL-{sheet_name.lower()}.xlsx"
                write_shaclplay_excel(
                    prefixes_df=prefixes_df,
                    nodeshapes_df=nodeshapes_df,
                    propertyshapes_df=propertyshapes_df,
                    output_path=output_file,
                )

                click.echo(f"  ✓ Generated {output_file}")
                click.echo()

            except SystemExit:
                raise
            except Exception as e:
                click.echo(
                    f"  ✗ Unexpected error processing class at row {idx}: {e}",
                    err=True,
                )
                traceback.print_exc()
                exit(1)

        click.echo("=" * 80)
        click.echo("Conversion complete!")
        click.echo(f"Output files written to {output_dir}")
        click.echo("=" * 80)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if click.get_current_context().obj:
            traceback.print_exc()
        exit(1)


@main.command()
@click.option(
    "-i",
    "--input-path",
    type=click.Path(exists=True),
    required=True,
    help="Path to directory containing SHACLPlay Excel files.",
)
@click.option(
    "-o",
    "--output-path",
    type=click.Path(),
    default="./outputs/shacl_shapes",
    help="Output directory for SHACL Turtle files.",
)
@click.option(
    "-e",
    "--input-excel",
    type=click.Path(exists=True, dir_okay=False),
    help="Metadata model Excel the SHACLPlay files were generated from; defines the FDP schemas.",
)
def shacl_from_shaclplay(
    input_path: str,
    output_path: str,
    input_excel: str | None,
) -> None:
    """Generate SHACL Turtle files from SHACLPlay Excel files.

    \b
    Converts SHACLPlay Excel files to SHACL Turtle format using the xls2rdf
    tool. Requires Java to be installed and available in PATH. Writes:
      PiecesShape/         {namespace}-{class}.ttl, one file per class
      FairDataPointShape/  one file per independent class, merged with the classes it uses
                           (skipped without SHACL_independent_class)
      ValidationShape/     the files used by the FDP schemas (all files without FDP schemas),
                           merged into {namespace}-shapes.ttl, or Validation-shapes.ttl
                           when the classes have different namespaces
    """
    try:
        shaclplay_dir = Path(input_path)
        output_dir = Path(output_path)
        jar_path = Path(__file__).parent.parent.resolve() / "inputs/shacls/xls2rdf-app-3.2.1-onejar.jar"

        click.echo("=" * 80)
        click.echo("SHACL Turtle Generator from SHACLPlay Excel")
        click.echo("=" * 80)
        click.echo()

        # Check if xls2rdf JAR exists
        if not jar_path.exists():
            click.echo(f"Error: xls2rdf JAR not found at {jar_path}", err=True)
            exit(1)

        # Find all SHACLPlay Excel files
        excel_files = list(shaclplay_dir.glob("SHACL-*.xlsx"))

        if not excel_files:
            click.echo(
                f"No SHACLPlay Excel files found in {shaclplay_dir}",
                err=True,
            )
            exit(1)

        click.echo(f"Found {len(excel_files)} SHACLPlay Excel files to convert")
        click.echo()

        # Read the model Excel before converting, so a bad -e file fails before any output is written.
        schemas = fdp_schema_classes(Path(input_excel)) if input_excel else {}
        if not schemas:
            click.echo(
                f"Warning: No FDP schemas found (no class has {INDEPENDENT_COLUMN} TRUE), skipping {FDP_DIR}",
                err=True,
            )
        missing = missing_pieces(schemas, {f.stem.removeprefix("SHACL-") for f in excel_files})
        if missing:
            click.echo(
                f"Error: SHACLPlay files needed for the FDP schemas were not found: {', '.join(missing)}",
                err=True,
            )
            exit(1)

        # Process each file
        output_file_dir = output_dir / PIECES_DIR
        pieces: dict[str, Path] = {}
        namespaces: set[str] = set()
        for excel_file in excel_files:
            try:
                # Extract namespace from the Excel file
                try:
                    df = pd.read_excel(
                        excel_file,
                        sheet_name="NodeShapes (classes)",
                        header=None,
                    )
                except ValueError:
                    click.echo(
                        f"Error: 'NodeShapes (classes)' sheet not found in {excel_file.name}",
                        err=True,
                    )
                    exit(1)
                except Exception as e:
                    click.echo(
                        f"Error: Failed to read {excel_file.name}: {e}",
                        err=True,
                    )
                    exit(1)

                try:
                    nodeshape_uri = df.iloc[13, 0]

                    if ":" in str(nodeshape_uri):
                        ns = nodeshape_uri.split(":")[0]
                    else:
                        ns = shaclplay_dir.name
                except Exception as e:
                    click.echo(
                        f"Error: Could not extract namespace from {excel_file.name}: {e}",
                        err=True,
                    )
                    exit(1)

                class_name = excel_file.stem.replace("SHACL-", "")
                output_file = output_file_dir / f"{ns}-{class_name}.ttl"

                click.echo(f"Processing {excel_file.name}...")
                click.echo(f"  Namespace: {ns}")
                click.echo(f"  Output: {output_file}")

                # Create output directory
                output_file_dir.mkdir(parents=True, exist_ok=True)

                # Run xls2rdf conversion
                cmd = [
                    "java",
                    "-jar",
                    str(jar_path),
                    "convert",
                    "-i",
                    str(excel_file),
                    "-o",
                    str(output_file),
                    "-sh",
                    "-np",
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, check=True)

                click.echo(f"  ✓ Successfully generated {output_file}")
                pieces[class_name] = output_file
                namespaces.add(ns)

                # Print any stdout/stderr for debugging
                if result.stdout:
                    click.echo(f"  Output: {result.stdout.strip()}")
                if result.stderr:
                    click.echo(f"  Warnings: {result.stderr.strip()}")

                click.echo()

            except SystemExit:
                raise
            except subprocess.CalledProcessError as e:
                click.echo(f"Error: Failed to convert {excel_file.name}", err=True)
                click.echo(f"  Return code: {e.returncode}", err=True)
                if e.stdout:
                    click.echo(f"  stdout: {e.stdout}", err=True)
                if e.stderr:
                    click.echo(f"  stderr: {e.stderr}", err=True)
                exit(1)

            except Exception as e:
                click.echo(
                    f"Error: Unexpected error processing {excel_file.name}: {e}",
                    err=True,
                )
                traceback.print_exc()
                exit(1)

        for path in merge_fdp_shapes(schemas, pieces, namespaces, output_dir):
            click.echo(f"  ✓ Merged {path}")
        click.echo()

        click.echo("=" * 80)
        click.echo("Conversion complete!")
        click.echo(f"SHACL Turtle files written to {output_dir}")
        click.echo("=" * 80)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if click.get_current_context().obj:
            traceback.print_exc()
        exit(1)


@main.command()
@click.option(
    "-i",
    "--input-excel",
    type=click.Path(exists=True),
    required=True,
    help="Path to source metadata Excel file.",
)
@click.option(
    "-n",
    "--namespace",
    type=str,
    default=None,
    help="Namespace prefix (auto-detected from Excel if not provided).",
)
@click.option(
    "--linkml-output-path",
    type=click.Path(),
    default="./outputs/linkml",
    help="Output directory for LinkML schemas.",
)
@click.option(
    "--sempyro-output-path",
    type=click.Path(),
    default="./outputs/sempyro_classes",
    help="Output directory for SeMPyRO Pydantic classes.",
)
@click.option(
    "--imports-path",
    type=click.Path(exists=True),
    default="./inputs/sempyro/imports.yaml",
    help="Path to imports configuration YAML file.",
)
def sempyro(
    input_excel: str,
    namespace: str,
    linkml_output_path: str,
    sempyro_output_path: str,
    imports_path: str,
) -> None:
    """Generate SeMPyRO Pydantic classes from metadata.

    Converts metadata Excel file to LinkML schemas and then generates
    SeMPyRO Pydantic classes with RDF capabilities.

    \b
    The Excel file must contain:
    - A 'classes' sheet with class configuration including class_uri
    - One sheet per class with property definitions
    """
    try:
        excel_path = Path(input_excel)
        linkml_output_path = Path(linkml_output_path)
        sempyro_output_path = Path(sempyro_output_path)
        imports_p = Path(imports_path)
        exclude_list = ["Info", "User Guide"]

        click.echo("=" * 80)
        click.echo("SeMPyRO Pydantic Class Generator")
        click.echo("=" * 80)
        click.echo()

        # Auto-detect namespace if not provided
        if namespace is None:
            click.echo("Auto-detecting namespace from Excel file...")
            try:
                classes_df = pd.read_excel(excel_path, sheet_name="classes")
                if "class_URI" in classes_df.columns and len(classes_df) > 0:
                    first_ontology = classes_df["class_URI"].iloc[0]
                    if ":" in str(first_ontology):
                        namespace = first_ontology.split(":")[0]
                        click.echo(f"  Detected namespace: {namespace}")
                    else:
                        click.echo(
                            "  Warning: Could not parse namespace from class_URI",
                            err=True,
                        )
                        click.echo("  Please provide namespace with --namespace option")
                        exit(1)
                else:
                    click.echo(
                        "  Error: 'class_URI' column not found in classes sheet",
                        err=True,
                    )
                    exit(1)
            except Exception as e:
                click.echo(f"  Error reading classes sheet: {e}", err=True)
                exit(1)
        else:
            click.echo(f"Using provided namespace: {namespace}")

        click.echo()

        click.echo("[1/4] Generating LinkML schemas...")
        try:
            linkml_creator = LinkMLCreator(linkml_output_path)
            linkml_creator.load_excel(str(excel_path), exclude_list)
            linkml_creator.build_sempyro()
            linkml_creator.write_to_file()
            click.echo("  ✓ LinkML schemas generated")
        except Exception as e:
            click.echo(f"Error: Failed to generate LinkML schemas: {e}", err=True)
            traceback.print_exc()
            exit(1)
        click.echo()

        click.echo("[2/4] Loading imports configuration...")
        if not imports_p.exists():
            click.echo(f"Error: Imports file not found at {imports_p}", err=True)
            exit(1)

        try:
            imports = load_yaml(imports_p)
            click.echo(f"  ✓ Loaded imports for {len(imports)} classes")
        except Exception as e:
            click.echo(f"Error: Failed to load imports configuration: {e}", err=True)
            traceback.print_exc()
            exit(1)
        click.echo()

        # Extract class names from the Excel file
        try:
            classes_df = pd.read_excel(excel_path, sheet_name="classes")
            if "class_URI" not in classes_df.columns:
                click.echo(
                    "Error: 'class_URI' column not found in classes sheet",
                    err=True,
                )
                exit(1)

            class_names = [ont_name.split(":")[-1] for ont_name in classes_df["class_URI"] if pd.notna(ont_name)]
            click.echo(f"  ✓ Found {len(class_names)} classes in Excel file")
        except Exception as e:
            click.echo(f"Error: Failed to read class names from Excel: {e}", err=True)
            traceback.print_exc()
            exit(1)

        click.echo()
        click.echo("[3/4] Generating SeMPyRO Pydantic classes...")

        linkml_definitions_path = linkml_output_path / namespace
        sempyro_class_output_path = sempyro_output_path / namespace
        sempyro_class_output_path.mkdir(parents=True, exist_ok=True)

        success_count = 0
        no_imports = []

        for class_name in class_names:
            class_key = f"{namespace}-{class_name}"
            schema_file = linkml_definitions_path / f"{class_key}.yaml"
            output_file = sempyro_class_output_path / f"{class_key}.py"

            click.echo(f"  Processing {class_name}...")

            if not schema_file.exists():
                click.echo(
                    f"Error: Schema file not found for {class_name}: {schema_file}",
                    err=True,
                )
                exit(1)

            if class_key not in imports:
                click.echo(
                    f"Warning: No imports configuration found for {class_key}",
                )
                no_imports.append(class_key)
                continue

            try:
                link_dict = {
                    "schema_path": schema_file,
                    "imports": imports[class_key],
                    "output_path": str(output_file),
                }
                generate_from_linkml(link_dict)
                remove_unwanted_classes(output_file, schema_file)

                click.echo(f"    ✓ Generated {output_file.name}")
                success_count += 1

            except Exception as e:
                click.echo(f"Error: Failed to generate {class_name}: {e}", err=True)
                traceback.print_exc()
                exit(1)

        click.echo()

        # Format generated files with ruff
        if success_count > 0:
            click.echo("[4/4] Formatting generated Python files with ruff...")
            try:
                # Find ruff in the same environment as this Python interpreter
                python_bin_dir = Path(sys.executable).parent
                ruff_path = python_bin_dir / "ruff"

                # Fall back to system ruff if not found in environment
                if not ruff_path.exists():
                    ruff_path = "ruff"

                format_cmd = [
                    str(ruff_path),
                    "format",
                    str(sempyro_class_output_path),
                ]

                result = subprocess.run(format_cmd, capture_output=True, text=True, check=True)

                click.echo(f"  ✓ Formatted files in {sempyro_class_output_path}")

                if result.stdout:
                    click.echo(f"  {result.stdout.strip()}")

            except subprocess.CalledProcessError as e:
                click.echo("  ⚠ Warning: ruff format failed", err=True)
                if e.stderr:
                    click.echo(f"  {e.stderr.strip()}", err=True)
            except FileNotFoundError:
                click.echo(
                    "  ⚠ Warning: ruff not found. Install with: pip install ruff",
                    err=True,
                )
            click.echo()

        click.echo("=" * 80)
        click.echo("Generation complete!")
        click.echo(f"  Successfully generated: {success_count} classes")
        click.echo(f"  LinkML schemas: {linkml_output_path}")
        click.echo(f"  SeMPyRO classes: {sempyro_output_path}")
        if no_imports:
            click.echo("  Classes skipped due to missing imports configuration:")
            for cls in no_imports:
                click.echo(f"    - {cls}")
        click.echo("=" * 80)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if click.get_current_context().obj:
            traceback.print_exc()
        exit(1)


@main.command()
@click.option(
    "-i",
    "--input-excel",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to the plain metadata Excel file. Only modified with --in-place.",
)
@click.option(
    "-o",
    "--output-excel",
    type=click.Path(dir_okay=False),
    default=None,
    help="Path for the prepared Excel. Give this or --in-place.",
)
@click.option(
    "-n",
    "--namespace",
    type=str,
    default=None,
    help="Namespace prefix used to derive empty class_URI values. Without it, class_URI is left empty.",
)
@click.option(
    "--in-place",
    is_flag=True,
    help="Update the input in place: add sheets, columns, prefixes, sh:node and DASH values, and run the checks.",
)
@click.option("--overwrite", is_flag=True, help="Replace an existing output file. Not used with --in-place.")
def prepare_excel(
    input_excel: str, output_excel: str | None, namespace: str | None, in_place: bool, overwrite: bool
) -> None:
    """Prepare a plain metadata Excel for the shaclplay and sempyro commands.

    \b
    Adds the prefixes and classes sheets and the SHACL_* and SeMPyRO_*
    columns, sets sh:node and DASH values, checks prefix consistency, and
    prints the cells that still have to be filled in by hand. Either writes a
    new Excel (-o) or updates the input in place (--in-place). The FDP variant
    is made with derive-fdp-excel.
    """
    if in_place == (output_excel is not None):
        click.echo("Error: give either an output path (-o) or --in-place, not both and not neither.", err=True)
        exit(1)
    input_path = Path(input_excel)
    output_path = Path(output_excel) if output_excel else None
    try:
        report = prepare_workbook(input_path, output_path, namespace, overwrite=overwrite)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        exit(1)
    click.echo(report.format())
    click.echo(f"Prepared Excel written to {output_path or input_path}")


@main.command()
@click.option(
    "-i",
    "--input-excel",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to the metadata Excel file. It is never modified.",
)
@click.option(
    "-o",
    "--output-plan",
    type=click.Path(dir_okay=False),
    default=None,
    help="Path for the plan (default: next to the input as {name}-plan.xlsx).",
)
@click.option(
    "-n",
    "--namespace",
    type=str,
    default=None,
    help="Namespace prefix used to derive empty class_URI values. Without it, class_URI is left empty.",
)
@click.option("--overwrite", is_flag=True, help="Replace an existing plan, including any edits made to it.")
def plan_excel(input_excel: str, output_plan: str | None, namespace: str | None, overwrite: bool) -> None:
    """Plan the technical columns of a metadata Excel without modifying it.

    \b
    Computes what prepare-excel would change and writes it as a plan
    workbook (Summary, Edits, Gaps, Issues) that can be inspected and edited
    before it is applied. Nothing is written when there is nothing to plan.
    """
    input_path = Path(input_excel)
    plan_path = Path(output_plan) if output_plan else default_plan_path(input_path)
    try:
        plan, report = compute_plan(input_path, namespace)
        click.echo(report.format())
        click.echo(f"Plan: {len(plan.edits)} edit(s), {len(plan.gaps)} required cell(s) to fill in.")
        if plan.is_empty:
            click.echo("Nothing to plan: the technical columns are correct and complete. No plan written.")
            return
        write_plan(plan, plan_path, overwrite=overwrite)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        exit(1)
    click.echo(f"Plan written to {plan_path}")


@main.command()
@click.option(
    "-i",
    "--input-excel",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to the metadata Excel file. It is never modified.",
)
@click.option(
    "-n",
    "--namespace",
    type=str,
    default=None,
    help="Namespace prefix used to derive empty class_URI values, as for plan-excel.",
)
@click.option(
    "--summary",
    "summary_path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Also write the result as markdown to this file, e.g. $GITHUB_STEP_SUMMARY (appended).",
)
@click.option("--hint", type=str, default=DEFAULT_HINT, help="What to do when the check fails; shown in the result.")
def check_excel(input_excel: str, namespace: str | None, summary_path: str | None, hint: str) -> None:
    """Check that the technical columns of a metadata Excel are correct and complete.

    \b
    Computes the plan in memory. Exits with 0 when no edit is pending and no
    required cell is empty, and with 1 otherwise, listing what is missing.
    The Excel is never modified.
    """
    input_path = Path(input_excel)
    try:
        plan, _ = compute_plan(input_path, namespace)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        exit(2)
    result = format_check(plan, hint, input_path)
    click.echo(result)
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(result + "\n")
    if not plan.is_empty:
        exit(1)


@main.command()
@click.option(
    "-p",
    "--plan",
    "plan_path",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to the plan made by plan-excel.",
)
@click.option(
    "-i",
    "--input-excel",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Excel the plan was made from (default: the source named in the plan, next to the plan).",
)
@click.option(
    "-o",
    "--output-excel",
    type=click.Path(dir_okay=False),
    default=None,
    help="Write the result to a new file instead of updating the input in place.",
)
@click.option("--overwrite", is_flag=True, help="Replace an existing output file. Not used when updating in place.")
@click.option("--keep-plan", is_flag=True, help="Keep the plan after updating in place; it is deleted by default.")
@click.option(
    "--ignore-source-hash",
    is_flag=True,
    help="Apply although the Excel changed since the plan was made. Each edit is still matched and checked.",
)
@click.option(
    "--log",
    "log_path",
    type=click.Path(dir_okay=False),
    default=None,
    help="Also write the log of changes to this file.",
)
def apply_plan(
    plan_path: str,
    input_excel: str | None,
    output_excel: str | None,
    overwrite: bool,
    keep_plan: bool,
    ignore_source_hash: bool,
    log_path: str | None,
) -> None:
    """Apply a plan from plan-excel to the metadata Excel.

    \b
    Writes the edits of the plan that are marked Apply = yes and the values
    typed under Gaps, and logs every change. Refuses a plan made from another
    version of the Excel (unless --ignore-source-hash), and writes nothing
    when an edit does not fit. The
    Excel is updated in place (the plan is then deleted) unless -o is given.
    """
    plan_file = Path(plan_path)
    try:
        source = Path(input_excel) if input_excel else plan_file.with_name(read_plan(plan_file).source_name)
        if not source.exists():
            raise ValueError(f"Source {source} not found; pass it with -i.")
        output = Path(output_excel) if output_excel else None
        result = apply_plan_to_workbook(
            source, plan_file, output, overwrite=overwrite, keep_plan=keep_plan, check_hash=not ignore_source_hash
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        exit(1)
    log = result.format()
    click.echo(log)
    if log_path:
        Path(log_path).write_text(log, encoding="utf-8")
    click.echo(f"Updated Excel written to {output or source}")


@main.command()
@click.option(
    "-i",
    "--input-excel",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to the metadata Excel file. It is never modified.",
)
@click.option(
    "-o",
    "--output-excel",
    type=click.Path(dir_okay=False),
    required=True,
    help="Path for the FDP variant of the Excel.",
)
@click.option(
    "-n",
    "--namespace",
    type=str,
    default=None,
    help="Namespace prefix used to derive empty class_URI values. Without it, class_URI is left empty.",
)
@click.option("--overwrite", is_flag=True, help="Replace an existing output file.")
def derive_fdp_excel(input_excel: str, output_excel: str, namespace: str | None, overwrite: bool) -> None:
    """Derive the FDP variant of a metadata Excel.

    \b
    Classes with SHACL_independent_class TRUE are resources of their own in
    the FDP. A range pointing at one gets (IRI), a non-required cardinality,
    an empty SHACL_sh:node and the URI viewer and editor. The Resource sheet
    is added when missing and independent classes without dct:title are
    reported. The workbook is prepared in memory as prepare-excel does, which
    changes nothing for an already prepared Excel. The input is never modified.
    """
    try:
        report = derive_fdp_workbook(Path(input_excel), Path(output_excel), namespace, overwrite=overwrite)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        exit(1)
    click.echo(report.format())
    click.echo(f"FDP Excel written to {output_excel}")


@main.command()
@click.option(
    "-i",
    "--input-excel",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
    help="Path to the metadata model Excel file.",
)
@click.option(
    "-b",
    "--base-properties",
    type=click.Path(exists=True, dir_okay=False),
    default=str(Path(__file__).parent.parent / "inputs/fdp/Properties-base.yaml"),
    help="Properties.yaml providing the non-derived settings (default: inputs/fdp/Properties-base.yaml).",
)
@click.option(
    "-o",
    "--output-path",
    type=click.Path(dir_okay=False),
    default="./outputs/fdp/Properties.yaml",
    help="Path for the generated Properties.yaml.",
)
@click.option(
    "--namespace",
    type=str,
    default=None,
    help="Prefix of the SHACL file names (default: the class_URI prefix). Match the shaclplay --namespace.",
)
@click.option("--schema-version", type=str, default=None, help="Override schemaVersion from the base file.")
def fdp_properties(
    input_excel: str, base_properties: str, output_path: str, namespace: str | None, schema_version: str | None
) -> None:
    """Generate a FairDataPointSchemaTool Properties.yaml.

    \b
    schemasToPublish: classes with SHACL_independent_class TRUE.
    schemas: per schema its SHACL file plus all classes reached through SHACL_sh:node.
    resources: properties with an FDP_resources name.
    Other settings are copied from the base Properties.yaml.
    """
    try:
        properties = generate_properties(
            Path(input_excel), Path(base_properties), Path(output_path), namespace, schema_version
        )
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        exit(1)
    for name, files in properties["schemas"].items():
        click.echo(f"{name}: {', '.join(files)}")
    click.echo(f"Properties written to {output_path}")


@main.command()
@click.option(
    "-i",
    "--input-dir",
    type=click.Path(exists=True, file_okay=False),
    required=True,
    help="Directory containing generated SeMPyRO Python class files.",
)
@click.option(
    "-o",
    "--output-file",
    type=click.Path(),
    default=None,
    help="Optional path to write the report to a file.",
)
def inspect_inheritance(
    input_dir: str,
    output_file: str | None,
) -> None:
    """Inspect inheritance overlap in generated SeMPyRO classes.

    Loads every generated SeMPyRO ``.py`` file in INPUT_DIR, walks the full
    MRO ancestor chain, and reports which fields in each subclass are already
    defined in an ancestor.  Useful for identifying properties that can be
    removed because they are already inherited.

    \b
    For each overlapping field the report shows:
    - Which ancestor class defines it (and how many levels up)
    - Whether description, rdf_term, and rdf_type are identical or differ
    - A verdict: [IDENTICAL – can be removed] or [DIFFERS – review before removing]
    """
    try:
        input_path = Path(input_dir)
        py_files = sorted(f for f in input_path.glob("*.py") if f.name != "__init__.py")

        click.echo("=" * 80)
        click.echo("Inheritance Inspector")
        click.echo("=" * 80)
        click.echo()

        if not py_files:
            click.echo(f"No Python class files found in {input_path}", err=True)
            exit(1)

        click.echo(f"Found {len(py_files)} class file(s) in {input_path}")
        click.echo()

        results = []
        for py_file in py_files:
            click.echo(f"  Inspecting {py_file.name}...")
            results.append(inspect_file(py_file))

        click.echo()
        report = format_report(results)
        click.echo(report)

        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(report, encoding="utf-8")
            click.echo(f"Report written to {output_path}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
