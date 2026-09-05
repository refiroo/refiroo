from typing import Any

RELATION_IDENTITY_FIELDS = ("relationTypeKey", "fromObjectTypeKey", "toObjectTypeKey")


def pointer_segment(value: Any) -> str:
    """Escape one RFC 6901 JSON Pointer segment."""
    return str(value).replace("~", "~0").replace("/", "~1")


def relation_path(identity: tuple[str, str, str]) -> str:
    """Build the model pointer for an object-type relation identified by its triple."""
    return "/objectTypeRelations/" + "/".join(pointer_segment(item) for item in identity)
