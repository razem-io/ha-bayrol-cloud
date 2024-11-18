"""Test cases for the Bayrol Cloud parser module."""
import pytest
from custom_components.bayrol_cloud.client.parser import (
    parse_pool_data,
    parse_controllers,
    parse_login_form,
    check_login_error,
    check_device_offline,
)

# Sample device HTML outputs
POOL_RELAX_CL_HTML = """<div><div class="gapp_"></div><div class="tab_data_link" onclick="document.location.href='device.php?c=XXXXX'"><div class="gstat_ok"></div><div class="tab_box stat_ok"><span>pH&nbsp;[pH]</span><h1>7.17</h1></div><div class="tab_box stat_ok"><span>mV&nbsp;[mV]</span><h1>708</h1></div><div class="tab_box stat_ok"><span>T&nbsp;[°C]</span><h1>34.4</h1></div><div class="tab_box "></div><div class="tab_info"><span>24PR3-1928</span></br><span>Pool Relax Cl</span></br><span>v3.5/220211 PR3</span></br><span><a href="device.php?c=XXXXX">Direct access</a></div></div></div>"""

AUTOMATIC_CL_PH_HTML = """<div><div class="gapp_ase" onclick="gotoapp(28354)"><span>App Link<span></div><div class="tab_data_link" onclick="document.location.href='device.php?c=XXXXX&s=v1.40 (220715)'"><div class="gstat_warning"></div><div class="tab_box stat_warning"><span>pH&nbsp;[pH]</span><h1>6.5</h1></div><div class="tab_box stat_warning"><span>Redox&nbsp;[mV]</span><h1>685</h1></div><div class="tab_box stat_warning"><span>Temp.&nbsp;[°C]</span><h1>19.0</h1></div><div class="tab_box "></div><div class="tab_info"><span>22ACL2-02745</span></br><span>Automatic Cl-pH</span></br><span>v1.40 (220715)</span></br><span><a href="device.php?c=XXXXX&s=v1.40 (220715)">Accès direct</a></div></div></div>"""

OFFLINE_DEVICE_HTML = """<div><div class="gapp_"></div><div class="tab_data_link" onclick="document.location.href='help.php#offline'"><div class="gstat_error"></div><div class="tab_error">No connection to the controller since 13.11.24, 07:10 UTC<br>Click here for additional information</div><div class="tab_info"><span>24PR3-1928</span></br><span></span></br><span></span></br><span><a href="help.php#offline">Direct access</a></div></div></div>"""

EMPTY_HTML = "<div></div>"
INVALID_HTML = "<div><div class='tab_box'><span>pH [pH]</span><h1>invalid</h1></div></div>"

def test_parse_pool_data_pool_relax_cl():
    """Test parsing pool data from Pool Relax Cl device."""
    data = parse_pool_data(POOL_RELAX_CL_HTML)
    
    assert data == {
        "pH": 7.17,
        "mV": 708.0,
        "T": 34.4,
        "status": "online"
    }

def test_parse_pool_data_automatic_cl_ph():
    """Test parsing pool data from Automatic Cl-pH device."""
    data = parse_pool_data(AUTOMATIC_CL_PH_HTML)
    
    assert data == {
        "pH": 6.5,
        "mV": 685.0,
        "T": 19.0,
        "status": "online"
    }

def test_parse_pool_data_offline_device():
    """Test parsing pool data from offline device."""
    data = parse_pool_data(OFFLINE_DEVICE_HTML)
    
    assert data == {
        "status": "offline",
        "device_id": "24PR3-1928",
        "last_seen": "13.11.24, 07:10"
    }

def test_check_device_offline():
    """Test detection of offline device status."""
    result = check_device_offline(OFFLINE_DEVICE_HTML)
    assert result == {
        "status": "offline",
        "device_id": "24PR3-1928",
        "last_seen": "13.11.24, 07:10"
    }

def test_check_device_offline_online_device():
    """Test offline check with online device."""
    result = check_device_offline(POOL_RELAX_CL_HTML)
    assert result is None

def test_parse_pool_data_empty():
    """Test parsing empty HTML response."""
    data = parse_pool_data(EMPTY_HTML)
    assert data == {}

def test_parse_pool_data_invalid_values():
    """Test parsing HTML with invalid numeric values."""
    data = parse_pool_data(INVALID_HTML)
    assert data == {}

def test_parse_pool_data_missing_values():
    """Test parsing HTML with missing values."""
    html = """<div class="tab_box"><span>pH [pH]</span><h1></h1></div>"""
    data = parse_pool_data(html)
    assert data == {}

def test_parse_pool_data_partial_data():
    """Test parsing HTML with only some measurements."""
    html = """<div>
        <div class="tab_box"><span>pH [pH]</span><h1>7.2</h1></div>
        <div class="tab_box"><span>mV [mV]</span><h1>invalid</h1></div>
        <div class="tab_box"><span>T [°C]</span><h1>30.5</h1></div>
    </div>"""
    data = parse_pool_data(html)
    assert data == {
        "pH": 7.2,
        "T": 30.5,
        "status": "online"
    }

def test_parse_controllers():
    """Test parsing controllers from plants page."""
    html = """<div onclick="document.location.href='plant_settings.php?c=12345'">
        <div class="tab_info">
            <span>Device ID</span>
            <span>Pool Controller 1</span>
        </div>
    </div>"""
    controllers = parse_controllers(html)
    assert controllers == [{"cid": "12345", "name": "Pool Controller 1"}]

def test_parse_login_form():
    """Test parsing login form fields."""
    html = """<form id="form_login">
        <input name="username" value="">
        <input name="password" value="">
        <input name="token" value="abc123">
    </form>"""
    form_data = parse_login_form(html)
    assert form_data == {
        "username": "",
        "password": "",
        "token": "abc123"
    }

def test_check_login_error():
    """Test checking for login errors."""
    html_with_error = """<div class="error_text">Fehler: Invalid credentials</div>"""
    assert check_login_error(html_with_error) is True

    html_without_error = """<div>Welcome!</div>"""
    assert check_login_error(html_without_error) is False
