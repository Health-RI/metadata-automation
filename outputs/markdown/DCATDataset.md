

# Class: DCATDataset 


_A collection of data, published or curated by a single source, and available for access or download in one or more representations._





URI: [dcat:Dataset](https://www.w3.org/ns/dcat#Dataset)

## Slots

| Name | Cardinality and Range | Description | Inheritance |
| ---  | --- | --- | --- |
| [distribution](distribution.md) | * <br/> [AnyHttpUrl](AnyHttpUrl.md) | An available distribution of the dataset | direct |
| [frequency](frequency.md) | 0..1 <br/> [String](String.md)&nbsp;or&nbsp;<br />[AnyHttpUrl](AnyHttpUrl.md)&nbsp;or&nbsp;<br />[Frequency](Frequency.md) | The frequency at which a dataset is published | direct |
| [in_series](in_series.md) | * <br/> [AnyHttpUrl](AnyHttpUrl.md) | A dataset series of which the dataset is part | direct |
| [spatial_resolution](spatial_resolution.md) | * <br/> [Float](Float.md) | Minimum spatial separation resolvable in a dataset, measured in meters | direct |
| [temporal_resolution](temporal_resolution.md) | 0..1 <br/> [String](String.md)&nbsp;or&nbsp;<br />[String](String.md)&nbsp;or&nbsp;<br />[LiteralField](LiteralField.md) | Minimum time period resolvable in the dataset | direct |
| [was_generated_by](was_generated_by.md) | * <br/> [String](String.md)&nbsp;or&nbsp;<br />[AnyHttpUrl](AnyHttpUrl.md)&nbsp;or&nbsp;<br />[Activity](Activity.md) | An activity that generated, or provides the business context for, the creatio... | direct |
| [access_rights_dataset](access_rights_dataset.md) | 0..1 <br/> [AnyHttpUrl](AnyHttpUrl.md) | Information about who can access the dataset and under what conditions | direct |
