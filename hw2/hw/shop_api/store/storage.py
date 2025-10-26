from dataclasses import dataclass, field
from typing import List, Dict, Optional
import uuid


@dataclass(slots=True)
class ItemData:
    """Represents an item in the shop with basic information."""

    id: int
    name: str
    price: float
    deleted: bool = False


@dataclass(slots=True)
class ItemsData:
    """Container for multiple items data."""

    items: List[ItemData] = field(default_factory=list)


@dataclass(slots=True)
class ItemnInCartData:
    """Represents an item in a shopping cart with quantity and availability."""

    id: int
    name: str
    quantity: int
    available: bool


@dataclass(slots=True)
class CartData:
    """Represents a shopping cart with items and total price."""

    id: int
    items: List[ItemnInCartData] = field(default_factory=list)
    price: float = 0.0


@dataclass(slots=True)
class IdDataGen:
    """ID generator utility class."""

    id: int

    def gen_id():
        """Generate a new unique ID using UUID4."""
        id = int(uuid.uuid4())
        return IdDataGen(id=id)