"""
Controlled vocabulary mappings for SHACLPlay generation.

Maps controlled vocabulary URLs to their corresponding sh:in value lists
and appropriate dash:editor settings.
"""

import re

VOCAB_MAPPINGS = {
    "http://publications.europa.eu/resource/authority/access-right": {
        "sh_in": "( <http://publications.europa.eu/resource/authority/access-right/PUBLIC> "
        + "<http://publications.europa.eu/resource/authority/access-right/RESTRICTED> "
        + "<http://publications.europa.eu/resource/authority/access-right/NON_PUBLIC> )",
        "editor": "dash:EnumSelectEditor",
        "example_property": "access rights",
    },
    "http://publications.europa.eu/resource/authority/distribution-status": {
        "sh_in": "( <http://publications.europa.eu/resource/authority/distribution-status/COMPLETED> "
        + "<http://publications.europa.eu/resource/authority/distribution-status/DEVELOP> "
        + "<http://publications.europa.eu/resource/authority/distribution-status/WITHDRAWN> "
        + "<http://publications.europa.eu/resource/authority/distribution-status/PLANNED> "
        + "<http://publications.europa.eu/resource/authority/distribution-status/ARCHIVE> "
        + "<http://publications.europa.eu/resource/authority/distribution-status/ONGOING> "
        + "<http://publications.europa.eu/resource/authority/distribution-status/REQUIRED> "
        + "<http://publications.europa.eu/resource/authority/distribution-status/OP_DATPRO> "
        + "<http://publications.europa.eu/resource/authority/distribution-status/DEPRECATED> )",
        "editor": "dash:EnumSelectEditor",
        "example_property": "status",
    },
    # Add more mappings as they are discovered or manually specified
    # Format: URL -> {'sh_in': '( value1 value2 ... )', 'editor': 'dash:EnumSelectEditor'}
}


URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")
TRAILING_PUNCTUATION = ".,;:)]}"


def _normalize_url(url: str) -> str:
    """Normalize a URL for matching: ignore scheme (http/https) and trailing slashes."""
    return re.sub(r"^https?://", "", url.strip()).rstrip("/")


_NORMALIZED_MAPPINGS = {_normalize_url(url): mapping for url, mapping in VOCAB_MAPPINGS.items()}


def get_vocab_mapping(vocab_url: object) -> dict | None:
    """
    Get the sh:in mapping for a controlled vocabulary URL.

    Args:
        vocab_url: The controlled vocabulary URL

    Returns:
        Dictionary with 'sh_in' and 'editor' keys, or None if not found
    """
    if not isinstance(vocab_url, str):
        return None
    return _NORMALIZED_MAPPINGS.get(_normalize_url(vocab_url))


def find_vocab_mapping(cell_text: object, hyperlink: object = None) -> dict | None:
    """
    Find the sh:in mapping for a controlled vocabulary cell.

    Tries, in order: the cell's hyperlink target, the full cell text,
    and any URLs contained in the cell text.

    Args:
        cell_text: Text of the controlled vocabulary cell
        hyperlink: Hyperlink target of the cell, if any

    Returns:
        Dictionary with 'sh_in' and 'editor' keys, or None if not found
    """
    candidates = []
    for source in (hyperlink, cell_text):
        if isinstance(source, str):
            urls = [url.rstrip(TRAILING_PUNCTUATION) for url in URL_PATTERN.findall(source)]
            candidates += [source, *urls]
    for candidate in candidates:
        mapping = get_vocab_mapping(candidate)
        if mapping:
            return mapping
    return None


def has_vocab_mapping(vocab_url: object) -> bool:
    """
    Check if a controlled vocabulary URL has a known mapping.

    Args:
        vocab_url: The controlled vocabulary URL

    Returns:
        True if mapping exists, False otherwise
    """
    return get_vocab_mapping(vocab_url) is not None
