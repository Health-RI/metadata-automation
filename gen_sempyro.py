from metadata_automation.linkml.creator import LinkMLCreator

from metadata_automation.sempyro.cleanup import remove_unwanted_classes
from metadata_automation.sempyro.utils import generate_from_linkml, load_yaml

from pathlib import Path

# excel_file_path = "./inputs/EUCAIM.xlsx"
excel_file_path = "./inputs/Metadata_CoreGenericHealth_v2.xlsx"
exclude_sheets = ['Info', 'User Guide']

linkml_output_path = Path("./outputs/linkml")
linkml_creator = LinkMLCreator(linkml_output_path)
linkml_creator.load_excel(excel_file_path, exclude_sheets)
linkml_creator.build_sempyro()
linkml_creator.write_to_file()

linkml_definitions_path = Path("./outputs/linkml")

imports_path = Path("./inputs/sempyro/imports.yaml")
imports = load_yaml(imports_path)

link_dicts = [
    {
        "schema_path": linkml_definitions_path / "hri" / "hri-Dataset.yaml",
        "imports": imports['hri-Dataset'],
        "output_path": "./outputs/sempyro_classes/hri/hri-Dataset.py",
    },
    {
        "schema_path": linkml_definitions_path / "hri" / "hri-Agent.yaml",
        "imports": imports['hri-Agent'],
        "output_path": "./outputs/sempyro_classes/hri/hri-Agent.py",
    },
    {
        "schema_path": linkml_definitions_path / "hri" / "hri-Catalog.yaml",
        "imports": imports['hri-Catalog'],
        "output_path": "./outputs/sempyro_classes/hri/hri-Catalog.py",
    },
    {
        "schema_path": linkml_definitions_path / "hri" / "hri-Kind.yaml",
        "imports": imports['hri-Kind'],
        "output_path": "./outputs/sempyro_classes/hri/hri-Kind.py",
    },
    {
        "schema_path": linkml_definitions_path / "hri" / "hri-Distribution.yaml",
        "imports": imports['hri-Distribution'],
        "output_path": "./outputs/sempyro_classes/hri/hri-Distribution.py",
    },
    {
        "schema_path": linkml_definitions_path / "hri" / "hri-Datasetseries.yaml",
        "imports": imports['hri-Datasetseries'],
        "output_path": "./outputs/sempyro_classes/hri/hri-Datasetseries.py",
    },
    {
        "schema_path": linkml_definitions_path / "hri" / "hri-Dataservice.yaml",
        "imports": imports['hri-Dataservice'],
        "output_path": "./outputs/sempyro_classes/hri/hri-Dataservice.py",
    },
    {
        "schema_path": linkml_definitions_path / "hri" / "hri-Identifier.yaml",
        "imports": imports['hri-Identifier'],
        "output_path": "./outputs/sempyro_classes/hri/hri-Identifier.py",
    },
    {
        "schema_path": linkml_definitions_path / "hri" / "hri-PeriodOfTime.yaml",
        "imports": imports['hri-PeriodOfTime'],
        "output_path": "./outputs/sempyro_classes/hri/hri-PeriodOfTime.py",
    },
    {
        "schema_path": linkml_definitions_path / "hri" / "hri-Attribution.yaml",
        "imports": imports['hri-Attribution'],
        "output_path": "./outputs/sempyro_classes/hri/hri-Attribution.py",
    },
    {
        "schema_path": linkml_definitions_path / "hri" / "hri-Relationship.yaml",
        "imports": imports['hri-Relationship'],
        "output_path": "./outputs/sempyro_classes/hri/hri-Relationship.py",
    },
    {
        "schema_path": linkml_definitions_path / "hri" / "hri-QualityCertificate.yaml",
        "imports": imports['hri-QualityCertificate'],
        "output_path": "./outputs/sempyro_classes/hri/hri-QualityCertificate.py",
    },
    {
        "schema_path": linkml_definitions_path / "hri" / "hri-Checksum.yaml",
        "imports": imports['hri-Checksum'],
        "output_path": "./outputs/sempyro_classes/hri/hri-Checksum.py",
    },
]

for link_dict in link_dicts:
    generate_from_linkml(link_dict)
    remove_unwanted_classes(Path(link_dict['output_path']), Path(link_dict['schema_path']))
