from pathlib import Path
import shutil

import pandas as pd
import yaml
from typing import List, Optional, Union


class LinkMLCreator():
    def __init__(self, output_path: Path) -> None:
        self.output_path = output_path
        self.filtered_sheets = None
        self.prefixes = {}
        self.table_classes = None
        self.linkml_data = {}
        self.validation_logic = self._load_validation_logic()

    def _load_validation_logic(self) -> dict:
        """Load validation logic from YAML file if it exists."""
        validation_logic_path = Path("./inputs/sempyro/validation_logic.yaml")

        if not validation_logic_path.exists():
            return {}

        try:
            with open(validation_logic_path, 'r', encoding='utf-8') as file:
                validation_data = yaml.safe_load(file)
                return validation_data.get('classes', {}) if validation_data else {}
        except Exception as e:
            print(f"Warning: Could not load validation logic: {e}")
            return {}

    def load_excel(self, file_path: str, exclude_sheets: Optional[List[str]] = None) -> None:
        """
        Load an Excel file and return a dictionary of sheet data.

        Args:
            file_path: Path to the Excel file
            exclude_sheets: List of sheet names to exclude from the result

        Returns:
            Dictionary with sheet names as keys and DataFrame objects as values
        """
        if exclude_sheets is None:
            exclude_sheets = []

        # Read all sheets from the Excel file
        all_sheets = pd.read_excel(file_path, sheet_name=None, dtype=str)

        # Filter out excluded sheets
        self.filtered_sheets = {
            sheet_name: sheet_data.astype(str)
            for sheet_name, sheet_data in all_sheets.items()
            if sheet_name not in exclude_sheets
        }

        # Sheet with prefixes: 'prefixes'
        table_prefixes = self.filtered_sheets['prefixes']
        table_prefixes = table_prefixes.map(lambda x: x.strip())
        self.prefixes = dict(zip(table_prefixes['prefix'], table_prefixes['namespace']))
        # Sheet with a table 'classes'
        # sheet_name, ontology_name, inherits_from
        # Dataset, dcat:Dataset, dcat:Resource
        # Ontology names should also reflect application profiles. E.g., Health-RI Dataset should be hri:Dataset
        self.table_classes = self.filtered_sheets['classes']

    def _create_id(self, ontology: str, ontology_class: str) -> str:
        return f"{self.prefixes[ontology]}{ontology_class}"

    def _create_class_id(self, ontology: str, ontology_class: str) -> str:
        return f"{ontology.upper()}{ontology_class.capitalize()}"

    def _create_path(self, ontology: str, ontology_class: str) -> Path:
        return self.output_path / self._create_rel_path(ontology, ontology_class)

    @staticmethod
    def _create_rel_path(ontology: str, ontology_class: str) -> Path:
        return Path(f"./{ontology}/{ontology}-{ontology_class}.yaml")

    def _ontology_name_to_class_name(self, ontology_name: str) -> str:
        ontology = ontology_name.strip().split(':')[0]
        ontology_class = ontology_name.strip().split(':')[1]
        return f"{ontology.upper()}{ontology_class.capitalize()}"

    def build_base(self):
        for index, row in self.table_classes.iterrows():
            self.build_base_class(row)

    def build_sempyro(self):
        for index, row in self.table_classes.iterrows():
            self.build_base_class(row)
            self.build_sempyro_class(row)

    def build_base_class(self, row):
        ontology_name = row['ontology_name']
        class_description = row.get('description')

        ontology = ontology_name.split(':')[0]
        ontology_class = ontology_name.split(':')[1]

        linkml_id = self._create_id(ontology, ontology_class)
        self.linkml_data[linkml_id] = {}
        self.linkml_data[linkml_id]['path'] = self._create_path(ontology, ontology_class)
        self.linkml_data[linkml_id]['rel_path'] = self._create_rel_path(ontology, ontology_class)
        self.linkml_data[linkml_id]['data'] = {}
        self.linkml_data[linkml_id]['data']['id'] = linkml_id
        self.linkml_data[linkml_id]['data']['title'] = ontology_name.replace(':', '-')
        self.linkml_data[linkml_id]['data']['description'] = class_description if class_description != 'nan' else ontology_name.replace(':', '-')
        self.linkml_data[linkml_id]['data']['prefixes'] = self.prefixes
        self.linkml_data[linkml_id]['data']['imports'] = ['linkml:types']

    def build_sempyro_class(self, row):
        sheet_name = row['sheet_name']
        ontology_name = row['ontology_name']
        inherits_from = row.get('inherits_from')
        class_description = str(row.get('description'))
        import_classes = row.get('import_classes').split(',') if (
                row.get('import_classes') and row.get('import_classes') != 'nan') else []
        add_rdf_model = row.get('Sempyro_add_rdf_model')

        ontology = ontology_name.split(':')[0]
        ontology_class = ontology_name.split(':')[1]

        linkml_id = self._create_id(ontology, ontology_class)

        # Add Sempyro types
        self.linkml_data[linkml_id]['data']['imports'].append("../sempyro_types")

        # Add RDF model import if needed
        if add_rdf_model and str(add_rdf_model).lower() in ['true', '1', 'yes']:
            self.linkml_data[linkml_id]['data']['imports'].append("../rdf_model")

        annotations = {
            'ontology': row['annotations_ontology'],
            'IRI': f"\"{row['annotations_IRI']}\"",
            'namespace': ontology.upper(),
            'prefix': ontology
        }

        # Apply validation logic if available
        class_id = self._create_class_id(ontology, ontology_class)
        if class_id in self.validation_logic:
            validation_annotations = self.validation_logic[class_id].get('annotations', {})
            annotations.update(validation_annotations)

        class_sheet = self.filtered_sheets[sheet_name]
        class_slots = []

        slots = {}
        for index, slot_row in class_sheet.iterrows():
            if slot_row['Property label'] == 'nan':
                continue
            slot_name = slot_row['Property label'].replace(' ','_')
            class_slots.append(slot_name)

            # Handle comma-separated range values
            sempyro_range = slot_row['Sempyro range']
            slot_def = {
                'description': slot_row['Definition'],
                'slot_uri': slot_row['Property URI'],
                'annotations': {
                    'rdf_term': slot_row['rdf_term'],
                    'rdf_type': slot_row['rdf_type'],
                },
                'required': (str(slot_row['Cardinality']) == '1' or str(slot_row['Cardinality']) == '1..n'),
                'multivalued': (str(slot_row['Cardinality']) == '0..n' or str(slot_row['Cardinality']) == '1..n')
            }

            # Check if range contains comma-separated values
            if ',' in str(sempyro_range):
                # Split and strip whitespace from each range value
                range_values = [r.strip() for r in sempyro_range.split(',')]
                # Use any_of to create Union type in LinkML
                slot_def['any_of'] = [{'range': r} for r in range_values]
            else:
                slot_def['range'] = sempyro_range

            slots[slot_name] = slot_def

        class_dict = {
            'class_uri': ontology_name,
            'annotations': annotations,
            'slots': class_slots
        }


        if class_description and class_description != 'nan':
            class_dict['description'] = class_description

        class_stubs = {}
        for item in import_classes:
            stub_class_name = self._ontology_name_to_class_name(item)
            class_stubs[stub_class_name] = {
                'class_uri': item
            }
        if inherits_from and str(inherits_from) != 'nan':
            class_dict['is_a'] = self._ontology_name_to_class_name(inherits_from)
            class_stubs[self._ontology_name_to_class_name(inherits_from)] = {
                'class_uri': inherits_from
            }
        # Add RDFModel inheritance if Sempyro_add_rdf_model is true
        elif add_rdf_model and str(add_rdf_model).lower() in ['true', '1', 'yes']:
            class_dict['is_a'] = 'RDFModel'

        # Combine main class with stubs
        all_classes = {
            self._create_class_id(ontology, ontology_class): class_dict
        }
        all_classes.update(class_stubs)

        self.linkml_data[linkml_id]['data']['classes'] = all_classes
        self.linkml_data[linkml_id]['data']['slots'] = slots

    def write_to_file(self):
        # Check if any schema uses RDFModel import
        needs_rdf_model = any(
            '../rdf_model' in linkml_dict['data'].get('imports', [])
            for linkml_dict in self.linkml_data.values()
        )

        # Check if any schema uses sempyro_types import
        needs_sempyro_types = any(
            '../sempyro_types' in linkml_dict['data'].get('imports', [])
            for linkml_dict in self.linkml_data.values()
        )

        for linkml_dict in self.linkml_data.values():
            linkml_path = linkml_dict['path']
            linkml_data = linkml_dict['data']

            # Create directories if they don't exist
            linkml_path.parent.mkdir(parents=True, exist_ok=True)

            # Write linkml_data as YAML to linkml_path
            with open(linkml_path, 'w') as f:
                yaml.dump(linkml_data, f, default_flow_style=False, sort_keys=False)

            print(f"Written {linkml_path}")

        # Copy rdf_model.yaml if needed
        if needs_rdf_model:
            rdf_model_source = Path("./inputs/sempyro/rdf_model.yaml")
            rdf_model_dest = self.output_path / "rdf_model.yaml"

            if rdf_model_source.exists():
                shutil.copy2(rdf_model_source, rdf_model_dest)
                print(f"Copied {rdf_model_source} to {rdf_model_dest}")
            else:
                print(f"Warning: RDF model source file not found at {rdf_model_source}")

        # Copy sempyro_types.yaml if needed
        if needs_sempyro_types:
            sempyro_types_source = Path("./inputs/sempyro/sempyro_types.yaml")
            sempyro_types_dest = self.output_path / "sempyro_types.yaml"

            if sempyro_types_source.exists():
                shutil.copy2(sempyro_types_source, sempyro_types_dest)
                print(f"Copied {sempyro_types_source} to {sempyro_types_dest}")
            else:
                print(f"Warning: Sempyro types source file not found at {sempyro_types_source}")
