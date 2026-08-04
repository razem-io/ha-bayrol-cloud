"""Tests for Bayrol Cloud parser repairs."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.bayrol_cloud import (
    DOMAIN,
    _async_handle_test_parser_repair,
    _set_parser_issue,
)
from custom_components.bayrol_cloud.const import (
    ATTR_CONFIG_ENTRY_ID,
    SERVICE_CLEAR_TEST_PARSER_REPAIR,
    SERVICE_CREATE_TEST_PARSER_REPAIR,
)


@patch("custom_components.bayrol_cloud.ir.async_delete_issue")
@patch("custom_components.bayrol_cloud.ir.async_create_issue")
def test_set_parser_issue(create_issue: Mock, delete_issue: Mock) -> None:
    """Use the production repair content for create and clear operations."""
    hass = Mock()

    _set_parser_issue(hass, "parser_test", create=True)
    create_issue.assert_called_once()
    delete_issue.assert_not_called()

    _set_parser_issue(hass, "parser_test", create=False)
    delete_issue.assert_called_once_with(hass, DOMAIN, "parser_test")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("service", "expected_create"),
    (
        (SERVICE_CREATE_TEST_PARSER_REPAIR, True),
        (SERVICE_CLEAR_TEST_PARSER_REPAIR, False),
    ),
)
async def test_handle_test_parser_repair(
    service: str,
    expected_create: bool,
) -> None:
    """Create and clear the isolated test repair for a loaded entry."""
    entry_id = "test-entry"
    hass = SimpleNamespace(data={DOMAIN: {entry_id: {}}})
    call = SimpleNamespace(
        service=service,
        data={ATTR_CONFIG_ENTRY_ID: entry_id},
    )

    with patch("custom_components.bayrol_cloud._set_parser_issue") as set_issue:
        await _async_handle_test_parser_repair(hass, call)

    set_issue.assert_called_once_with(
        hass,
        f"test_device_status_parser_{entry_id}",
        create=expected_create,
    )


@pytest.mark.asyncio
async def test_handle_test_parser_repair_rejects_unloaded_entry() -> None:
    """Do not create orphaned repairs for unknown config entries."""
    hass = SimpleNamespace(data={DOMAIN: {}})
    call = SimpleNamespace(
        service=SERVICE_CREATE_TEST_PARSER_REPAIR,
        data={ATTR_CONFIG_ENTRY_ID: "missing"},
    )

    with pytest.raises(HomeAssistantError):
        await _async_handle_test_parser_repair(hass, call)
