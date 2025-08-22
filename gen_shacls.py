from os import mkdir
from pathlib import Path

from metadata_automation.utils import create_temp_definition, remove_temp_definitions, copy_temp_types, TEMP_FOLDER
from metadata_automation.linkml.creator import LinkMLCreator
from metadata_automation.shacl.utils import generate_from_linkml, remove_sempyro_annotations


# link_dicts = [
#     {
#         "schema_path": "./linkml-definitions/dcat/dcat_resource.yaml",
#         "output_path": "./outputs/shacl_shapes/dcat_resource.ttl",
#     },
#     {
#         "schema_path": "./linkml-definitions/dcat/dcat_dataset.yaml",
#         "output_path": "./outputs/shacl_shapes/dcat_dataset.ttl"
#     },
#     {
#         "schema_path": "./linkml-definitions/vcard/dcat_vcard.yaml",
#         "output_path": "./outputs/shacl_shapes/dcat_vcard.ttl",
#     },
#     {
#         "schema_path": "./linkml-definitions/foaf/foaf_agent.yaml",
#         "output_path": "./outputs/shacl_shapes/foaf_agent.ttl",
#     },
# ]

excel_file_path = "./inputs/Health-RI-Metadata_CoreGenericHealth_v2-0-0.xlsx"
exclude_sheets = ['Info', 'User Guide']
shacl_output_path = Path('./outputs/shacl_shapes/')

if not shacl_output_path.exists():
    mkdir(shacl_output_path)

copy_temp_types()

linkml_creator = LinkMLCreator(TEMP_FOLDER)
linkml_creator.load_excel(excel_file_path, exclude_sheets)
linkml_creator.build_shacl()
linkml_creator.write_to_file()

link_dicts = []
for linkml_dict in linkml_creator.linkml_data.values():
    link_dicts.append({
        'schema_path': linkml_dict['path'],
        'output_path': (shacl_output_path / linkml_dict['rel_path']).with_suffix('.ttl')
    })

# for link_dict in link_dicts:
#     link_dict = create_temp_definition(link_dict)
#     remove_sempyro_annotations(link_dict)

for link_dict in link_dicts:
    generate_from_linkml(link_dict)

remove_temp_definitions()
