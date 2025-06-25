from linkml.generators.pydanticgen import PydanticGenerator
from linkml.generators.pydanticgen.template import Import, ObjectImport, Imports

# Define custom imports
imports_dcat_resource = (
    Imports() +
    Import(module="logging") +
    Import(module="abc", objects=[ObjectImport(name="ABCMeta")]) +
    Import(module="datetime", objects=[
        ObjectImport(name="date"),
        ObjectImport(name="datetime")
    ]) +
    Import(module="enum", objects=[ObjectImport(name="Enum")]) +
    Import(module="pathlib", objects=[ObjectImport(name="Path")]) +
    Import(module="typing", objects=[
        ObjectImport(name="List"),
        ObjectImport(name="Union"),
        ObjectImport(name="Optional"),
        ObjectImport(name="ClassVar"),
        ObjectImport(name="Set")
    ]) +
    Import(module="pydantic", objects=[
        ObjectImport(name="AnyHttpUrl"),
        ObjectImport(name="AwareDatetime"),
        ObjectImport(name="ConfigDict"),
        ObjectImport(name="Field"),
        ObjectImport(name="NaiveDatetime"),
        ObjectImport(name="field_validator")
    ]) +
    Import(module="rdflib", objects=[
        ObjectImport(name="DCAT"),
        ObjectImport(name="DCTERMS"),
        ObjectImport(name="ODRL2"),
        ObjectImport(name="PROV"),
        ObjectImport(name="URIRef")
    ]) +
    Import(module="sempyro", objects=[
        ObjectImport(name="LiteralField"),
        ObjectImport(name="RDFModel")
    ]) +
    Import(module="sempyro.foaf", objects=[ObjectImport(name="Agent")]) +
    Import(module="sempyro.geo", objects=[ObjectImport(name="Location")]) +
    Import(module="sempyro.namespaces", objects=[
        ObjectImport(name="ADMS"),
        ObjectImport(name="ADMSStatus"),
        ObjectImport(name="DCATv3")
    ]) +
    Import(module="sempyro.odrl", objects=[ObjectImport(name="ODRLPolicy")]) +
    Import(module="sempyro.time", objects=[ObjectImport(name="PeriodOfTime")]) +
    Import(module="sempyro.utils.validator_functions", objects=[
        ObjectImport(name="date_handler"),
        ObjectImport(name="convert_to_literal")
    ]) +
    Import(module="sempyro.vcard", objects=[ObjectImport(name="VCard")])
)

imports_dcat_dataset = (
    Imports() +
    Import(module="enum", objects=[ObjectImport(name="Enum")]) +
    Import(module="pathlib", objects=[ObjectImport(name="Path")]) +
    Import(module="typing", objects=[
        ObjectImport(name="List"),
        ObjectImport(name="Union"),
        ObjectImport(name="Optional")
    ]) +
    Import(module="pydantic", objects=[
        ObjectImport(name="AnyHttpUrl"),
        ObjectImport(name="ConfigDict"),
        ObjectImport(name="Field"),
        ObjectImport(name="field_validator")
    ]) +
    Import(module="rdflib.namespace", objects=[
        ObjectImport(name="DCAT"),
        ObjectImport(name="DCTERMS"),
        ObjectImport(name="PROV")
    ]) +
    Import(module="sempyro", objects=[ObjectImport(name="LiteralField")]) +
    Import(module="sempyro.dcat", objects=[ObjectImport(name="DCATResource")]) +
    Import(module="sempyro.namespaces", objects=[
        ObjectImport(name="FREQ"),
        ObjectImport(name="DCATv3")
    ]) +
    Import(module="sempyro.prov", objects=[ObjectImport(name="Activity")])
)


# Generate with custom imports
generator = PydanticGenerator(
    schema="./linkml-definitions/dcat/dcat_resource.yaml",
    imports=imports_dcat_resource,
    black=True,
    template_dir="./templates/sempyro",
    mergeimports=False
)

with open("./sempyro_classes/dcat/dcat_resource.py", 'w') as fname:
    fname.write(generator.serialize())

generator = PydanticGenerator(
    schema="./linkml-definitions/dcat/dcat_dataset.yaml",
    imports=imports_dcat_dataset,
    black=True,
    template_dir="./templates/sempyro",
    mergeimports=False
)

with open("./sempyro_classes/dcat/dcat_dataset.py", 'w') as fname:
    fname.write(generator.serialize())