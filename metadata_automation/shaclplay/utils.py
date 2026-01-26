"""
Utility functions for SHACLPlay Excel generation.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional
import pandas as pd


def slugify_property_label(label: str) -> str:
    """
    Convert a property label to a URL-friendly slug.

    Args:
        label: Property label (e.g., "access rights")

    Returns:
        Slugified version (e.g., "access-rights")
    """
    # Convert to lowercase and replace spaces with hyphens
    slug = label.lower().strip()
    slug = re.sub(r"\s+", "-", slug)
    # Remove any characters that aren't alphanumeric or hyphens
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    return slug


def parse_cardinality(cardinality: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Parse cardinality string into min and max counts.

    Args:
        cardinality: Cardinality string (e.g., "1", "0..n", "1..n")

    Returns:
        Tuple of (min_count, max_count). max_count is None for unbounded.

    Examples:
        "1" -> (1, 1)
        "0..n" -> (0, None)
        "1..n" -> (1, None)
        "0..1" -> (0, 1)
    """
    if not cardinality or str(cardinality) == "nan":
        return (None, None)

    cardinality = str(cardinality).strip()

    # Check if it's a range (e.g., "0..n", "1..n")
    if ".." in cardinality:
        parts = cardinality.split("..")
        min_count = int(parts[0].strip()) if parts[0].strip() != "0" else None
        max_part = parts[1].strip()
        max_count = None if max_part == "n" else int(max_part)
        return (min_count, max_count)
    else:
        # Single value (e.g., "1")
        count = int(cardinality)
        return (count, count)


def get_current_datetime_iso() -> str:
    """
    Get current datetime in ISO format suitable for dcterms:modified.

    Returns:
        ISO datetime string (e.g., "2025-02-10T00:00:00")
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def write_shaclplay_excel(
    prefixes_df: pd.DataFrame,
    nodeshapes_df: pd.DataFrame,
    propertyshapes_df: pd.DataFrame,
    output_path: Path,
) -> None:
    """
    Write SHACLPlay data to Excel file with three sheets.

    Args:
        prefixes_df: DataFrame for prefixes sheet
        nodeshapes_df: DataFrame for NodeShapes sheet
        propertyshapes_df: DataFrame for PropertyShapes sheet
        output_path: Path to output Excel file
    """
    # Create parent directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write to Excel with three sheets
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        prefixes_df.to_excel(
            writer, sheet_name="prefixes", index=False, header=False
        )
        nodeshapes_df.to_excel(
            writer,
            sheet_name="NodeShapes (classes)",
            index=False,
            header=False,
        )
        propertyshapes_df.to_excel(
            writer,
            sheet_name="PropertyShapes (properties)",
            index=False,
            header=False,
        )

    print(f"Written SHACLPlay Excel to {output_path}")
