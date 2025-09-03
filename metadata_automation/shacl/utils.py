from pathlib import Path

import yaml
from linkml.generators import ShaclGenerator
from rdflib import Namespace, Graph, RDF


def remove_sempyro_annotations(link_dict):
    schema_path = link_dict['schema_path']

    try:
        # Read original schema
        with open(schema_path, 'r', encoding='utf-8') as file:
            schema_data = yaml.safe_load(file)

        # Remove annotations from classes
        if 'classes' in schema_data:
            for class_name, class_info in schema_data['classes'].items():
                if 'annotations' in class_info:
                    annotations = class_info['annotations']
                    # Remove the specified annotations
                    for annotation_key in ['ontology', 'namespace', 'IRI', 'prefix']:
                        annotations.pop(annotation_key, None)
                    # Remove annotations dict if empty
                    if annotations:
                        class_info['annotations'] = annotations
                    else:
                        del class_info['annotations']
                    schema_data['classes'][class_name] = class_info

        # Remove annotations from slots
        if 'slots' in schema_data:
            for slot_name, slot_info in schema_data['slots'].items():
                if 'annotations' in slot_info:
                    annotations = slot_info['annotations']
                    # Remove the specified annotations
                    for annotation_key in ['rdf_term', 'rdf_type']:
                        annotations.pop(annotation_key, None)
                    # Remove annotations dict if empty
                    if annotations:
                        slot_info['annotations'] = annotations
                    else:
                        del slot_info['annotations']
                    schema_data['slots'][slot_name] = slot_info


        with open(schema_path, 'w', encoding='utf-8') as file:
            yaml.dump(schema_data, file, default_flow_style=False, sort_keys=False, indent=2)

        print(f"Removed SeMPyRO annotations from {schema_path}")

    except Exception as e:
        print(f"Warning: Could remove SeMPyRO annotations: {e}")
    return None


def generate_from_linkml(link_dict):
    print(f"Generating from {link_dict['schema_path']}...")

    generator = ShaclGenerator(
        schema=link_dict['schema_path'],
        include_annotations=True,
        suffix="Shape",
        mergeimports=False,
        closed=False
    )

    Path(link_dict['output_path']).parent.mkdir(parents=True, exist_ok=True)

    with open(link_dict['output_path'], 'w') as fname:
        fname.write(generator.serialize())
    print("Done.")


def remove_empty_node_shapes(shacl_file_path):
    """
    Remove sh:NodeShapes that have no properties from a SHACL file and clean up orphaned blank nodes.
    """
    from rdflib import BNode

    SH = Namespace("http://www.w3.org/ns/shacl#")

    # Load the SHACL file
    g = Graph()
    g.parse(shacl_file_path, format="turtle")

    # Find all NodeShapes
    node_shapes = list(g.subjects(RDF.type, SH.NodeShape))

    # Check each NodeShape for properties
    for node_shape in node_shapes:
        has_properties = bool(list(g.triples((node_shape, SH.property, None))))

        # If no properties, remove this NodeShape and all its triples
        if not has_properties:
            # Remove all triples where this NodeShape is the subject
            triples_to_remove = list(g.triples((node_shape, None, None)))
            for triple in triples_to_remove:
                g.remove(triple)
            print(f"Removed empty NodeShape: {node_shape}")

    # Clean up orphaned blank nodes
    # Find all blank nodes in the graph
    all_blank_nodes = {node for node in g.all_nodes() if isinstance(node, BNode)}

    # Find blank nodes that are referenced (appear as objects)
    referenced_blank_nodes = {obj for subj, pred, obj in g if isinstance(obj, BNode)}

    # Find orphaned blank nodes (not referenced by anything)
    orphaned_blank_nodes = all_blank_nodes - referenced_blank_nodes

    # Remove orphaned blank nodes and their triples
    for blank_node in orphaned_blank_nodes:
        triples_to_remove = list(g.triples((blank_node, None, None)))
        for triple in triples_to_remove:
            g.remove(triple)
        if triples_to_remove:
            print(f"Removed orphaned blank node with {len(triples_to_remove)} triples")

    # Write back to file
    g.serialize(destination=shacl_file_path, format="turtle")


def remove_redundant_constraints(shacl_file_path):
    """
    Remove sh:class and sh:nodeKind from properties that have sh:node defined.
    """
    SH = Namespace("http://www.w3.org/ns/shacl#")

    # Load the SHACL file
    g = Graph()
    g.parse(shacl_file_path, format="turtle")

    # Find all properties that have sh:node
    properties_with_node = []
    for subj, pred, obj in g.triples((None, SH.property, None)):
        # obj is a blank node representing the property
        if list(g.triples((obj, SH.node, None))):
            properties_with_node.append(obj)

    # Remove sh:class and sh:nodeKind from these properties
    for prop in properties_with_node:
        # Remove sh:class triples
        class_triples = list(g.triples((prop, SH['class'], None)))
        for triple in class_triples:
            g.remove(triple)
            print(f"Removed sh:class from property with sh:node")

        # Remove sh:nodeKind triples
        nodekind_triples = list(g.triples((prop, SH.nodeKind, None)))
        for triple in nodekind_triples:
            g.remove(triple)
            print(f"Removed sh:nodeKind from property with sh:node")

    # Write back to file
    g.serialize(destination=shacl_file_path, format="turtle")


def fix_uri_node_kinds(shacl_file_path):
    """
    Change sh:nodeKind to sh:IRI for properties that have sh:datatype xsd:anyURI.
    """
    SH = Namespace("http://www.w3.org/ns/shacl#")
    XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
    
    # Load the SHACL file
    g = Graph()
    g.parse(shacl_file_path, format="turtle")
    
    # Find all properties that have sh:datatype xsd:anyURI
    properties_with_anyuri = []
    for subj, pred, obj in g.triples((None, SH.property, None)):
        # obj is a blank node representing the property
        if list(g.triples((obj, SH.datatype, XSD.anyURI))):
            properties_with_anyuri.append(obj)
    
    # Change sh:nodeKind to sh:IRI for these properties
    for prop in properties_with_anyuri:
        # Remove existing sh:nodeKind triples
        nodekind_triples = list(g.triples((prop, SH.nodeKind, None)))
        for triple in nodekind_triples:
            g.remove(triple)
        
        # Add sh:nodeKind sh:IRI
        g.add((prop, SH.nodeKind, SH.IRI))
        print(f"Changed sh:nodeKind to sh:IRI for xsd:anyURI property")
    
    # Write back to file
    g.serialize(destination=shacl_file_path, format="turtle")


def remove_ignored_properties(shacl_file_path):
    """
    Remove sh:ignoredProperties from all sh:NodeShapes in a SHACL file.
    """
    SH = Namespace("http://www.w3.org/ns/shacl#")
    
    # Load the SHACL file
    g = Graph()
    g.parse(shacl_file_path, format="turtle")
    
    # Find all NodeShapes
    node_shapes = list(g.subjects(RDF.type, SH.NodeShape))
    
    # Remove sh:ignoredProperties from each NodeShape
    for node_shape in node_shapes:
        ignored_props_triples = list(g.triples((node_shape, SH.ignoredProperties, None)))
        for triple in ignored_props_triples:
            g.remove(triple)
            print(f"Removed sh:ignoredProperties from {node_shape}")
    
    # Write back to file
    g.serialize(destination=shacl_file_path, format="turtle")


def remove_closed_properties(shacl_file_path):
    """
    Remove sh:closed from all sh:NodeShapes in a SHACL file.
    """
    SH = Namespace("http://www.w3.org/ns/shacl#")

    # Load the SHACL file
    g = Graph()
    g.parse(shacl_file_path, format="turtle")

    # Find all NodeShapes
    node_shapes = list(g.subjects(RDF.type, SH.NodeShape))

    # Remove sh:closed from each NodeShape
    for node_shape in node_shapes:
        closed_props_triples = list(g.triples((node_shape, SH.closed, None)))
        for triple in closed_props_triples:
            g.remove(triple)
            print(f"Removed sh:closed from {node_shape}")

    # Write back to file
    g.serialize(destination=shacl_file_path, format="turtle")


def remove_anyuri_datatype(shacl_file_path):
    """
    Remove sh:datatype xsd:anyURI from properties that have it defined.
    """
    SH = Namespace("http://www.w3.org/ns/shacl#")
    XSD = Namespace("http://www.w3.org/2001/XMLSchema#")
    
    # Load the SHACL file
    g = Graph()
    g.parse(shacl_file_path, format="turtle")
    
    # Find all properties that have sh:datatype xsd:anyURI
    properties_with_anyuri = []
    for subj, pred, obj in g.triples((None, SH.property, None)):
        # obj is a blank node representing the property
        if list(g.triples((obj, SH.datatype, XSD.anyURI))):
            properties_with_anyuri.append(obj)
    
    # Remove sh:datatype xsd:anyURI from these properties
    for prop in properties_with_anyuri:
        datatype_triples = list(g.triples((prop, SH.datatype, XSD.anyURI)))
        for triple in datatype_triples:
            g.remove(triple)
            print(f"Removed sh:datatype xsd:anyURI from property")
    
    # Write back to file
    g.serialize(destination=shacl_file_path, format="turtle")
