import yaml
from linkml.generators import ShaclGenerator

def remove_sempyro_annotations(link_dict):
    schema_path = link_dict['schema_path']

    try:
        # Read original schema
        with open(schema_path, 'r', encoding='utf-8') as file:
            schema_data = yaml.safe_load(file)

        # Remove annotations from classes
        if 'classes' in schema_data:
            for class_name, class_info in schema_data['classes'].items():
                if 'annotations' in class_info:
                    annotations = class_info['annotations']
                    # Remove the specified annotations
                    for annotation_key in ['ontology', 'namespace', 'IRI', 'prefix']:
                        annotations.pop(annotation_key, None)
                    # Remove annotations dict if empty
                    if annotations:
                        class_info['annotations'] = annotations
                    else:
                        del class_info['annotations']
                    schema_data['classes'][class_name] = class_info

        # Remove annotations from slots
        if 'slots' in schema_data:
            for slot_name, slot_info in schema_data['slots'].items():
                if 'annotations' in slot_info:
                    annotations = slot_info['annotations']
                    # Remove the specified annotations
                    for annotation_key in ['rdf_term', 'rdf_type']:
                        annotations.pop(annotation_key, None)
                    # Remove annotations dict if empty
                    if annotations:
                        slot_info['annotations'] = annotations
                    else:
                        del slot_info['annotations']
                    schema_data['slots'][slot_name] = slot_info


        with open(schema_path, 'w', encoding='utf-8') as file:
            yaml.dump(schema_data, file, default_flow_style=False, sort_keys=False, indent=2)

        print(f"Removed SeMPyRO annotations from {schema_path}")

    except Exception as e:
        print(f"Warning: Could remove SeMPyRO annotations: {e}")
    return None


def generate_from_linkml(link_dict):
    print(f"Generating from {link_dict['schema_path']}...")

    generator = ShaclGenerator(
        schema=link_dict['schema_path'],
        include_annotations=True
    )

    with open(link_dict['output_path'], 'w') as fname:
        fname.write(generator.serialize())
    print("Done.")