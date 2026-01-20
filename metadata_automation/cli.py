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

from metadata_automation.linkml.creator import LinkMLCreator
from metadata_automation.sempyro.cleanup import remove_unwanted_classes
from metadata_automation.sempyro.utils import generate_from_linkml, load_yaml
from metadata_automation.shaclplay.converter import SHACLPlayConverter
from metadata_automation.shaclplay.utils import write_shaclplay_excel


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
    default="./outputs/shaclplay/default",
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

        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize converter
        click.echo(f"Loading template from {template_p}...")
        click.echo(f"Loading prefixes from {excel_path}...")
        converter = SHACLPlayConverter(template_p, excel_path)

        # Read the classes sheet to get configuration for each class
        click.echo(f"Reading classes configuration...")
        classes_df = pd.read_excel(excel_path, sheet_name="classes")
        click.echo(f"Found {len(classes_df)} classes to process")
        click.echo()

        # Process each class
        for idx, class_row in classes_df.iterrows():
            sheet_name = class_row["sheet_name"]
            ontology_name = class_row["ontology_name"]
            target_class = class_row["target_ontology_name"]
            description = class_row.get("description", None)

            # Convert NaN to None for description
            if pd.isna(description):
                description = None

            # Override namespace if provided (only for ontology_name)
            if namespace:
                # Extract the class name from the original ontology_name
                class_name_only = ontology_name.split(":")[-1]
                # Override ontology_name with the new namespace
                ontology_name = f"{namespace}:{class_name_only}"

            click.echo(f"Processing {sheet_name} class...")
            click.echo(f"  Ontology: {ontology_name}")
            click.echo(f"  Target: {target_class}")

            try:
                # Read the class sheet
                class_df = pd.read_excel(excel_path, sheet_name=sheet_name)
                click.echo(f"  Loaded {len(class_df)} properties")

                # Extract class name from ontology_name
                # (e.g., "hri:Dataset" -> "Dataset")
                class_name = ontology_name.split(":")[-1]

                # Convert to SHACLPlay format
                (
                    nodeshapes_df,
                    propertyshapes_df,
                ) = converter.convert_class_sheet(
                    class_sheet_df=class_df,
                    class_name=class_name,
                    ontology_name=ontology_name,
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

            except Exception as e:
                click.echo(f"  ✗ Error processing {sheet_name}: {e}")
                if click.get_current_context().obj:
                    traceback.print_exc()
                click.echo()

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
def shacl_from_shaclplay(
    input_path: str,
    output_path: str,
) -> None:
    """Generate SHACL Turtle files from SHACLPlay Excel files.

    Converts SHACLPlay Excel files to SHACL Turtle format using the xls2rdf
    tool. Requires Java to be installed and available in PATH.
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

        click.echo(
            f"Found {len(excel_files)} SHACLPlay Excel files to convert"
        )
        click.echo()

        # Process each file
        for excel_file in excel_files:
            try:
                # Extract namespace from the Excel file
                df = pd.read_excel(
                    excel_file,
                    sheet_name="NodeShapes (classes)",
                    header=None,
                )
                nodeshape_uri = df.iloc[13, 0]

                if ":" in str(nodeshape_uri):
                    ns = nodeshape_uri.split(":")[0]
                else:
                    ns = shaclplay_dir.name

            except Exception as e:
                click.echo(
                    f"Warning: Could not extract namespace from {excel_file.name}: {e}"
                )
                ns = shaclplay_dir.name

            output_file_dir = output_dir / ns
            class_name = excel_file.stem.replace("SHACL-", "")
            output_file = output_file_dir / f"{ns}-{class_name}.ttl"

            click.echo(f"Processing {excel_file.name}...")
            click.echo(f"  Namespace: {ns}")
            click.echo(f"  Output: {output_file}")

            try:
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

                result = subprocess.run(
                    cmd, capture_output=True, text=True, check=True
                )

                click.echo(f"  ✓ Successfully generated {output_file}")

                # Print any stdout/stderr for debugging
                if result.stdout:
                    click.echo(f"  Output: {result.stdout.strip()}")
                if result.stderr:
                    click.echo(f"  Warnings: {result.stderr.strip()}")

                click.echo()

            except subprocess.CalledProcessError as e:
                click.echo(f"  ✗ Error converting {excel_file.name}")
                click.echo(f"  Return code: {e.returncode}")
                if e.stdout:
                    click.echo(f"  stdout: {e.stdout}")
                if e.stderr:
                    click.echo(f"  stderr: {e.stderr}")
                click.echo()

            except Exception as e:
                click.echo(f"  ✗ Unexpected error: {e}")
                if click.get_current_context().obj:
                    traceback.print_exc()
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
def sempyro(
    input_excel: str,
    namespace: str,
) -> None:
    """Generate SeMPyRO Pydantic classes from metadata.

    Converts metadata Excel file to LinkML schemas and then generates
    SeMPyRO Pydantic classes with RDF capabilities.

    \b
    The Excel file must contain:
    - A 'classes' sheet with class configuration including ontology_name
    - One sheet per class with property definitions
    """
    try:
        excel_path = Path(input_excel)
        linkml_output_path = Path("./outputs/linkml")
        sempyro_output_path = Path("./outputs/sempyro_classes")
        imports_p = Path("./inputs/sempyro/imports.yaml")
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
                if (
                    "ontology_name" in classes_df.columns
                    and len(classes_df) > 0
                ):
                    first_ontology = classes_df["ontology_name"].iloc[0]
                    if ":" in str(first_ontology):
                        namespace = first_ontology.split(":")[0]
                        click.echo(f"  Detected namespace: {namespace}")
                    else:
                        click.echo(
                            "  Warning: Could not parse namespace from ontology_name",
                            err=True,
                        )
                        click.echo(
                            "  Please provide namespace with --namespace option"
                        )
                        exit(1)
                else:
                    click.echo(
                        "  Error: 'ontology_name' column not found in classes sheet",
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
        linkml_creator = LinkMLCreator(linkml_output_path)
        linkml_creator.load_excel(str(excel_path), exclude_list)
        linkml_creator.build_sempyro()
        linkml_creator.write_to_file()
        click.echo("  ✓ LinkML schemas generated")
        click.echo()

        click.echo("[2/4] Loading imports configuration...")
        if not imports_p.exists():
            click.echo(
                f"  Error: Imports file not found at {imports_p}", err=True
            )
            exit(1)

        imports = load_yaml(imports_p)
        click.echo(f"  ✓ Loaded imports for {len(imports)} classes")
        click.echo()

        # Extract class names from the Excel file
        try:
            classes_df = pd.read_excel(excel_path, sheet_name="classes")
            if "ontology_name" not in classes_df.columns:
                click.echo(
                    "  Error: 'ontology_name' column not found in classes sheet",
                    err=True,
                )
                exit(1)

            class_names = [
                ont_name.split(":")[-1]
                for ont_name in classes_df["ontology_name"]
                if pd.notna(ont_name)
            ]
            click.echo(f"  ✓ Found {len(class_names)} classes in Excel file")
        except Exception as e:
            click.echo(
                f"  Error reading class names from Excel: {e}", err=True
            )
            exit(1)

        click.echo()
        click.echo("[3/4] Generating SeMPyRO Pydantic classes...")

        linkml_definitions_path = linkml_output_path / namespace
        sempyro_class_output_path = sempyro_output_path / namespace
        sempyro_class_output_path.mkdir(parents=True, exist_ok=True)

        success_count = 0
        error_count = 0

        for class_name in class_names:
            class_key = f"{namespace}-{class_name}"
            schema_file = linkml_definitions_path / f"{class_key}.yaml"
            output_file = sempyro_class_output_path / f"{class_key}.py"

            click.echo(f"  Processing {class_name}...")
            if not schema_file.exists():
                click.echo(f"    ⚠ Schema file not found: {schema_file}")
                error_count += 1
                continue

            if class_key not in imports:
                click.echo(
                    f"    ⚠ No imports configuration found for {class_key}"
                )
                error_count += 1
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
                click.echo(f"    ✗ Error: {e}")
                if click.get_current_context().obj:
                    traceback.print_exc()
                error_count += 1

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

                result = subprocess.run(
                    format_cmd, capture_output=True, text=True, check=True
                )

                click.echo(
                    f"  ✓ Formatted files in {sempyro_class_output_path}"
                )

                if result.stdout:
                    click.echo(f"  {result.stdout.strip()}")

            except subprocess.CalledProcessError as e:
                click.echo(f"  ⚠ Warning: ruff format failed")
                if e.stderr:
                    click.echo(f"  {e.stderr.strip()}")
            except FileNotFoundError:
                click.echo(
                    f"  ⚠ Warning: ruff not found. Install with: pip install ruff"
                )
            click.echo()

        click.echo("=" * 80)
        click.echo("Generation complete!")
        click.echo(f"  Successfully generated: {success_count} classes")
        if error_count > 0:
            click.echo(f"  Errors: {error_count} classes")
        click.echo(f"  LinkML schemas: {linkml_output_path}")
        click.echo(f"  SeMPyRO classes: {sempyro_output_path}")
        click.echo("=" * 80)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        if click.get_current_context().obj:
            traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
