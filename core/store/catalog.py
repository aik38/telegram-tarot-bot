from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

ProductKind = Literal["ticket", "pass", "addon"]


@dataclass(frozen=True)
class Product:
    sku: str
    title: str
    description: str
    price_stars: int
    kind: ProductKind


PRODUCTS: tuple[Product, ...] = (
    Product(
        sku="TICKET_3",
        title="3枚スプレッドチケット",
        description="3枚引きの占いを1回利用できます。",
        price_stars=300,
        kind="ticket",
    ),
    Product(
        sku="TICKET_7",
        title="7枚スプレッドチケット",
        description="ヘキサグラムなど7枚スプレッドを1回利用できます。",
        price_stars=650,
        kind="ticket",
    ),
    Product(
        sku="TICKET_10",
        title="10枚スプレッドチケット",
        description="ケルト十字など10枚スプレッドを1回利用できます。",
        price_stars=900,
        kind="ticket",
    ),
    Product(
        sku="PASS_7D",
        title="7日パス",
        description="7日間すべてのスプレッドが使い放題になります。",
        price_stars=1500,
        kind="pass",
    ),
    Product(
        sku="PASS_30D",
        title="30日パス",
        description="30日間すべてのスプレッドが使い放題になります。",
        price_stars=4000,
        kind="pass",
    ),
    Product(
        sku="ADDON_IMAGES",
        title="画像追加オプション",
        description="占い結果に画像を添付するオプションを有効化します。",
        price_stars=500,
        kind="addon",
    ),
)

PRODUCT_INDEX: dict[str, Product] = {product.sku: product for product in PRODUCTS}


def iter_products() -> Iterable[Product]:
    return PRODUCTS


def get_product(sku: str) -> Product | None:
    return PRODUCT_INDEX.get(sku)


__all__ = [
    "Product",
    "ProductKind",
    "PRODUCTS",
    "PRODUCT_INDEX",
    "get_product",
    "iter_products",
]
