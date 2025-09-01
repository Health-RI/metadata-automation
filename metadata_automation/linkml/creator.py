from pathlib import Path

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

    def build_shacl(self):
        for index, row in self.table_classes.iterrows():
            self.build_base_class(row)
            self.build_shacl_class(row)

    def build_sempyro(self):
        for index, row in self.table_classes.iterrows():
            self.build_base_class(row)
            self.build_sempyro_class(row)

    def build_base_class(self, row):
        ontology_name = row['ontology_name']
        inherits_from = row.get('inherits_from')
        class_description = row.get('description')
        # import_classes = row.get('import_classes').split(',') if (
        #         row.get('import_classes') and row.get('import_classes') != 'nan') else []

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

        # Handle imports for inheritance
        # if inherits_from and str(inherits_from) != 'nan':
        #     inherits_ontology = inherits_from.split(':')[0]
        #     inherits_class = inherits_from.split(':')[1]

        #     if inherits_ontology == ontology:
        #         # Same ontology - import from same folder
        #         import_path = f"{inherits_ontology}-{inherits_class}"
        #     else:
        #         # Different ontology - go up one folder and into the other ontology folder
        #         import_path = f"../{inherits_ontology}/{inherits_ontology}-{inherits_class}"

        #     self.linkml_data[linkml_id]['data']['imports'].append(import_path)

        # Handle other imports
        # for item in import_classes:
        #     import_ontology = item.strip().split(':')[0]
        #     import_class = item.strip().split(':')[1]

        #     if import_ontology == ontology:
        #         # Same ontology - import from same folder
        #         import_path = f"{import_ontology}-{import_class}"
        #     else:
        #         # Different ontology - go up one folder and into the other ontology folder
        #         import_path = f"../{import_ontology}/{import_ontology}-{import_class}"

        #     self.linkml_data[linkml_id]['data']['imports'].append(import_path)

    def build_shacl_class(self, row):
        sheet_name = row['sheet_name']
        ontology_name = row['ontology_name']
        ontology = ontology_name.split(':')[0]
        ontology_class = ontology_name.split(':')[1]
        inherits_from = row.get('inherits_from')
        class_description = str(row.get('description'))
        import_classes = row.get('import_classes').split(',') if (
                row.get('import_classes') and row.get('import_classes') != 'nan') else []

        target_ontology_name = row['target_ontology_name']

        linkml_id = self._create_id(ontology, ontology_class)

        class_sheet = self.filtered_sheets[sheet_name]
        class_slots = []

        slots = {}
        for index, slot_row in class_sheet.iterrows():
            if slot_row['Property label'] == 'nan':
                continue
            slot_name = slot_row['Property label'].replace(' ', '_')
            class_slots.append(slot_name)
            slots[slot_name] = {
                'title': slot_row['Property label'],
                'description': slot_row['Definition'],
                'slot_uri': slot_row['Property URI'],
                'annotations': {},
                'required': (str(slot_row['Cardinality']) == '1' or str(slot_row['Cardinality']) == '1..n'),
                'multivalued': (str(slot_row['Cardinality']) == '0..n' or str(slot_row['Cardinality']) == '1..n')
            }
            if slot_row['dash.viewer'] and slot_row['dash.viewer'] != "nan":
                slots[slot_name]['annotations']['dash:viewer'] = slot_row['dash.viewer']
                slots[slot_name]['annotations']['dash:editor'] = slot_row['dash.editor']

            if slot_row['SHACL range'] and slot_row['SHACL range'] != 'nan':
                slots[slot_name]['range'] = slot_row['SHACL range'] if ':' not in slot_row['SHACL range'] else self._ontology_name_to_class_name(slot_row['SHACL range'])

            if ':' in slot_row['SHACL range']:
                slots[slot_name]['annotations']['sh:node'] = f"{slot_row['SHACL range']}Shape"

            if slot_row['Pattern'] and slot_row['Pattern'] != 'nan':
                slots[slot_name]['pattern'] = slot_row['Pattern']

            if slot_row['Default value'] and slot_row['Default value'] != 'nan':
                slots[slot_name]['ifabsent'] = slot_row['Default value']

        class_dict = {
            'class_uri': ontology_name,
            'slots': class_slots,
            'annotations': {'sh:targetClass':target_ontology_name}
        }

        if class_description and class_description != 'nan':
            class_dict['description'] = class_description

        # Create class stubs for imported classes (for SHACL generation)
        class_stubs = {}
        for item in import_classes:
            stub_class_name = self._ontology_name_to_class_name(item)
            class_stubs[stub_class_name] = {
                'class_uri': item
            }

        # Combine main class with stubs
        all_classes = {
            f"{ontology.upper()}{ontology_class.capitalize()}": class_dict
        }
        all_classes.update(class_stubs)

        # Add custom XSD types needed for SHACL
        self.linkml_data[linkml_id]['data']['types'] = {
            'nonNegativeInteger': {
                'uri': 'xsd:nonNegativeInteger',
                'base': 'int'
            },
            'duration': {
                'uri': 'xsd:duration',
                'base': 'str'
            }
        }

        self.linkml_data[linkml_id]['data']['classes'] = all_classes
        self.linkml_data[linkml_id]['data']['slots'] = slots


    def build_sempyro_class(self, row):
        # TODO: Add validation logic
        # TODO: Add RDF model to class
        sheet_name = row['sheet_name']
        ontology_name = row['ontology_name']
        inherits_from = row.get('inherits_from')
        class_description = str(row.get('description'))
        import_classes = row.get('import_classes').split(',') if (
                row.get('import_classes') and row.get('import_classes') != 'nan') else []

        ontology = ontology_name.split(':')[0]
        ontology_class = ontology_name.split(':')[1]

        linkml_id = self._create_id(ontology, ontology_class)
        self.linkml_data[linkml_id]['data']['imports'].append("../rdf-model")

        annotations = {
            'ontology': row['annotations_ontology'],
            'IRI': row['annotations_IRI'],
            'namespace': ontology.upper(),
            'prefix': ontology
        }

        class_sheet = self.filtered_sheets[sheet_name]
        class_slots = []

        slots = {}
        for index, slot_row in class_sheet.iterrows():
            if slot_row['Property label'] == 'nan':
                continue
            slot_name = slot_row['Property label'].replace(' ','_')
            class_slots.append(slot_name)
            slots[slot_name] = {
                'description': slot_row['Definition'],
                'slot_uri': slot_row['Property URI'],
                'range': slot_row['Sempyro range'],
                'annotations': {
                    'rdf_term': slot_row['rdf_term'],
                    'rdf_type': slot_row['rdf_type'],
                },
                'required': (str(slot_row['Cardinality']) == '1' or str(slot_row['Cardinality']) == '1..n'),
                'multivalued': (str(slot_row['Cardinality']) == '0..n' or str(slot_row['Cardinality']) == '1..n')
            }

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

        # Combine main class with stubs
        all_classes = {
            f"{ontology.upper()}{ontology_class.capitalize()}": class_dict
        }
        all_classes.update(class_stubs)

        self.linkml_data[linkml_id]['data']['slots'] = slots

    def write_to_file(self):
        for linkml_dict in self.linkml_data.values():
            linkml_path = linkml_dict['path']
            linkml_data = linkml_dict['data']

            # Create directories if they don't exist
            linkml_path.parent.mkdir(parents=True, exist_ok=True)

            # Write linkml_data as YAML to linkml_path
            with open(linkml_path, 'w') as f:
                yaml.dump(linkml_data, f, default_flow_style=False, sort_keys=False)

            print(f"Written {linkml_path}")
