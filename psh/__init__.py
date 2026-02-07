"""Python Shell (psh) - An educational Unix shell implementation."""

from .shell import Shell
from .version import __version__, get_version, get_version_info

__all__ = ['Shell', '__version__', 'get_version', 'get_version_info']
