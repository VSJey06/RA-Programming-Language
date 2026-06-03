"""
object_system.py — Object registry for the RA runtime.

Manages runtime object instances created by ``Obj.ClassName``
instantiation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from parser.ra_ast import AssignmentNode, LiteralNode

if TYPE_CHECKING:
    from runtime.structural.class_system import ClassRegistry


class ObjectRegistry:
    """Registry that stores runtime object instances.

    Each object is represented as a ``dict`` with at least an
    ``__class__`` key holding the name of the class from which it
    was instantiated.

    Attributes
    ----------
    _objects : dict[str, dict[str, Any]] — internal object store.
    """

    def __init__(self) -> None:
        self._objects: dict[str, dict[str, Any]] = {}

    def create(self, name: str, class_name: str, class_registry: ClassRegistry) -> None:
        """Create a new object instance from a class definition.

        Looks up the class in *class_registry*, copies default field
        values from the class body into the new object.

        Parameters
        ----------
        name           : str          — variable name that will hold the object.
        class_name     : str          — name of the class to instantiate.
        class_registry : ClassRegistry — registry holding class definitions.

        Raises
        ------
        RuntimeError — when *class_name* is not registered.
        """
        class_node = class_registry.get(class_name)
        obj: dict[str, Any] = {"__class__": class_name}
        for member in class_node.members:
            if isinstance(member, AssignmentNode):
                if isinstance(member.value, LiteralNode):
                    obj[member.name] = member.value.value
                else:
                    obj[member.name] = None
        self._objects[name] = obj

    def set_property(self, object_name: str, property_name: str, value: Any) -> None:
        """Set a property value on an object.

        Parameters
        ----------
        object_name   : str — variable name of the object.
        property_name : str — property key to set.
        value         : Any — value to assign.
        """
        obj = self.get(object_name)
        obj[property_name] = value

    def get_property(self, object_name: str, property_name: str) -> Any:
        """Retrieve a property value from an object.

        Parameters
        ----------
        object_name   : str — variable name of the object.
        property_name : str — property key to look up.

        Returns
        -------
        Any — the stored property value.

        Raises
        ------
        RuntimeError — when *property_name* does not exist on the object.
        """
        obj = self.get(object_name)
        try:
            return obj[property_name]
        except KeyError:
            raise RuntimeError(
                f"Property '{property_name}' does not exist "
                f"on object '{object_name}'"
            )

    def exists(self, name: str) -> bool:
        """Return True if an object with *name* has been created."""
        return name in self._objects

    def get(self, name: str) -> dict[str, Any]:
        """Retrieve an object instance by variable name.

        Parameters
        ----------
        name : str — variable name of the object.

        Returns
        -------
        dict[str, Any]

        Raises
        ------
        RuntimeError — when *name* has not been created.
        """
        try:
            return self._objects[name]
        except KeyError:
            raise RuntimeError(f"Object '{name}' does not exist")

    def all_objects(self) -> dict[str, dict[str, Any]]:
        """Return a copy of every registered object instance.

        Returns
        -------
        dict[str, dict[str, Any]]
        """
        return dict(self._objects)
