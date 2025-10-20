"""
Generate SHACLPlay Excel files from Health-RI metadata Excel.

This script converts the Health-RI metadata Excel file to SHACLPlay-compatible
Excel format that can be imported into SHACLPlay for SHACL shape editing.
"""

import traceback
from pathlib import Path
import pandas as pd

from metadata_automation.shaclplay.converter import SHACLPlayConverter
from metadata_automation.shaclplay.utils import write_shaclplay_excel

# Configuration
EXCEL_FILE_PATH = "./inputs/EUCAIM.xlsx"
TEMPLATE_PATH = Path("./inputs/shacls/shaclplay-template.xlsx")
FOLDER_NAME = "eucaim"
OUTPUT_PATH = Path("./outputs/shaclplay") / FOLDER_NAME

def main():
    """Main conversion function."""
    print("=" * 80)
    print("SHACLPlay Excel Generator")
    print("=" * 80)
    print()

    # Create output directory
    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)

    # Initialize converter
    print(f"Loading template from {TEMPLATE_PATH}...")
    print(f"Loading prefixes from {EXCEL_FILE_PATH}...")
    converter = SHACLPlayConverter(TEMPLATE_PATH, Path(EXCEL_FILE_PATH))

    # Read the classes sheet to get configuration for each class
    print(f"Reading classes configuration from {EXCEL_FILE_PATH}...")
    classes_df = pd.read_excel(EXCEL_FILE_PATH, sheet_name='classes')
    print(f"  Found {len(classes_df)} classes to process")
    print()

    # Process each class
    for idx, class_row in classes_df.iterrows():
        sheet_name = class_row['sheet_name']
        ontology_name = class_row['ontology_name']
        target_class = class_row['target_ontology_name']
        description = class_row.get('description', None)

        # Convert NaN to None for description
        if pd.isna(description):
            description = None

        print(f"Processing {sheet_name} class...")
        print(f"  Ontology: {ontology_name}")
        print(f"  Target: {target_class}")

        try:
            # Read the class sheet from Health-RI Excel
            class_df = pd.read_excel(EXCEL_FILE_PATH, sheet_name=sheet_name)
            print(f"  Loaded {len(class_df)} properties")

            # Extract class name from ontology_name (e.g., "hri:Dataset" -> "Dataset")
            class_name = ontology_name.split(':')[-1]

            # Convert to SHACLPlay format
            nodeshapes_df, propertyshapes_df = converter.convert_class_sheet(
                class_sheet_df=class_df,
                class_name=class_name,
                ontology_name=ontology_name,
                target_class=target_class,
                description=description
            )

            # Get prefixes
            prefixes_df = converter.get_prefixes_dataframe()

            # Write to output file
            output_file = OUTPUT_PATH / f"SHACL-{sheet_name.lower()}.xlsx"
            write_shaclplay_excel(
                prefixes_df=prefixes_df,
                nodeshapes_df=nodeshapes_df,
                propertyshapes_df=propertyshapes_df,
                output_path=output_file
            )

            print(f"  ✓ Generated {output_file}")
            print()

        except Exception as e:
            print(f"  ✗ Error processing {sheet_name}: {e}")
            traceback.print_exc()
            print()

    print("=" * 80)
    print("Conversion complete!")
    print(f"Output files written to {OUTPUT_PATH}")
    print("=" * 80)


if __name__ == "__main__":
    main()
