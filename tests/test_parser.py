"""Test cases for the Bayrol Cloud parser module."""
import pytest
import logging
from custom_components.bayrol_cloud.client.parser import (
    parse_pool_data,
    parse_controllers,
    parse_login_form,
    check_login_error,
    check_device_offline,
    parse_overview_page,
    check_device_compatibility,
    DebugInfo,
    get_available_measurements,
)

# Sample device HTML outputs
POOL_RELAX_CL_HTML = """<div><div class="gapp_"></div><div class="tab_data_link" onclick="document.location.href='device.php?c=XXXXX'"><div class="gstat_ok"></div><div class="tab_box stat_ok"><span>pH&nbsp;[pH]</span><h1>7.17</h1></div><div class="tab_box stat_ok"><span>mV&nbsp;[mV]</span><h1>708</h1></div><div class="tab_box stat_ok"><span>T&nbsp;[°C]</span><h1>34.4</h1></div><div class="tab_box "></div><div class="tab_info"><span>24PR3-1928</span></br><span>Pool Relax Cl</span></br><span>v3.5/220211 PR3</span></br><span><a href="device.php?c=XXXXX">Direct access</a></div></div></div>"""

AUTOMATIC_CL_PH_HTML = """<div><div class="gapp_ase" onclick="gotoapp(28354)"><span>App Link<span></div><div class="tab_data_link" onclick="document.location.href='device.php?c=XXXXX&s=v1.40 (220715)'"><div class="gstat_warning"></div><div class="tab_box stat_warning"><span>pH&nbsp;[pH]</span><h1>6.5</h1></div><div class="tab_box stat_warning"><span>Redox&nbsp;[mV]</span><h1>685</h1></div><div class="tab_box stat_warning"><span>Temp.&nbsp;[°C]</span><h1>19.0</h1></div><div class="tab_box "></div><div class="tab_info"><span>22ACL2-02745</span></br><span>Automatic Cl-pH</span></br><span>v1.40 (220715)</span></br><span><a href="device.php?c=XXXXX&s=v1.40 (220715)">Accès direct</a></div></div></div>"""

POOLMANAGER_PRO_HTML = """<div><div class="gapp_pm5" onclick="gotoapp(45890)"><span>App Link<span></div><div class="tab_data_link" onclick="document.location.href='device.php?c=XXXXX'"><div class="gstat_alarm"></div><div class="tab_box stat_alarm"><span>pH&nbsp;[pH]</span><h1>8.37</h1></div><div class="tab_box stat_ok"><span>Cl&nbsp;[mg/l]</span><h1>0.77</h1></div><div class="tab_box stat_ok"><span>T1&nbsp;[°C]</span><h1>27.2</h1></div><div class="tab_box "></div><div class="tab_info"><span>DGFB16739D22</span></br><span>PoolManager PRO</span></br><span>v240729 (9.1.1)</span></br><span><a href="device.php?c=XXXXX">Direct access</a></div></div></div>"""

AUTOMATIC_SALT_HTML = """<div><div class="gapp_ase" onclick="gotoapp(34391)"><span>App Link<span></div><div class="tab_data_link" onclick="document.location.href='device.php?c=XXXXX&s=v2.10 (240812-0831)'"><div class="gstat_warning"></div><div class="tab_box stat_ok"><span>pH&nbsp;[pH]</span><h1>7.3</h1></div><div class="tab_box stat_warning"><span>Redox&nbsp;[mV]</span><h1>683</h1></div><div class="tab_box stat_ok"><span>Temp.&nbsp;[°C]</span><h1>19.5</h1></div><div class="tab_box stat_ok"><span>Salz&nbsp;[g\l]</span><h1>2.0</h1></div><div class="tab_info"><span>24ASE2-11175</span></br><span>Automatic SALT</span></br><span>v2.10 (240812-0831)</span></br><span><a href="device.php?c=XXXXX&s=v2.10 (240812-0831)">Direktzugriff</a></div></div></div>"""

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
        "status": "online",
        "pH_alarm": False,
        "mV_alarm": False,
        "T_alarm": False
    }

def test_parse_pool_data_automatic_cl_ph():
    """Test parsing pool data from Automatic Cl-pH device with alarms."""
    data = parse_pool_data(AUTOMATIC_CL_PH_HTML)
    
    assert data == {
        "pH": 6.5,
        "mV": 685.0,
        "T": 19.0,
        "status": "online",
        "pH_alarm": True,
        "mV_alarm": True,
        "T_alarm": True
    }

def test_parse_pool_data_poolmanager_pro():
    """Test parsing pool data from PoolManager PRO device with chlorine measurements."""
    data = parse_pool_data(POOLMANAGER_PRO_HTML)
    
    assert data == {
        "pH": 8.37,
        "Cl": 0.77,
        "T": 27.2,
        "status": "online",
        "pH_alarm": True,
        "Cl_alarm": False,
        "T_alarm": False
    }

def test_parse_pool_data_automatic_salt():
    """Test parsing pool data from Automatic SALT device with salt measurements."""
    data = parse_pool_data(AUTOMATIC_SALT_HTML)
    
    assert data == {
        "pH": 7.3,
        "mV": 683.0,
        "T": 19.5,
        "Salt": 2.0,
        "status": "online",
        "pH_alarm": False,
        "mV_alarm": True,
        "T_alarm": False,
        "Salt_alarm": False
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
        "status": "online",
        "pH_alarm": False,
        "T_alarm": False
    }

def test_parse_pool_data_mixed_alarms():
    """Test parsing HTML with mixed alarm states."""
    html = """<div>
        <div class="tab_box stat_warning"><span>pH [pH]</span><h1>7.2</h1></div>
        <div class="tab_box"><span>mV [mV]</span><h1>685</h1></div>
        <div class="tab_box stat_warning"><span>T [°C]</span><h1>30.5</h1></div>
    </div>"""
    data = parse_pool_data(html)
    assert data == {
        "pH": 7.2,
        "mV": 685.0,
        "T": 30.5,
        "status": "online",
        "pH_alarm": True,
        "mV_alarm": False,
        "T_alarm": True
    }

def test_debug_info_partial_data(caplog):
    """Test debug info for partial data parse with log capture."""
    html = """<div>
        <div class="tab_box"><span>pH [pH]</span><h1>7.2</h1></div>
        <div class="tab_box"><span>mV [mV]</span><h1>invalid</h1></div>
        <div class="tab_box"><span>Unknown [X]</span><h1>123</h1></div>
    </div>"""
    
    # Set up logging capture
    caplog.set_level(logging.DEBUG)
    
    # Parse the data
    data = parse_pool_data(html)
    
    # Verify the data itself
    assert data == {
        "pH": 7.2,
        "status": "online",
        "pH_alarm": False
    }
    
    # Verify debug info in logs
    debug_info_log = None
    for record in caplog.records:
        if "Debug information" in record.message:
            debug_info_log = record.message
            break
    
    assert debug_info_log is not None
    assert "Unknown measurement label: Unknown" in debug_info_log
    assert "pH: 7.2" in debug_info_log
    assert "Failed to convert value 'invalid' to float for measurement 'mV'" in debug_info_log

def test_parse_controllers():
    """Test parsing controllers from plants page."""
    html = """<div class="tab_row">
        <div class="tab_1">
            <div style="float:left;" onclick="document.location.href='plant_settings.php?c=12345'" title="Edit controller data">
                <p>Pool Controller 1</p>
                <span>TestAddress<br>TestLocation</span>
                <a href="plant_settings.php?c=12345">Edit controller data</a>
            </div>
        </div>
        <div id="tab_data12345" class="tab_2">
            <div class="tab_info">
                <span>Device ID</span>
                <span>Pool Controller 1</span>
            </div>
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

def test_parse_pool_data_pm5():
    """Test parsing pool data from PM5 device with T1 temperature sensor."""
    PM5_HTML = """<div><div class="gapp_pm5" onclick="gotoapp(12345)"><span>App Link<span></div>
<div class="tab_data_link" onclick="document.location.href='device.php?c=12345'">
    <div class="gstat_ok"></div>
    <div class="tab_box stat_ok"><span>pH&nbsp;[pH]</span><h1>7.15</h1></div>
    <div class="tab_box stat_ok"><span>mV&nbsp;[mV]</span><h1>831</h1></div>
    <div class="tab_box stat_warning"><span>T1&nbsp;[°C]</span><h1>11.3</h1></div>
    <div class="tab_box "></div>
    <div class="tab_info">
        <span>SOMESERIAL</span></br>
        <span>PoolManager Chlor (Cl)</span></br>
        <span>v240404 (9.0.1)</span></br>
        <span><a href="device.php?c=12345">Direktzugriff</a></div>
</div></div>"""
    data = parse_pool_data(PM5_HTML)
    assert data == {
        "pH": 7.15,
        "mV": 831.0,
        "T": 11.3,
        "status": "online",
        "pH_alarm": False,
        "mV_alarm": False,
        "T_alarm": True
    }

    html_without_error = """<div>Welcome!</div>"""
    assert check_login_error(html_without_error) is False

# Sample HTML for the overview page with multiple controllers
OVERVIEW_PAGE_HTML = """
<div id="content_table">
    <div class="tab_paging">
        <div class="search">
        <form method="get" action="plants.php">
        <input type="submit" name="send" value="">
        <input type="text" name="s" value="" placeholder="Search controller">
        <input type="button" name="cancel" value="" onclick="document.location.href='plants.php?s='">
        </form>
        </div>
        <div id="btn_sort">
        <div id="btn_sort_menu">
            <ul>
            <li>&nbsp;&nbsp;Sort by:</li>
            <li><a class="on" href="plants.php?sort=1">Device name</a></li>
            <li><a class="" href="plants.php?sort=2">Device with alarm status first</a></li>
            <li><a class="" href="plants.php?sort=3">Device with ok status first</a></li>
            </ul>
        </div>
        </div>
        <div class="reload" onclick="document.location.reload();" title="Reload page (F5)">
        </div>
    </div>
    <div class="tab_row">
        <div class="tab_1">
            <div style="float:left;" onclick="document.location.href='plant_settings.php?c=11111'" title="Edit controller data">
                <p>Haho Pool Controller 1&nbsp;</p>
                <span>Test Company&nbsp;<br>Test Address, Test City&nbsp;</span>
                <a href="plant_settings.php?c=11111">Edit controller data</a>
            </div>
        </div>
        <div id="tab_data11111" class="tab_2"><div><div class="gapp_"></div><div class="tab_data_link" onclick="document.location.href='device.php?c=11111'"><div class="gstat_ok"></div><div class="tab_box stat_ok"><span>pH&nbsp;[pH]</span><h1>7.20</h1></div><div class="tab_box stat_ok"><span>mV&nbsp;[mV]</span><h1>733</h1></div><div class="tab_box stat_ok"><span>T&nbsp;[°C]</span><h1>34.2</h1></div><div class="tab_box "></div><div class="tab_info"><span>TEST-SERIAL1</span><br><span>Pool Relax Cl</span><br><span>v3.5/220211 PR3</span><br><span><a href="device.php?c=11111">Direct access</a></span></div></div></div></div>
    </div>
    <div class="tab_row">
        <div class="tab_1">
            <div style="float:left;" onclick="document.location.href='plant_settings.php?c=22222'" title="Edit controller data">
                <p>Teeuwen&nbsp;</p>
                <span>&nbsp;<br>&nbsp;</span>
                <a href="plant_settings.php?c=22222">Edit controller data</a>
            </div>
        </div>
        <div id="tab_data22222" class="tab_2"><div><div class="gapp_pm5" onclick="gotoapp(22222)"><span>App Link<span></span></span></div><div class="tab_data_link" onclick="document.location.href='device.php?c=22222'"><div class="gstat_ok"></div><div class="tab_box stat_ok"><span>pH&nbsp;[pH]</span><h1>7.37</h1></div><div class="tab_box stat_ok"><span>mV&nbsp;[mV]</span><h1>709</h1></div><div class="tab_box stat_ok"><span>T1&nbsp;[°C]</span><h1>28.2</h1></div><div class="tab_box "></div><div class="tab_info"><span>TEST-SERIAL2</span><br><span>PoolManager Chlor (Cl)</span><br><span>v240729 (9.1.1)</span><br><span><a href="device.php?c=22222">Direct access</a></span></div></div></div></div>
    </div>
</div>
"""

def test_parse_overview_page():
    """Test parsing of the overview page with multiple controllers."""
    data = parse_overview_page(OVERVIEW_PAGE_HTML)
    
    # Verify we have data for both controllers
    assert "11111" in data
    assert "22222" in data
    
    # Check the data for the first controller (Haho Pool Controller)
    haho_data = data["11111"]
    assert haho_data["pH"] == 7.20
    assert haho_data["mV"] == 733
    assert haho_data["T"] == 34.2
    assert haho_data["status"] == "online"
    assert haho_data["name"] == "Haho Pool Controller 1"
    assert haho_data["device_model"] == "Pool Relax Cl"
    assert haho_data["device_id"] == "TEST-SERIAL1"
    assert haho_data["device_version"] == "v3.5/220211 PR3"
    assert not haho_data["pH_alarm"]
    assert not haho_data["mV_alarm"]
    assert not haho_data["T_alarm"]
    
    # Check the data for the second controller (Teeuwen)
    teeuwen_data = data["22222"]
    assert teeuwen_data["pH"] == 7.37
    assert teeuwen_data["mV"] == 709
    assert teeuwen_data["T"] == 28.2  # T1 should be mapped to T
    assert teeuwen_data["status"] == "online"
    assert teeuwen_data["name"] == "Teeuwen"
    assert teeuwen_data["device_model"] == "PoolManager Chlor (Cl)"
    assert teeuwen_data["device_id"] == "TEST-SERIAL2"
    assert teeuwen_data["device_version"] == "v240729 (9.1.1)"
    assert not teeuwen_data["pH_alarm"]
    assert not teeuwen_data["mV_alarm"]
    assert not teeuwen_data["T_alarm"]

def test_parse_overview_page_empty():
    """Test parsing empty overview page."""
    data = parse_overview_page(EMPTY_HTML)
    assert data == {}

def test_check_device_compatibility():
    """Test checking device compatibility against known list."""
    # Should be compatible
    assert check_device_compatibility("Pool Relax Cl") is True
    assert check_device_compatibility("PoolManager Chlor (Cl)") is True
    assert check_device_compatibility("PoolManager PRO") is True
    assert check_device_compatibility("Automatic SALT") is True
    
    # Should not be compatible
    assert check_device_compatibility("Unknown Device") is False
    assert check_device_compatibility("") is False

def test_parse_overview_page_with_warnings(caplog):
    """Test parsing overview page with device not in compatibility list."""
    # Modified overview page with unknown device model
    html = OVERVIEW_PAGE_HTML.replace("Pool Relax Cl", "Unknown Device Model")
    
    # Set up logging capture
    caplog.set_level(logging.WARNING)
    
    # Parse the data
    data = parse_overview_page(html)
    
    # Check that the warning was logged
    warning_logged = False
    for record in caplog.records:
        if "is not in the compatibility list but was successfully parsed" in record.message and "Unknown Device Model" in record.message:
            warning_logged = True
            break
    
    assert warning_logged, "Warning about unknown device model was not logged"
    
    # The data should still be parsed successfully
    assert "11111" in data
    assert data["11111"]["device_model"] == "Unknown Device Model"

def test_get_available_measurements():
    """Test extracting available measurements from parsed data."""
    # Test with PoolManager PRO data (has pH, Cl, T)
    poolmanager_data = parse_pool_data(POOLMANAGER_PRO_HTML)
    measurements = get_available_measurements(poolmanager_data)
    assert set(measurements) == {"pH", "Cl", "T"}
    
    # Test with Pool Relax Cl data (has pH, mV, T)
    relax_data = parse_pool_data(POOL_RELAX_CL_HTML)
    measurements = get_available_measurements(relax_data)
    assert set(measurements) == {"pH", "mV", "T"}
    
    # Test with Automatic SALT data (has pH, mV, T, Salt)
    salt_data = parse_pool_data(AUTOMATIC_SALT_HTML)
    measurements = get_available_measurements(salt_data)
    assert set(measurements) == {"pH", "mV", "T", "Salt"}
    
    # Test with empty data
    measurements = get_available_measurements({})
    assert measurements == []
    
    # Test with offline device (no measurements)
    offline_data = parse_pool_data(OFFLINE_DEVICE_HTML)
    measurements = get_available_measurements(offline_data)
    assert measurements == []
