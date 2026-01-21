metadata-automation shaclplay -i ./inputs/HealthRI_v2.0.2.xlsx -o ./outputs/shaclplay -n hri
metadata-automation shacl-from-shaclplay -i ./outputs/shaclplay -o ./outputs/shacl_shapes