"""Python Shell (psh) - An educational Unix shell implementation."""

from .version import __version__, get_version, get_version_info
from .shell import Shell

__all__ = ['Shell', '__version__', 'get_version', 'get_version_info']