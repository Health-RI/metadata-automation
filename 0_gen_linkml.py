from pathlib import Path

from metadata_automation.linkml.creator import LinkMLCreator


excel_file_path = "./inputs/Health-RI-Metadata_CoreGenericHealth_v2-0-0.xlsx"
exclude_sheets = ['Info', 'User Guide']

# linkml_output_path = Path("./linkml-definitions")
linkml_output_path = Path("./temp-linkml")
linkml_creator = LinkMLCreator(linkml_output_path)
linkml_creator.load_excel(excel_file_path, exclude_sheets)
linkml_creator.build_shacl()
linkml_creator.write_to_file()
