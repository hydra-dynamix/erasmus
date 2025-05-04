import re
import xml.etree.ElementTree as ET
from typing import Any


def _sanitize_string(name: str | None) -> str:
    """Sanitize a string by removing emoji and non-ASCII characters while preserving valid markdown characters.
    Returns an ASCII-safe string suitable for filenames.
    """
    # Handle None or empty input
    if not name:
        return "p_empty"
    
    # Convert to string to handle any input type
    name = str(name)

    # First remove emoji using regex pattern
    no_emoji = re.sub(r"[\U0001F300-\U0001F9FF]", "", name)

    # Replace any non-alphanumeric character (including special characters like *) with underscore
    sanitized = re.sub(r"[^a-zA-Z0-9]", "_", no_emoji)

    # Collapse multiple underscores
    sanitized = re.sub(r"_+", "_", sanitized)

    # Ensure it starts with a letter
    if not sanitized or not sanitized[0].isalpha():
        sanitized = "p_" + sanitized

    # Strip trailing underscores
    sanitized = sanitized.rstrip("_")

    # Ensure non-empty result
    return sanitized or "p_empty"


def _sanitize_xml_content(xml_content: str) -> str:
    """Sanitize XML content by ensuring it's well-formed and safe.

    Args:
        xml_content: The XML content to sanitize

    Returns:
        Sanitized XML content
    """
    # Replace invalid XML characters
    # XML 1.0 specification allows: #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
    # We'll replace control characters and other invalid characters
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", xml_content)

    # Replace invalid XML entities
    sanitized = re.sub(r"&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", sanitized)

    # Ensure the XML is well-formed
    try:
        # Try to parse the XML to ensure it's well-formed
        ET.fromstring(sanitized)
        return sanitized
    except ET.ParseError:
        # If parsing fails, try to fix common issues
        # Add XML declaration if missing
        if not sanitized.strip().startswith("<?xml"):
            sanitized = '<?xml version="1.0" encoding="UTF-8"?>\n' + sanitized

        # Try to parse again
        try:
            ET.fromstring(sanitized)
            return sanitized
        except ET.ParseError:
            # If still failing, return a minimal valid XML
            return '<?xml version="1.0" encoding="UTF-8"?>\n<root></root>'


def _sanitize_xml_attribute(value: str) -> str:
    """Sanitize a string for use as an XML attribute value.

    Args:
        value: The attribute value to sanitize

    Returns:
        Sanitized attribute value
    """
    # Replace special XML characters with their entities
    sanitized = value.replace("&", "&amp;")
    sanitized = sanitized.replace("<", "&lt;")
    sanitized = sanitized.replace(">", "&gt;")
    sanitized = sanitized.replace('"', "&quot;")
    sanitized = sanitized.replace("'", "&apos;")

    # Remove invalid XML characters
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized)

    return sanitized


def _sanitize_xml_tag(tag: str) -> str:
    """Sanitize a string for use as an XML tag name.

    Args:
        tag: The tag name to sanitize

    Returns:
        Sanitized tag name
    """
    # XML tag names must start with a letter or underscore
    if not tag or not (tag[0].isalpha() or tag[0] == "_"):
        tag = "x_" + tag

    # Replace invalid characters with underscores
    sanitized = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", tag)

    # Ensure it's a valid XML name
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_\-\.]*$", sanitized):
        sanitized = "x_" + sanitized

    return sanitized


def sanitize_for_xml(value: Any) -> str:
    """Sanitize a value for use in XML.

    Args:
        value: The value to sanitize

    Returns:
        Sanitized value as a string
    """
    if value is None:
        return ""

    # Convert to string
    str_value = str(value)

    # Replace special XML characters with their entities
    sanitized = str_value.replace("&", "&amp;")
    sanitized = sanitized.replace("<", "&lt;")
    sanitized = sanitized.replace(">", "&gt;")
    sanitized = sanitized.replace('"', "&quot;")
    sanitized = sanitized.replace("'", "&apos;")

    # Remove invalid XML characters
    sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized)

    return sanitized
