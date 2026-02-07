"""Registry system for shell builtins."""

from typing import Dict, List, Optional, Set, Type

from .base import Builtin


class BuiltinRegistry:
    """Registry for shell builtins."""

    def __init__(self):
        self._builtins: Dict[str, Builtin] = {}
        self._instances: Set[Builtin] = set()

    def register(self, builtin_class: Type[Builtin]) -> None:
        """Register a builtin class."""
        builtin = builtin_class()
        self._instances.add(builtin)

        # Register primary name
        self._builtins[builtin.name] = builtin

        # Register aliases
        for alias in builtin.aliases:
            self._builtins[alias] = builtin

    def get(self, name: str) -> Optional[Builtin]:
        """Get a builtin by name."""
        return self._builtins.get(name)

    def has(self, name: str) -> bool:
        """Check if a builtin exists."""
        return name in self._builtins

    def all(self) -> Dict[str, Builtin]:
        """Get all registered builtins (including aliases)."""
        return self._builtins.copy()

    def names(self) -> List[str]:
        """Get all primary builtin names (excluding aliases)."""
        return sorted([builtin.name for builtin in self._instances])

    def instances(self) -> List[Builtin]:
        """Get all unique builtin instances."""
        return list(self._instances)

    def __contains__(self, item: str) -> bool:
        """Support 'in' operator."""
        return self.has(item)

    def __getitem__(self, key: str) -> Optional[Builtin]:
        """Support dict-like access."""
        return self.get(key)


# Global registry instance
registry = BuiltinRegistry()


def builtin(cls: Type[Builtin]) -> Type[Builtin]:
    """Decorator to auto-register builtins."""
    registry.register(cls)
    return cls
