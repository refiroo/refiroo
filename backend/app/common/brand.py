"""The names of the product (Product 0.12 I5, M1): what ``refiroo`` replaces, kept in one place."""

# The names `refiroo` replaces: a model that still names its product so is shown as refiroo alone.
DEFAULT_PRODUCT_NAMES = ("refiroo", "rdm engine")


def is_default_product_name(name: str) -> bool:
    return name.strip().lower() in DEFAULT_PRODUCT_NAMES
