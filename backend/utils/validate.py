from typing import Literal

SearchMode = Literal["hybrid", "keyword", "vector"]

def validate_search_mode(mode: str) -> bool:
    """Validate that search mode is one of the allowed values.
    
    Args:
        mode: The search mode to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    return mode in SearchMode.__args__
