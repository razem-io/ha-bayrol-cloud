"""Diagnostics support for Bayrol Cloud."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from homeassistant.components.diagnostics import REDACTED
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_USERNAME
from homeassistant.core import HomeAssistant

from .const import CONF_CID, DOMAIN, ISSUE_REPORT_URL

_SENSITIVE_NAME_PARTS = (
    "cid",
    "controller",
    "cookie",
    "email",
    "password",
    "session",
    "token",
    "username",
)
_SENSITIVE_QUERY_KEYS = {
    "c",
    "cid",
    "controller",
    "controller_id",
    "email",
    "password",
    "phpsessid",
    "session",
    "token",
    "username",
}


def _redact_url(value: str) -> str:
    """Redact sensitive query parameters without changing the URL shape."""
    try:
        parts = urlsplit(value)
    except ValueError:
        return value

    if not parts.query:
        return value

    query = [
        (key, REDACTED if key.lower() in _SENSITIVE_QUERY_KEYS else item_value)
        for key, item_value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def _redact_html(html: str, sensitive_values: set[str]) -> str:
    """Redact credentials and identifiers while preserving the HTML structure."""
    known_values = sorted(
        (value for value in sensitive_values if value), key=len, reverse=True
    )
    redacted = html
    redacted = re.sub(
        r"(?i)(PHPSESSID\s*[=:]\s*)[^;\s\"'&<]+",
        rf"\1{REDACTED}",
        redacted,
    )
    redacted = re.sub(
        r"(?i)((?:cid|controller_id|cookie|email|password|session|token|username)"
        r"\s*[:=]\s*[\"'])[^\"']*([\"'])",
        rf"\1{REDACTED}\2",
        redacted,
    )
    redacted = re.sub(
        r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
        REDACTED,
        redacted,
    )

    soup = BeautifulSoup(redacted, "html.parser")
    for element in soup.find_all(True):
        input_name = str(element.get("name", "")).lower()
        input_type = str(element.get("type", "")).lower()

        for attribute, value in list(element.attrs.items()):
            attribute_lower = attribute.lower()
            is_sensitive_attribute = any(
                part in attribute_lower for part in _SENSITIVE_NAME_PARTS
            )
            is_sensitive_input_value = attribute_lower == "value" and (
                input_type in {"email", "hidden", "password"}
                or any(part in input_name for part in _SENSITIVE_NAME_PARTS)
            )

            if is_sensitive_attribute or is_sensitive_input_value:
                element[attribute] = REDACTED
            elif attribute_lower in {"action", "href", "src"} and isinstance(value, str):
                for known_value in known_values:
                    value = value.replace(known_value, REDACTED)
                element[attribute] = _redact_url(value)
            elif isinstance(value, str):
                for known_value in known_values:
                    value = value.replace(known_value, REDACTED)
                element[attribute] = value

    for text_node in soup.find_all(string=True):
        value = str(text_node)
        for known_value in known_values:
            value = value.replace(known_value, REDACTED)
        if value != str(text_node):
            text_node.replace_with(value)

    return str(soup)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    runtime_data = hass.data[DOMAIN][entry.entry_id]
    api = runtime_data["api"]
    coordinator = runtime_data["coordinator"]
    response = api.last_device_status_response

    sensitive_values = {
        str(entry.data.get(key, ""))
        for key in (CONF_USERNAME, CONF_CID)
    }
    sensitive_values.add(str(entry.data.get("device_name", "")))

    response_diagnostics: dict[str, Any] = {"available": response is not None}
    if response is not None:
        response_diagnostics.update(response)
        response_diagnostics["html"] = _redact_html(
            response.get("html", ""), sensitive_values
        )

    return {
        "integration": {
            "entry_title": REDACTED,
            "entry_version": entry.version,
            "report_issue_url": ISSUE_REPORT_URL,
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception_type": (
                type(coordinator.last_exception).__name__
                if coordinator.last_exception is not None
                else None
            ),
        },
        "device_status_response": response_diagnostics,
    }
