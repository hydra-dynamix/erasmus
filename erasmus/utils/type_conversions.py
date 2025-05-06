import typing
import re
from types import NoneType, UnionType # UnionType for Python 3.10+ `|` syntax
from pydantic import BaseModel # Assuming Pydantic models might be type objects

def py_type_to_js_type_string(py_type: any) -> str:
    """
    Converts a Python type object to its JavaScript/TypeScript type string representation.
    """
    # Direct type checks for common built-ins
    if py_type is str:
        return "string"
    if py_type is int or py_type is float:
        return "number"
    if py_type is bool:
        return "boolean"
    if py_type is NoneType or py_type is None: # NoneType is type(None)
        return "null" # TypeScript common practice for optional or nullable

    if py_type is typing.Any:
        return "any"

    origin = typing.get_origin(py_type)
    args = typing.get_args(py_type)

    if origin: # It's a generic type from the typing module
        if origin is list or origin is set: # Covers List[T], Set[T]
            if args:
                element_type_str = python_type_to_js_type_string(args[0])
                return f"Array<{element_type_str}>" # Common: Array<Type>, alternative: Type[]
            return "Array<any>"
        
        if origin is tuple: # Covers Tuple[T1, T2, ...] or Tuple[T, ...]
            if args:
                if len(args) == 2 and args[1] is Ellipsis: # Tuple[SomeType, ...]
                    element_type_str = python_type_to_js_type_string(args[0])
                    return f"Array<{element_type_str}>" # Represent as an array of SomeType
                # Fixed-length tuple: Tuple[str, int] -> [string, number]
                element_types_str = [python_type_to_js_type_string(arg) for arg in args]
                return f"[{', '.join(element_types_str)}]"
            return "Array<any>" # Default for bare tuple or unknown elements

        if origin is dict: # Covers Dict[K, V]
            if args and len(args) == 2:
                key_type_str = python_type_to_js_type_string(args[0])
                value_type_str = python_type_to_js_type_string(args[1])
                # TypeScript Record keys are typically string, number, or symbol.
                # For simplicity, if key isn't string/number, we might default or ensure it.
                if key_type_str not in ["string", "number"]:
                     # This simplification might depend on actual key types used.
                     # For broad compatibility, string is a safe bet for JS object keys.
                    key_type_str = "string"
                return f"Record<{key_type_str}, {value_type_str}>"
            return "object" # More generic: Record<string, any> or { [key: string]: any; }

        if origin is typing.Literal:
            if args:
                literal_values = []
                for arg in args:
                    if isinstance(arg, str):
                        literal_values.append(f'"{arg}"') # String literals in quotes
                    elif isinstance(arg, bool):
                        literal_values.append(str(arg).lower()) # true / false
                    elif isinstance(arg, (int, float)):
                        literal_values.append(str(arg))
                    elif arg is None:
                        literal_values.append("null")
                    else: # Fallback for other literal types if any
                        literal_values.append(str(arg))
                return " | ".join(literal_values)
            return "any" # Should not happen for a valid Literal

        if origin is typing.Union or origin is UnionType: # UnionType for Python 3.10+ X | Y
            if args:
                # Special handling for Optional[X] -> Union[X, NoneType]
                if len(args) == 2 and NoneType in args:
                    non_none_arg = args[0] if args[1] is NoneType else args[1]
                    return f"{python_type_to_js_type_string(non_none_arg)} | null"
                
                member_types = sorted(list(set(python_type_to_js_type_string(arg) for arg in args)))
                return " | ".join(member_types)
            return "any" # Should not occur for a valid Union

    # Handle non-generic built-in collection types (error.g., `list` passed directly)
    if py_type is list or py_type is set or py_type is tuple:
        return "Array<any>"
    if py_type is dict:
        return "object" # Or Record<string, any>

    # Check for Pydantic models or other classes
    # (Python 3.9+ check for class type)
    if isinstance(py_type, type): # Check if it's a class
        try:
            if issubclass(py_type, BaseModel): # Pydantic BaseModel
                return py_type.__name__ # Use the class name, implies an interface/type definition
        except TypeError: # py_type might not be a class (error.g. an instance, though type hint should be a class)
            pass 
        
        # For other custom classes not inheriting BaseModel
        if hasattr(py_type, '__name__'):
            return py_type.__name__ # Assumes it maps to a defined interface/class name in JS/TS

    return "any" # Default fallback if type is not recognized


def js_type_string_to_py_type(js_type_str: str, custom_type_map: dict[str, type] | None = None) -> any:
    """
    Converts a JavaScript/TypeScript type string to its Python type object representation.

    Args:
        js_type_str: The JavaScript/TypeScript type string (error.g., "string", "Array<number>", "MyInterface | null").
        custom_type_map: An optional dictionary to map custom type names (like interface names)
                         to actual Python type objects (error.g., Pydantic models).

    Returns:
        The corresponding Python type object, or typing.Any if parsing fails.
    """
    if custom_type_map is None:
        custom_type_map = {}

    original_str = js_type_str.strip()

    # Handle unions first, as they can contain other complex types
    if "|" in original_str:
        parts = [part.strip() for part in original_str.split("|")]
        # Handle Optional-like pattern: "SomeType | null" or "null | SomeType"
        if "null" in parts and len(parts) == 2:
            other_part = parts[0] if parts[1] == "null" else parts[1]
            return typing.Optional[js_type_string_to_py_type(other_part, custom_type_map)] # type: ignore
        
        python_types = []
        for part in parts:
            py_type = js_type_string_to_py_type(part, custom_type_map)
            if py_type is not typing.Any: # Avoid adding Any to the union if it's a failure of a part
                python_types.append(py_type)
            else: # If one part is Any, the whole union might as well be Any for simplicity, or handle error
                return typing.Any 
        if not python_types:
            return typing.Any
        if len(python_types) == 1:
            return python_types[0]
        # In Python 3.10+, use UnionType for | operator. For older, use typing.Union.
        if hasattr(typing, 'Union'): # Check for older Python versions
             # Canonical form by filtering NoneType and sorting would be good, but complex here
            return typing.Union[tuple(python_types)] # type: ignore
        else: # Should be Python 3.10+ where types.UnionType exists
            # This requires Python 3.10+ for the | syntax with types
            # For now, stick to typing.Union for wider compatibility in construction
            # Actual | operator would be: functools.reduce(lambda x, y: x | y, python_types)
            return typing.Union[tuple(python_types)] # type: ignore

    # Basic type mapping
    if original_str == "string":
        return str
    if original_str == "number":
        return float # Or int, float is generally more flexible for "number"
    if original_str == "boolean":
        return bool
    if original_str == "any" or original_str == "unknown":
        return typing.Any
    if original_str == "null" or original_str == "undefined": # undefined often maps to None or Optional in Python
        return NoneType
    if original_str == "object": # Generic object
        return dict

    # Array<Type> or Type[]
    array_match_generic = re.fullmatch(r"Array<(.+?)>", original_str)
    array_match_shorthand = re.fullmatch(r"(.+?)\[\]", original_str)
    array_match = array_match_generic or array_match_shorthand
    if array_match:
        element_type_str = array_match.group(1).strip()
        element_py_type = js_type_string_to_py_type(element_type_str, custom_type_map)
        return typing.List[element_py_type] # type: ignore

    # Record<KeyType, ValueType>
    record_match = re.fullmatch(r"Record<(.+?),\s*(.+?)>", original_str)
    if record_match:
        key_type_str = record_match.group(1).strip()
        value_type_str = record_match.group(2).strip()
        # Python dicts don't enforce key types as strictly as TS Record key types
        # We'll parse them but typically Python dicts use str or int keys
        key_py_type = js_type_string_to_py_type(key_type_str, custom_type_map)
        value_py_type = js_type_string_to_py_type(value_type_str, custom_type_map)
        return typing.Dict[key_py_type, value_py_type] # type: ignore

    # Fixed-length tuple: [string, number]
    tuple_match = re.fullmatch(r"\[(.+?)\]", original_str)
    if tuple_match:
        elements_str = tuple_match.group(1).strip()
        if not elements_str: # Empty array [] -> empty tuple or list of any
            return typing.Tuple[()]
        element_types_str = [e.strip() for e in elements_str.split(',')]
        element_py_types = [js_type_string_to_py_type(ets, custom_type_map) for ets in element_types_str]
        return typing.Tuple[tuple(element_py_types)] # type: ignore

    # Literal types: "value1" | "value2" | 123 | true
    # This is partly handled by the union logic, but a single literal needs parsing too.
    # For simplicity, if it's a quoted string or a number/boolean not caught by basic types, it might be a literal.
    # Proper literal parsing would involve checking if it's part of a union.
    # This basic version assumes single literals aren't distinctively marked beyond their value representation.
    # A true literal type in Python involves typing.Literal.
    # error.g. typing.Literal['cat', 'dog']
    # This function doesn't reconstruct typing.Literal from "cat" | "dog" directly
    # into a *single* typing.Literal object, but the union logic handles the parts.
    # A single "cat" without union would need context to be typing.Literal['cat'].

    # Check custom type map (error.g., for interface names, Pydantic models)
    if original_str in custom_type_map:
        return custom_type_map[original_str]

    # Fallback for unrecognized types, potentially custom class names not in map
    # Could attempt to return the string itself if a direct class name is expected
    # but for now, it's safer to return Any to indicate it wasn't fully resolved.
    return typing.Any

