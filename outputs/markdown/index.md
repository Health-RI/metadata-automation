# DCAT Dataset Schema

LinkML schema for DCAT Dataset model

URI: https://example.org/dcat-dataset

Name: dcat-dataset



## Classes

| Class | Description |
| --- | --- |
| [Agent](Agent.md) |  |
| [DCATResource](DCATResource.md) | Resource published or curated by a single agent |
| &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;[DCATDataset](DCATDataset.md) | A collection of data, published or curated by a single source, and available ... |
| [DCATVCard](DCATVCard.md) | A vCard-style representation of an agent (person or organization) |



## Slots

| Slot | Description |
| --- | --- |
| [access_rights](access_rights.md) | Information about who can access the resource or an indication of its securit... |
| [access_rights_dataset](access_rights_dataset.md) | Information about who can access the dataset and under what conditions |
| [conforms_to](conforms_to.md) | An established standard to which the described resource conforms |
| [contact_point](contact_point.md) | Relevant contact information for the cataloged resource |
| [country](country.md) |  |
| [creator](creator.md) | The entity responsible for producing the resource |
| [description](description.md) | An account of the resource |
| [distribution](distribution.md) | An available distribution of the dataset |
| [email](email.md) |  |
| [first](first.md) | The first resource in an ordered collection or series of resources, to which ... |
| [foaf_identifier](foaf_identifier.md) |  |
| [foaf_type](foaf_type.md) |  |
| [formatted_name](formatted_name.md) | The full name of the object (as a single string) |
| [frequency](frequency.md) | The frequency at which a dataset is published |
| [geographical_coverage](geographical_coverage.md) | The geographical area covered by the dataset |
| [has_current_version](has_current_version.md) | This resource has a more specific, versioned resource with equivalent content... |
| [has_part](has_part.md) | A related resource that is included either physically or logically in the des... |
| [has_policy](has_policy.md) | An ODRL conformant policy expressing the rights associated with the resource |
| [has_version](has_version.md) | This resource has a more specific, versioned resource |
| [hasEmail](hasEmail.md) | The email address as a mailto URI |
| [hasUID](hasUID.md) | A unique identifier for the object |
| [identifier](identifier.md) | A unique identifier of the resource being described or cataloged |
| [in_series](in_series.md) | A dataset series of which the dataset is part |
| [is_referenced_by](is_referenced_by.md) | A related resource, such as a publication, that references, cites, or otherwi... |
| [keyword](keyword.md) | A keyword or tag describing the resource |
| [landing_page](landing_page.md) | A Web page that can be navigated to in a Web browser to gain access to the ca... |
| [language](language.md) | A language of the resource |
| [last](last.md) | The last resource in an ordered collection or series of resources, to which t... |
| [license](license.md) | A legal document under which the resource is made available |
| [modification_date](modification_date.md) | Most recent date on which the resource was changed, updated or modified |
| [name](name.md) |  |
| [previous](previous.md) | The previous resource (before the current one) in an ordered collection or se... |
| [previous_version](previous_version.md) | The previous version of a resource in a lineage [PAV] |
| [publisher](publisher.md) | The entity responsible for making the resource available |
| [publisher_note](publisher_note.md) |  |
| [publisher_type](publisher_type.md) |  |
| [qualified_attribution](qualified_attribution.md) | Link to an Agent having some form of responsibility for the resource |
| [qualified_relation](qualified_relation.md) | Link to a description of a relationship with another resource |
| [relation](relation.md) | A resource with an unspecified relationship to the cataloged resource |
| [release_date](release_date.md) | Date of formal issuance (e |
| [replaces](replaces.md) | A related resource that is supplanted, displaced, or superseded by the descri... |
| [rights](rights.md) | Information about rights held in and over the distribution |
| [spatial_resolution](spatial_resolution.md) | Minimum spatial separation resolvable in a dataset, measured in meters |
| [status](status.md) | The status of the resource in the context of a particular workflow process [V... |
| [temporal_coverage](temporal_coverage.md) | The temporal period that the dataset covers |
| [temporal_resolution](temporal_resolution.md) | Minimum time period resolvable in the dataset |
| [theme](theme.md) | A main category of the resource |
| [title](title.md) | A name given to the resource |
| [type](type.md) | The nature or genre of the resource |
| [url](url.md) |  |
| [version](version.md) | The version indicator (name or identifier) of a resource |
| [version_notes](version_notes.md) | A description of changes between this version and the previous version of the... |
| [was_generated_by](was_generated_by.md) | An activity that generated, or provides the business context for, the creatio... |


## Enumerations

| Enumeration | Description |
| --- | --- |
| [AccessRights](AccessRights.md) | Access rights enumeration |
| [Frequency](Frequency.md) | Frequency enumeration |
| [Status](Status.md) | Status enumeration for ADMS |


## Types

| Type | Description |
| --- | --- |
| [Activity](Activity.md) | A PROV Activity |
| [AnyHttpUrl](AnyHttpUrl.md) | A valid HTTP URL |
| [AwareDatetime](AwareDatetime.md) |  |
| [Boolean](Boolean.md) | A binary (true or false) value |
| [Curie](Curie.md) | a compact URI |
| [Date](Date.md) | a date (year, month and day) in an idealized calendar |
| [DateOrDatetime](DateOrDatetime.md) | Either a date or a datetime |
| [Datetime](Datetime.md) | The combination of a date and time |
| [Decimal](Decimal.md) | A real number with arbitrary precision that conforms to the xsd:decimal speci... |
| [Double](Double.md) | A real number that conforms to the xsd:double specification |
| [Float](Float.md) | A real number that conforms to the xsd:float specification |
| [Integer](Integer.md) | An integer |
| [Jsonpath](Jsonpath.md) | A string encoding a JSON Path |
| [Jsonpointer](Jsonpointer.md) | A string encoding a JSON Pointer |
| [LiteralField](LiteralField.md) | A literal field with language and datatype support |
| [Location](Location.md) | A geographical location |
| [NaiveDatetime](NaiveDatetime.md) |  |
| [Ncname](Ncname.md) | Prefix part of CURIE |
| [Nodeidentifier](Nodeidentifier.md) | A URI, CURIE or BNODE that represents a node in a model |
| [Objectidentifier](Objectidentifier.md) | A URI or CURIE that represents an object in the model |
| [ODRLPolicy](ODRLPolicy.md) | An ODRL conformant policy |
| [PeriodOfTime](PeriodOfTime.md) | A temporal period |
| [Sparqlpath](Sparqlpath.md) | A string encoding a SPARQL Property Path |
| [String](String.md) | A character string |
| [Time](Time.md) | A time object represents a (local) time of day, independent of any particular... |
| [Uri](Uri.md) | a complete URI |
| [Uriorcurie](Uriorcurie.md) | a URI or a CURIE |
| [VCard](VCard.md) | vCard contact information |


## Subsets

| Subset | Description |
| --- | --- |
