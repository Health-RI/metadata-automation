import os


from inputs.sempyro.imports import imports_dcat_dataset, imports_dcat_resource
from metadata_automation.utils import create_temp_definition, remove_temp_definitions
from metadata_automation.sempyro.cleanup import remove_unwanted_classes
from metadata_automation.sempyro.utils import add_rdf_model_to_yaml, generate_from_linkml, add_validation_logic_to_schema

from pathlib import Path

import shutil

link_dicts = [
    {
        "schema_path": "./linkml-definitions/dcat/dcat_resource.yaml",
        "imports": imports_dcat_resource,
        "output_path": "./outputs/sempyro_classes/dcat/dcat_resource.py",
        "add_rdf_model_to_class": ['DCATResource']
    },
    {
        "schema_path": "./linkml-definitions/dcat/dcat_dataset.yaml",
        "imports": imports_dcat_dataset,
        "output_path": "./outputs/sempyro_classes/dcat/dcat_dataset.py"
    },
    {
        "schema_path": "./linkml-definitions/vcard/dcat_vcard.yaml",
        "imports": imports_dcat_dataset,
        "output_path": "./outputs/sempyro_classes/vcard/dcat_vcard.py",
        "add_rdf_model_to_class": ['DCATVCard']
    },
    {
        "schema_path": "./linkml-definitions/foaf/foaf_agent.yaml",
        "imports": imports_dcat_dataset,
        "output_path": "./outputs/sempyro_classes/foaf/foaf_agent.py",
        "add_rdf_model_to_class": ['FOAFAgent']
    },
]

for link_dict in link_dicts:
    link_dict = create_temp_definition(link_dict)
    add_rdf_model_to_yaml(link_dict)
    add_validation_logic_to_schema(link_dict)
    generate_from_linkml(link_dict)
    remove_unwanted_classes(Path(link_dict['output_path']), Path(link_dict['schema_path']))

remove_temp_definitions()
