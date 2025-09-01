from os import mkdir
from pathlib import Path

from metadata_automation.utils import remove_temp_definitions, copy_temp_types, TEMP_FOLDER
from metadata_automation.linkml.creator import LinkMLCreator
from metadata_automation.shacl.utils import generate_from_linkml, remove_empty_node_shapes, remove_redundant_constraints, fix_uri_node_kinds, remove_ignored_properties, remove_anyuri_datatype

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

for link_dict in link_dicts:
    generate_from_linkml(link_dict)
    remove_empty_node_shapes(link_dict['output_path'])
    remove_redundant_constraints(link_dict['output_path'])
    fix_uri_node_kinds(link_dict['output_path'])
    remove_ignored_properties(link_dict['output_path'])
    remove_anyuri_datatype(link_dict['output_path'])
    # Remove class stubs: Read in file, remove all sh:nodeShapes without properties, write back file
    # Remove sh:class: Read in file, for every property, when 'sh:node' is defined, remove 'sh:class' and 'sh:nodeKind'.
    #

remove_temp_definitions()
