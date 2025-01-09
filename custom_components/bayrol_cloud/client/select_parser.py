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
    
    # Match pattern for options with or without selected attribute
    # Format: <option( selected="")? value="(\d+)">([^<\t]+)
    option_pattern = r'<option(?:\s+selected(?:="")?)?(?:\s+value="(\d+)"|value="(\d+)")>\s*([^\t<]+)'
    matches = re.finditer(option_pattern, html)
    
    for match in matches:
        # Get value (could be in group 1 or 2 depending on attribute order)
        value = match.group(1) or match.group(2)
        value = int(value)
        
        # Get text and clean it
        text = match.group(3).strip()
        
        # Add to options list
        options.append({
            'value': value,
            'text': text
        })
        
        # Check if this was the selected option
        if 'selected' in match.group(0):
            selected_value = value
            selected_text = text
    
    # Sort options by value
    options.sort(key=lambda x: x['value'])
    
    return options, selected_value, selected_text
