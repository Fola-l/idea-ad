from urllib.parse import urlencode, urlparse, parse_qs, urlunparse
from typing import Dict, Optional


def build_utm_url(base_url: str, utm_params: Dict[str, str]) -> str:
    """
    Build a URL with UTM parameters appended.

    Args:
        base_url: The destination URL
        utm_params: Dictionary of UTM parameters

    Returns:
        URL with UTM parameters properly encoded
    """
    if not base_url:
        return ""

    # Build UTM params dict, excluding empty values
    params = {
        "utm_source": utm_params.get("utm_source", "facebook"),
        "utm_medium": utm_params.get("utm_medium", "paid_social"),
        "utm_campaign": utm_params.get("utm_campaign", ""),
        "utm_content": utm_params.get("utm_content", ""),
        "utm_term": utm_params.get("utm_term", "")
    }

    # Remove empty params
    params = {k: v for k, v in params.items() if v}

    if not params:
        return base_url

    # Parse the base URL
    parsed = urlparse(base_url)

    # Get existing query params
    existing_params = parse_qs(parsed.query)

    # Merge with UTM params (UTM params take precedence)
    for key, value in params.items():
        existing_params[key] = [value]

    # Build the new query string
    new_query = urlencode(existing_params, doseq=True)

    # Reconstruct the URL
    new_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))

    return new_url


def extract_utm_params(url: str) -> Dict[str, str]:
    """
    Extract UTM parameters from a URL.

    Args:
        url: URL to extract UTM params from

    Returns:
        Dictionary of UTM parameters found in the URL
    """
    if not url:
        return {}

    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    utm_keys = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"]

    return {
        key: params[key][0] if key in params and params[key] else ""
        for key in utm_keys
    }
