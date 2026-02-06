"""Base module for expansion components.

Note: The expansion components (GlobExpander, CommandSubstitution,
VariableExpander, TildeExpander) all take a Shell instance in their
constructor and have method signatures tailored to their specific
needs (e.g., GlobExpander.expand returns List[str], CommandSubstitution
uses execute() not expand()). A common abstract base class was removed
as it did not fit the varying interfaces.
"""
