"""
This is a symlink file that imports constants from the scripts directory.
This allows code that expects constants in the utils directory to work correctly.
"""

# Import constants from the scripts directory
try:
    from learning_app.scripts.constants import *
except ImportError:
    # Fallback for direct imports
    import sys
    import os
    
    # Add the parent directory to path
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    try:
        from scripts.constants import *
    except ImportError:
        # Define fallback constants if all imports fail
        import logging
        logging.warning("Failed to import constants from scripts directory. Using fallback values.")
        
        # Art elements and principles constants
        ELEMENT_OPTIONS = [
            "Line", "Shape", "Form", "Color", "Value", "Space", "Texture"
        ]
        
        PRINCIPLE_OPTIONS = [
            "Balance", "Emphasis", "Movement", "Pattern & Repetition", 
            "Rhythm", "Proportion", "Variety", "Unity"
        ]