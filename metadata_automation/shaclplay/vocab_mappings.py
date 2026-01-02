"""
Controlled vocabulary mappings for SHACLPlay generation.

Maps controlled vocabulary URLs to their corresponding sh:in value lists
and appropriate dash:editor settings.
"""

VOCAB_MAPPINGS = {
    "http://publications.europa.eu/resource/authority/access-right": {
        "sh_in": "( eu:PUBLIC eu:RESTRICTED eu:NON_PUBLIC )",
        "editor": "dash:EnumSelectEditor",
        "example_property": "access rights",
    },
    # Add more mappings as they are discovered or manually specified
    # Format: URL -> {'sh_in': '( value1 value2 ... )', 'editor': 'dash:EnumSelectEditor'}
}


def get_vocab_mapping(vocab_url: str) -> dict:
    """
    Get the sh:in mapping for a controlled vocabulary URL.

    Args:
        vocab_url: The controlled vocabulary URL

    Returns:
        Dictionary with 'sh_in' and 'editor' keys, or None if not found
    """
    return VOCAB_MAPPINGS.get(vocab_url)


def has_vocab_mapping(vocab_url: str) -> bool:
    """
    Check if a controlled vocabulary URL has a known mapping.

    Args:
        vocab_url: The controlled vocabulary URL

    Returns:
        True if mapping exists, False otherwise
    """
    return vocab_url in VOCAB_MAPPINGS
