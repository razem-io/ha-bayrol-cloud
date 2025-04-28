"""Parser for select elements in Bayrol device status page."""
import re
from typing import Dict, Any, List, Optional, Tuple

def parse_select_options(html: str) -> Tuple[List[Dict[str, Any]], Optional[int], Optional[str]]:
    """Parse options from a select element.
    
    Args:
        html: Raw HTML of a select element
        
    Returns:
        Tuple containing:
        - List of options with their values and text
        - Currently selected value (or None if no selection)
        - Currently selected text (or None if no selection)
    """
    options = []
    selected_value = None
    selected_text = None
    
    # First match each complete option tag
    option_pattern = r'<option[^>]*?value="(\d+)"[^>]*?>([^<\t]+)'
    selected_pattern = r'selected(?:="")?'
    
    matches = re.finditer(option_pattern, html)
    
    for match in matches:
        # Get value
        value = int(match.group(1))
        
        # Get text and clean it
        text = match.group(2).strip()
        
        # Add to options list
        options.append({
            'value': value,
            'text': text
        })
        
        # Check if this was the selected option - look for selected attribute
        full_tag = match.group(0)
        if re.search(selected_pattern, full_tag):
            selected_value = value
            selected_text = text
    
    # Sort options by value
    options.sort(key=lambda x: x['value'])
    
    return options, selected_value, selected_text
