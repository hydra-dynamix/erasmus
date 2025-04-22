import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


def parse_xml_file(file_path: Union[str, Path]) -> ET.Element:
    """
    Parse an XML file and return the root element.

    Args:
        file_path: Path to the XML file

    Returns:
        The root element of the XML document

    Raises:
        FileNotFoundError: If the file doesn't exist
        ET.ParseError: If the XML is not well-formed
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"XML file not found: {file_path}")

    try:
        tree = ET.parse(file_path)
        return tree.getroot()
    except ET.ParseError as parse_error:
        raise ET.ParseError(f"Error parsing XML file {file_path}: {parse_error}")


def parse_xml_string(xml_string: str) -> ET.Element:
    """
    Parse an XML string and return the root element.

    Args:
        xml_string: The XML content as a string

    Returns:
        The root element of the XML document

    Raises:
        ET.ParseError: If the XML is not well-formed
    """
    try:
        return ET.fromstring(xml_string)
    except ET.ParseError as parse_error:
        raise ET.ParseError(f"Error parsing XML string: {parse_error}")


def get_element_text(root: ET.Element, xpath: str, default: Any = None) -> Any:
    """
    Get the text content of an element using XPath.

    Args:
        root: The root element of the XML document
        xpath: XPath expression to find the element
        default: Default value to return if the element is not found

    Returns:
        The text content of the element, or the default value if not found
    """
    element = root.find(xpath)
    if element is None:
        return default
    return element.text


def get_element_attribute(root: ET.Element, xpath: str, attribute: str, default: Any = None) -> Any:
    """
    Get the value of an attribute using XPath.

    Args:
        root: The root element of the XML document
        xpath: XPath expression to find the element
        attribute: Name of the attribute
        default: Default value to return if the attribute is not found

    Returns:
        The value of the attribute, or the default value if not found
    """
    element = root.find(xpath)
    if element is None:
        return default
    return element.get(attribute, default)


def get_elements(root: ET.Element, xpath: str) -> list[ET.Element]:
    """
    Get all elements matching an XPath expression.

    Args:
        root: The root element of the XML document
        xpath: XPath expression to find the elements

    Returns:
        A list of elements matching the XPath expression
    """
    return root.findall(xpath)


def get_element_texts(root: ET.Element, xpath: str) -> list[str]:
    """
    Get the text content of all elements matching an XPath expression.

    Args:
        root: The root element of the XML document
        xpath: XPath expression to find the elements

    Returns:
        A list of text content from elements matching the XPath expression
    """
    elements = get_elements(root, xpath)
    return [element.text for element in elements if element.text]


def get_architecture_title(file_path: Union[str, Path]) -> str | None:
    """
    Extract the title from an architecture XML document.

    Args:
        file_path: Path to the architecture XML file

    Returns:
        The title of the architecture, or None if not found
    """
    try:
        root = parse_xml_file(file_path)
        # Try different possible locations for the title
        title = get_element_text(root, ".//Title")
        if title:
            return title

        title = get_element_text(root, ".//MetaAgent/Title")
        if title:
            return title

        title = get_element_text(root, ".//Overview/Title")
        if title:
            return title

        return None
    except (FileNotFoundError, ET.ParseError):
        return None


def get_protocol_name(file_path: Union[str, Path]) -> str | None:
    """
    Extract the protocol name from a protocol XML document.

    Args:
        file_path: Path to the protocol XML file

    Returns:
        The name of the protocol, or None if not found
    """
    try:
        root = parse_xml_file(file_path)
        # Try different possible locations for the protocol name
        name = get_element_text(root, ".//Name")
        if name:
            return name

        name = get_element_text(root, ".//Protocol/Name")
        if name:
            return name

        return None
    except (FileNotFoundError, ET.ParseError):
        return None


def xml_to_dict(element: ET.Element) -> dict[str, Any]:
    """
    Convert an XML element to a dictionary.

    Args:
        element: The XML element to convert

    Returns:
        A dictionary representation of the XML element
    """
    result = {}

    # Add attributes
    for attribute_key, attribute_value in element.attrib.items():
        result[f"@{attribute_key}"] = attribute_value

    # Add text content if it exists and is not just whitespace
    if element.text and element.text.strip():
        result["#text"] = element.text.strip()

    # Add child elements
    for child_element in element:
        child_dict = xml_to_dict(child_element)
        child_tag = child_element.tag

        # Handle multiple children with the same tag
        if child_tag in result:
            if isinstance(result[child_tag], list):
                result[child_tag].append(child_dict)
            else:
                result[child_tag] = [result[child_tag], child_dict]
        else:
            result[child_tag] = child_dict

    return result
