"""Tests for Bayrol Cloud diagnostics redaction."""

from homeassistant.components.diagnostics import REDACTED

from custom_components.bayrol_cloud.diagnostics import _redact_html, _redact_url


def test_redact_url_preserves_non_sensitive_parameters() -> None:
    """Redact controller identifiers without removing useful parameters."""
    result = _redact_url("/p/device.php?c=12345&view=status")

    assert "12345" not in result
    assert "view=status" in result
    assert "device.php" in result


def test_redact_html_preserves_parser_structure() -> None:
    """Remove secrets while retaining the tags and classes needed for support."""
    html = """
        <html>
          <body data-cid="12345">
            owner@example.com
            <form action="/p/device.php?c=12345&view=status">
              <input type="hidden" name="token" value="csrf-secret">
              <input type="password" value="pool-password">
              <div class="i_item">
                <div class="i_x16" id="device_1">My Pool</div>
              </div>
              <script>const session = "PHPSESSID=session-secret";</script>
            </form>
          </body>
        </html>
    """

    result = _redact_html(
        html,
        {"12345", "owner@example.com", "pool-password", "My Pool"},
    )

    for secret in (
        "12345",
        "owner@example.com",
        "csrf-secret",
        "pool-password",
        "session-secret",
        "My Pool",
    ):
        assert secret not in result

    assert 'class="i_item"' in result
    assert 'class="i_x16"' in result
    assert 'id="device_1"' in result
    assert "view=status" in result
    assert REDACTED in result
