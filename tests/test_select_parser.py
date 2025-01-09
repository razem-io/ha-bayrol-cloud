"""Tests for select element parser."""
from custom_components.bayrol_cloud.client.select_parser import parse_select_options

def test_parse_select_options():
    """Test parsing select options."""
    # Sample HTML from the device status page
    html = """
    <select class="i_x7" disabled>
        <option value="0" selected>AUS</option>
        <option value="1">Eco</option>
        <option value="2">Normal</option>
        <option value="3">Erhöht</option>
        <option value="4">Auto</option>
    </select>
    """
    
    options, selected_value, selected_text = parse_select_options(html)
    
    # Check options are parsed correctly
    assert len(options) == 5
    assert options == [
        {'value': 0, 'text': 'AUS'},
        {'value': 1, 'text': 'Eco'},
        {'value': 2, 'text': 'Normal'},
        {'value': 3, 'text': 'Erhöht'},
        {'value': 4, 'text': 'Auto'}
    ]
    
    # Check selected value and text
    assert selected_value == 0
    assert selected_text == 'AUS'

def test_parse_select_options_out1():
    """Test parsing select options for OUT1."""
    html = """
    <select class="i_x7" disabled>
        <option value="0">Ein</option>
        <option value="1" selected>Aus</option>
        <option value="2">Zeit-Steuerung</option>
    </select>
    """
    
    options, selected_value, selected_text = parse_select_options(html)
    
    # Check options are parsed correctly
    assert len(options) == 3
    assert options == [
        {'value': 0, 'text': 'Ein'},
        {'value': 1, 'text': 'Aus'},
        {'value': 2, 'text': 'Zeit-Steuerung'}
    ]
    
    # Check selected value and text
    assert selected_value == 1
    assert selected_text == 'Aus'

def test_parse_select_options_alarm():
    """Test parsing select options for alarm relay."""
    html = """
    <select class="i_x7" disabled>
        <option value="0">Auto</option>
        <option value="1" selected>Aus</option>
    </select>
    """
    
    options, selected_value, selected_text = parse_select_options(html)
    
    # Check options are parsed correctly
    assert len(options) == 2
    assert options == [
        {'value': 0, 'text': 'Auto'},
        {'value': 1, 'text': 'Aus'}
    ]
    
    # Check selected value and text
    assert selected_value == 1
    assert selected_text == 'Aus'
