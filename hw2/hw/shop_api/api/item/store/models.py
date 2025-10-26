from dataclasses import dataclass
from decimal import Decimal
from shop_api.database.models import Product


@dataclass(slots=True)
class ItemInfo:
    name: str
    price: Decimal
    deleted: bool = False


@dataclass(slots=True)
class ItemEntity:
    id: int
    info: ItemInfo

    @staticmethod
    def from_product(product: Product) -> 'ItemEntity':
        return ItemEntity(
            id=product.id,
            info=ItemInfo(
                name=product.name,
                price=product.price,
                deleted=not product.in_stock
            )
        )


@dataclass(slots=True)
class PatchItemInfo:
    name: str | None = None
    price: Decimal | None = None
