"""Command line interface for metadata-automation.

Provides CLI commands for generating metadata artifacts from source
Excel files. Supports generation of SHACL shapes, SHACLPlay Excel files,
and SeMPyRO Pydantic classes.
"""

import subprocess
import traceback
from pathlib import Path

import click
import pandas as pd

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
    "--excel-file",
    type=click.Path(exists=True),
    required=True,
    help="Path to source metadata Excel file.",
)
@click.option(
    "--template-path",
    type=click.Path(exists=True),
    required=True,
    help="Path to SHACLPlay template Excel file.",
)
@click.option(
    "--output-path",
    type=click.Path(),
    default="./outputs/shaclplay",
    help="Output directory for SHACLPlay Excel files.",
)
@click.option(
    "--namespace",
    type=str,
    default="hri",
    help="Namespace prefix for generated files (e.g., 'hri', 'eucaim').",
)
def shaclplay(
    excel_file: str,
    template_path: str,
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
        excel_path = Path(excel_file)
        template_p = Path(template_path)
        output_dir = Path(output_path) / namespace

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
        exit


@main.command()
@click.option(
    "--shaclplay-path",
    type=click.Path(exists=True),
    required=True,
    help="Path to directory containing SHACLPlay Excel files.",
)
@click.option(
    "--output-path",
    type=click.Path(),
    default="./outputs/shacl_shapes",
    help="Output directory for SHACL Turtle files.",
)
@click.option(
    "--namespace",
    type=str,
    default=None,
    help="Namespace prefix for output files (overrides auto-detection).",
)
@click.option(
    "--xls2rdf-jar",
    type=click.Path(exists=True),
    default="./inputs/shacls/xls2rdf-app-3.2.1-onejar.jar",
    help="Path to xls2rdf JAR file.",
)
def shacl(
    shaclplay_path: str,
    output_path: str,
    namespace: str,
    xls2rdf_jar: str,
) -> None:
    """Generate SHACL Turtle files from SHACLPlay Excel files.

    Converts SHACLPlay Excel files to SHACL Turtle format using the xls2rdf
    tool. Requires Java to be installed and available in PATH.
    """
    try:
        shaclplay_dir = Path(shaclplay_path)
        output_dir = Path(output_path)
        jar_path = Path(xls2rdf_jar)

        click.echo("=" * 80)
        click.echo("SHACL Turtle Generator from SHACLPlay Excel")
        click.echo("=" * 80)
        click.echo()

        # Check if xls2rdf JAR exists
        if not jar_path.exists():
            click.echo(f"Error: xls2rdf JAR not found at {jar_path}", err=True)
            raise click.Exit(1)

        # Find all SHACLPlay Excel files
        excel_files = list(shaclplay_dir.glob("*.xlsx"))

        if not excel_files:
            click.echo(
                f"No SHACLPlay Excel files found in {shaclplay_dir}",
                err=True,
            )
            exit

        click.echo(
            f"Found {len(excel_files)} SHACLPlay Excel files to convert"
        )
        click.echo()

        # Process each file
        for excel_file in excel_files:
            try:
                # Extract namespace from the Excel file if not specified
                if namespace:
                    ns = namespace
                else:
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
                ns = namespace if namespace else shaclplay_dir.name

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
        exit


if __name__ == "__main__":
    main()
