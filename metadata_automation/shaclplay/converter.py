"""
SHACLPlay Excel converter for Health-RI metadata.

Converts Health-RI Excel metadata files to SHACLPlay-compatible Excel format.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional

from .utils import (
    slugify_property_label,
    parse_cardinality,
    get_current_datetime_iso
)
from .vocab_mappings import get_vocab_mapping, has_vocab_mapping


class SHACLPlayConverter:
    """Converts Health-RI Excel metadata to SHACLPlay Excel format."""

    def __init__(self, template_path: Path, source_excel_path: Path):
        """
        Initialize the converter.

        Args:
            template_path: Path to the SHACLPlay template Excel file
            source_excel_path: Path to the source Health-RI Excel file
        """
        self.template_path = template_path
        self.source_excel_path = source_excel_path
        self.prefixes_df = None
        self.template_nodeshapes = None
        self.template_propertyshapes = None
        self._load_template()
        self._load_source_prefixes()

    def _load_template(self):
        """Load the SHACLPlay template to get structure."""
        # Read template structure for NodeShapes (to get headers and metadata structure)
        self.template_nodeshapes = pd.read_excel(
            self.template_path,
            sheet_name='NodeShapes (classes)',
            header=None
        )

        # Read template structure for PropertyShapes
        self.template_propertyshapes = pd.read_excel(
            self.template_path,
            sheet_name='PropertyShapes (properties)',
            header=None
        )

    def _load_source_prefixes(self):
        """Load prefixes from the source Health-RI Excel file and convert to SHACLPlay format."""
        # Read source prefixes (has header row with 'prefix' and 'namespace' columns)
        source_prefixes = pd.read_excel(
            self.source_excel_path,
            sheet_name='prefixes',
            header=0  # First row is header
        )

        # Convert to SHACLPlay format:
        # - Row 0: empty row (all NaN)
        # - Subsequent rows: ['PREFIX', prefix_value, namespace_value]

        # Create empty first row
        empty_row = pd.Series([np.nan, np.nan, np.nan])

        # Create prefix rows
        prefix_rows = []
        for idx, row in source_prefixes.iterrows():
            prefix_row = pd.Series(['PREFIX', row['prefix'], row['namespace']])
            prefix_rows.append(prefix_row)

        # Combine all rows
        all_rows = [empty_row] + prefix_rows

        # Create DataFrame with no column headers
        self.prefixes_df = pd.DataFrame(all_rows)
        self.prefixes_df.reset_index(drop=True, inplace=True)

    def convert_class_sheet(
        self,
        class_sheet_df: pd.DataFrame,
        class_name: str,
        ontology_name: str,
        target_class: str,
        description: str = None
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Convert a class sheet from Health-RI format to SHACLPlay format.

        Args:
            class_sheet_df: DataFrame of the class sheet (e.g., 'Dataset')
            class_name: Name of the class (e.g., 'Dataset')
            ontology_name: Ontology name with prefix (e.g., 'hri:Dataset')
            target_class: Target class URI (e.g., 'dcat:Dataset')
            description: Optional description of the class

        Returns:
            Tuple of (nodeshapes_df, propertyshapes_df)
        """
        # Build NodeShapes sheet
        nodeshapes_df = self._build_nodeshapes(
            class_name, ontology_name, target_class, description
        )

        # Build PropertyShapes sheet
        propertyshapes_df = self._build_propertyshapes(
            class_sheet_df, class_name, ontology_name
        )

        return nodeshapes_df, propertyshapes_df

    def _build_nodeshapes(
        self,
        class_name: str,
        ontology_name: str,
        target_class: str,
        description: Optional[str]
    ) -> pd.DataFrame:
        """
        Build the NodeShapes sheet.

        Args:
            class_name: Name of the class (e.g., 'Dataset')
            ontology_name: Ontology name (e.g., 'hri:Dataset')
            target_class: Target class (e.g., 'dcat:Dataset')
            description: Optional description

        Returns:
            DataFrame for NodeShapes sheet
        """
        # Create a deep copy of the template structure
        df = self.template_nodeshapes.copy(deep=True)

        # Update metadata rows
        shape_uri = f"http://data.health-ri.nl/core/p2/{class_name}Shape"
        df.iat[0, 1] = shape_uri  # Shapes URI

        # Update labels and description
        label = f"Excel template for {class_name} class"
        df.iat[2, 1] = label  # rdfs:label@en
        df.iat[3, 1] = label  # rdfs:comment@en

        if description:
            df.iat[4, 1] = description  # dcterms:description@en
        else:
            df.iat[4, 1] = f"This is an excel template for {class_name} class in Health RI Core plateau 2."

        # Update version and modified date
        df.iat[5, 1] = "0.1"  # owl:versionInfo
        df.iat[6, 1] = get_current_datetime_iso()  # dcterms:modified

        # Add a new row for the actual NodeShape data (after the 13 template rows)
        # Create new row with the NodeShape data
        new_nodeshape_row = pd.Series([np.nan] * len(df.columns))
        new_nodeshape_row.iloc[0] = f"hri:{class_name}Shape"  # URI
        new_nodeshape_row.iloc[1] = class_name  # rdfs:label@en
        new_nodeshape_row.iloc[2] = np.nan  # rdfs:comment@en (usually empty)
        new_nodeshape_row.iloc[3] = "sh:NodeShape"  # rdf:type
        new_nodeshape_row.iloc[4] = target_class  # sh:targetClass

        # Append the new row to the DataFrame
        df = pd.concat([df, new_nodeshape_row.to_frame().T], ignore_index=True)

        return df

    def _build_propertyshapes(
        self,
        class_sheet_df: pd.DataFrame,
        class_name: str,
        ontology_name: str
    ) -> pd.DataFrame:
        """
        Build the PropertyShapes sheet.

        Args:
            class_sheet_df: DataFrame of the class properties
            class_name: Name of the class
            ontology_name: Ontology name with prefix

        Returns:
            DataFrame for PropertyShapes sheet
        """
        # Start with template structure (rows 0-6 contain headers and metadata)
        df = self.template_propertyshapes.copy(deep=True)

        # Update the Shapes URI in row 0
        shape_uri = f"http://data.health-ri.nl/core/p2/{class_name}Shape"
        df.iat[0, 1] = shape_uri

        # Build property rows
        property_rows = []

        # Add section header row (row 7 in template)
        section_header = df.iloc[7].copy()
        property_rows.append(section_header)

        # Process each property from the class sheet
        for idx, row in class_sheet_df.iterrows():
            if pd.isna(row['Property label']) or row['Property label'] == 'nan':
                continue

            property_row = self._convert_property_to_shaclplay(row, class_name)
            property_rows.append(property_row)

        # Combine header rows (0-6) with property rows
        header_rows = [df.iloc[i] for i in range(7)]
        all_rows = header_rows + property_rows

        # Create new DataFrame
        result_df = pd.DataFrame(all_rows)
        result_df.reset_index(drop=True, inplace=True)

        return result_df

    def _convert_property_to_shaclplay(
        self,
        property_row: pd.Series,
        class_name: str
    ) -> pd.Series:
        """
        Convert a single property row to SHACLPlay format.

        Args:
            property_row: Row from class sheet
            class_name: Name of the class

        Returns:
            Series representing PropertyShape row
        """
        # Create a new row with proper column count (24 columns based on template)
        new_row = pd.Series([np.nan] * 24)

        # Column 0: URI (PropertyShape identifier)
        prop_label = property_row['Property label']
        slug = slugify_property_label(prop_label)
        new_row[0] = f"hri:{class_name}Shape#{slug}"

        # Column 1: ^sh:property (parent NodeShape)
        new_row[1] = f"hri:{class_name}Shape"

        # Column 2: sh:path (property URI)
        new_row[2] = property_row['Property URI']

        # Column 3: sh:name@en (property label)
        new_row[3] = prop_label

        # Column 4: sh:description@en (definition or usage note)
        description = property_row.get('Definition', '')
        usage_note = property_row.get('Usage note', '')
        if pd.notna(description) and description != 'nan':
            new_row[4] = description
        elif pd.notna(usage_note) and usage_note != 'nan':
            new_row[4] = usage_note

        # Column 5: # (comments - leave empty)
        new_row[5] = np.nan

        # Columns 6-7: sh:minCount and sh:maxCount
        cardinality = property_row.get('Cardinality', '')
        min_count, max_count = parse_cardinality(cardinality)
        if min_count is not None:
            new_row[6] = min_count
        if max_count is not None:
            new_row[7] = max_count

        # Columns 8-10: sh:nodeKind, sh:datatype, sh:node
        # Decision logic based on Range column (Option 3)
        range_value = str(property_row.get('Range', ''))
        sh_node_col = str(property_row.get('sh:node', ''))  # Renamed from 'SHACL range'

        # Pattern 1: Range contains "(IRI)" suffix → sh:nodeKind = sh:IRI only
        # Check explicitly for (IRI) at the end to avoid matching "dcat:Class (IRI)" in middle
        if range_value.strip().endswith('(IRI)'):
            new_row[8] = 'sh:IRI'  # sh:nodeKind
            # No sh:datatype, no sh:node

        # Pattern 2: Range = "rdfs:Literal" → sh:nodeKind = sh:Literal only
        elif range_value.strip() == 'rdfs:Literal':
            new_row[8] = 'sh:Literal'  # sh:nodeKind
            # No sh:datatype, no sh:node

        # Pattern 3: Range contains ":" but no "(IRI)" suffix → use sh:node from 'sh:node' column
        elif ':' in range_value and not range_value.strip().endswith('(IRI)') and sh_node_col and sh_node_col != 'nan':
            # Convert sh:node column value to full URI if needed
            if sh_node_col.startswith('hri:'):
                # Already in correct format (e.g., "hri:KindShape", "hri:RelationshipShape")
                shape_name = sh_node_col.split(':')[1]  # Gets "KindShape", "RelationshipShape", etc.
                new_row[10] = f"http://data.health-ri.nl/core/p2/{shape_name}"
            elif ':' not in sh_node_col:
                # Plain name (e.g., "KindShape") - add full URI
                new_row[10] = f"http://data.health-ri.nl/core/p2/{sh_node_col}"
            else:
                # Already a full URI or other prefixed form
                new_row[10] = sh_node_col
            # No sh:nodeKind, no sh:datatype when using sh:node

        # Pattern 4: Range starts with "xsd:" → use as sh:datatype
        elif range_value.startswith('xsd:'):
            new_row[8] = 'sh:Literal'  # sh:nodeKind
            new_row[9] = range_value    # sh:datatype (e.g., "xsd:dateTime")
            # No sh:node

        # Columns 11-14: sh:qualifiedValueShape, sh:qualifiedMinCount, sh:qualifiedMaxCount, sh:or
        # (Leave empty for now - not commonly used)

        # Column 15: sh:pattern
        pattern = property_row.get('Pattern', '')
        if pd.notna(pattern) and pattern != 'nan':
            new_row[15] = pattern

        # Column 16: sh:uniqueLang (leave empty for now)

        # Column 17: sh:in (controlled vocabulary)
        vocab_url = property_row.get('Controlled vocabluary (if applicable)', '')
        if pd.notna(vocab_url) and vocab_url != 'nan':
            vocab_mapping = get_vocab_mapping(vocab_url)
            if vocab_mapping:
                new_row[17] = vocab_mapping['sh_in']

        # Columns 18-19: sh:languageIn, sh:uniqueLang (leave empty)

        # Column 20: sh:defaultValue
        default_value = property_row.get('Default value', '')
        if pd.notna(default_value) and default_value != 'nan':
            new_row[20] = default_value

        # Column 21: sh:pattern (duplicate, leave empty)

        # Column 22: dash:viewer
        viewer = property_row.get('dash.viewer', '')
        if pd.notna(viewer) and viewer != 'nan':
            new_row[22] = viewer

        # Column 23: dash:editor
        editor = property_row.get('dash.editor', '')
        if pd.notna(editor) and editor != 'nan':
            # Check if we need to override to EnumSelectEditor for controlled vocabs
            if pd.notna(vocab_url) and vocab_url != 'nan':
                vocab_mapping = get_vocab_mapping(vocab_url)
                if vocab_mapping:
                    new_row[23] = vocab_mapping['editor']
                else:
                    new_row[23] = editor
            else:
                new_row[23] = editor

        return new_row

    def get_prefixes_dataframe(self) -> pd.DataFrame:
        """
        Get the prefixes DataFrame from the template.

        Returns:
            DataFrame with prefixes
        """
        return self.prefixes_df.copy()
