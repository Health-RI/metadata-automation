from metadata_automation.utils import create_temp_definition, remove_temp_definitions, copy_temp_types
from metadata_automation.shacl.utils import generate_from_linkml, remove_sempyro_annotations

link_dicts = [
    {
        "schema_path": "./linkml-definitions/dcat/dcat_resource.yaml",
        "output_path": "./outputs/shacl_shapes/dcat_resource.ttl",
    },
    {
        "schema_path": "./linkml-definitions/dcat/dcat_dataset.yaml",
        "output_path": "./outputs/shacl_shapes/dcat_dataset.ttl"
    },
    {
        "schema_path": "./linkml-definitions/vcard/dcat_vcard.yaml",
        "output_path": "./outputs/shacl_shapes/dcat_vcard.ttl",
    },
    {
        "schema_path": "./linkml-definitions/foaf/foaf_agent.yaml",
        "output_path": "./outputs/shacl_shapes/foaf_agent.ttl",
    },
]

copy_temp_types()

for link_dict in link_dicts:
    link_dict = create_temp_definition(link_dict)
    remove_sempyro_annotations(link_dict)

for link_dict in link_dicts:
    generate_from_linkml(link_dict)

remove_temp_definitions()
