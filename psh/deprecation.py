"""Deprecation utilities for PSH."""

import warnings
from typing import Type, Optional


class PSHDeprecationWarning(DeprecationWarning):
    """Custom deprecation warning for PSH."""
    pass


def deprecated_class(old_class: Type, new_class: Type, version: str, removal_version: Optional[str] = None):
    """Mark a class as deprecated.
    
    Args:
        old_class: The deprecated class
        new_class: The replacement class
        version: Version when deprecation started
        removal_version: Version when the class will be removed
    """
    removal_msg = f" and will be removed in version {removal_version}" if removal_version else ""
    message = (
        f"{old_class.__name__} is deprecated as of version {version}{removal_msg}. "
        f"Use {new_class.__name__} instead."
    )
    
    # Store deprecation info on the class
    old_class._deprecation_warning = message
    old_class._replacement_class = new_class
    
    # Modify __init__ to show warning
    original_init = old_class.__init__
    
    def new_init(self, *args, **kwargs):
        warnings.warn(message, PSHDeprecationWarning, stacklevel=2)
        original_init(self, *args, **kwargs)
    
    old_class.__init__ = new_init
    
    # Update docstring
    if old_class.__doc__:
        old_class.__doc__ = f"**DEPRECATED**: {message}\n\n{old_class.__doc__}"
    else:
        old_class.__doc__ = f"**DEPRECATED**: {message}"
    
    return old_class