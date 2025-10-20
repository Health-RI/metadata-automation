from metadata_automation.linkml.creator import LinkMLCreator

from inputs.sempyro.imports import imports_dcat_dataset, imports_dcat_resource
from metadata_automation.sempyro.cleanup import remove_unwanted_classes
from metadata_automation.sempyro.utils import generate_from_linkml

from pathlib import Path

excel_file_path = "./inputs/EUCAIM.xlsx"
exclude_sheets = ['Info', 'User Guide']

linkml_output_path = Path("./outputs/linkml")
linkml_creator = LinkMLCreator(linkml_output_path)
linkml_creator.load_excel(excel_file_path, exclude_sheets)
linkml_creator.build_sempyro()
linkml_creator.write_to_file()

linkml_definitions_path = Path("./outputs/linkml")

link_dicts = [
    {
        "schema_path": linkml_definitions_path / "eucaim" / "eucaim-Dataset.yaml",
        "imports": imports_dcat_resource,
        "output_path": "./outputs/sempyro_classes/eucaim/eucaim-Dataset.py",
    },
    # {
    #     "schema_path": linkml_definitions_path / "hri" / "hri-Kind.yaml",
    #     "imports": imports_dcat_resource,
    #     "output_path": "./outputs/sempyro_classes/hri/hri-Kind.py",
    # },
    # {
    #     "schema_path": linkml_definitions_path / "dcat" / "dcat_resource.yaml",
    #     "imports": imports_dcat_resource,
    #     "output_path": "./outputs/sempyro_classes/dcat/dcat_resource.py",
    # },
    # {
    #     "schema_path": linkml_definitions_path / "dcat" / "dcat_dataset.yaml",
    #     "imports": imports_dcat_dataset,
    #     "output_path": "./outputs/sempyro_classes/dcat/dcat_dataset.py"
    # },
    # {
    #     "schema_path": linkml_definitions_path / "vcard" / "dcat_vcard.yaml",
    #     "imports": imports_dcat_dataset,
    #     "output_path": "./outputs/sempyro_classes/vcard/dcat_vcard.py",
    # },
    # {
    #     "schema_path": linkml_definitions_path / "foaf" / "foaf_agent.yaml",
    #     "imports": imports_dcat_dataset,
    #     "output_path": "./outputs/sempyro_classes/foaf/foaf_agent.py",
    # },
]

for link_dict in link_dicts:
    generate_from_linkml(link_dict)
    remove_unwanted_classes(Path(link_dict['output_path']), Path(link_dict['schema_path']))
