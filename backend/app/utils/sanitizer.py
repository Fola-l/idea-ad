import re
from typing import Any, Dict


def sanitize_for_meta(text: str) -> str:
    """
    Sanitize text for Meta Marketing API.

    Facebook will throw errors on unescaped special characters.
    This must be applied to every string field before it touches the API.
    """
    if not isinstance(text, str):
        return text

    # Remove duplicate escape sequences first
    text = re.sub(r'\\\\', '', text)

    # Escape remaining backslashes
    text = re.sub(r'(?<!\\)\\(?!\\)', r'\\\\', text)

    # Escape double quotes
    text = text.replace('"', '\\"')

    # Remove control characters
    text = re.sub(r'[\x00-\x1f\x7f]', '', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def sanitize_dict_for_meta(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively sanitize all string values in a dictionary for Meta API.
    """
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_for_meta(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict_for_meta(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict_for_meta(item) if isinstance(item, dict)
                else sanitize_for_meta(item) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized
