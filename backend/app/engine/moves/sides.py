"""One side of a model mapping: what a release's model says about the elements a mapping names
(0.11 X1). Read from the compiled model, never from a key it knows."""

from dataclasses import dataclass
from functools import cached_property
from typing import Any

from ...models.schema import (
    EngineModel,
    ObjectTypeAttributeDefinition,
    ObjectTypeRelationDefinition,
)


@dataclass(frozen=True)
class Side:
    model: EngineModel
    release_id: str

    @property
    def model_key(self) -> str:
        return self.model.release.key

    @cached_property
    def type_keys(self) -> list[str]:
        return [item.key for item in self.model.objectTypes]

    def has_type(self, key: Any) -> bool:
        return isinstance(key, str) and self.model.object_type(key) is not None

    def has_attribute(self, key: Any) -> bool:
        return isinstance(key, str) and self.model.attribute_type(key) is not None

    def has_relation(self, key: Any) -> bool:
        return isinstance(key, str) and self.model.relation_type(key) is not None

    def value_type(self, attribute: str) -> str:
        definition = self.model.attribute_type(attribute)
        return definition.valueType if definition else ""

    def bindings(self, type_key: str) -> tuple[ObjectTypeAttributeDefinition, ...]:
        definition = self.model.object_type(type_key)
        return definition.attributes if definition else ()

    def binding(self, type_key: str, attribute: Any) -> ObjectTypeAttributeDefinition | None:
        return next((b for b in self.bindings(type_key) if b.attributeTypeKey == attribute), None)

    def unique(self, attribute: str) -> bool:
        definition = self.model.attribute_type(attribute)
        return bool(definition and definition.features.get("unique"))

    def rootable(self, type_key: str) -> bool:
        definition = self.model.object_type(type_key)
        return bool(definition and definition.features.get("rootCreatable", False))

    @cached_property
    def containment(self) -> frozenset[str]:
        """The relation types that place a record under its parent."""
        return frozenset(
            key
            for item in self.model.objectTypes
            for key in self.model.containment_relation_keys(item.key)
        )

    def parents(self, type_key: str) -> list[tuple[str, str]]:
        """The containment relations placing ``type_key`` under a parent: (relation, parent type)."""
        own = self.model.containment_relation_keys(type_key)
        return [
            (item.relationTypeKey, item.fromObjectTypeKey)
            for item in self.model.objectTypeRelations
            if item.toObjectTypeKey == type_key and item.relationTypeKey in own
        ]

    def relations_from(self, type_key: str) -> list[ObjectTypeRelationDefinition]:
        """The relationships other than containment a record of ``type_key`` holds at their ``from`` end."""
        return [
            item
            for item in self.model.objectTypeRelations
            if item.fromObjectTypeKey == type_key and item.relationTypeKey not in self.containment
        ]

    def relation_ends(
        self, relation: str, type_key: str, direction: str
    ) -> list[ObjectTypeRelationDefinition]:
        """The bindings of ``relation`` with ``type_key`` at the end ``direction`` reads it from."""
        end = "fromObjectTypeKey" if direction == "outgoing" else "toObjectTypeKey"
        return [
            item
            for item in self.model.objectTypeRelations
            if item.relationTypeKey == relation and getattr(item, end) == type_key
        ]
