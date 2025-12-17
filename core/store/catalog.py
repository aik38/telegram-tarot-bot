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
        sku="PASS_7D",
        title="7日パス",
        description="毎日占いや雑談を楽しみたい方向けの7日間パスです。",
        price_stars=1000,
        kind="pass",
    ),
    Product(
        sku="PASS_30D",
        title="30日パス",
        description="ひと月まとめて安心して使える30日パスです。",
        price_stars=3500,
        kind="pass",
    ),
    Product(
        sku="TICKET_3",
        title="スリーカード(3枚)",
        description="まずは状況を整理したい方向けの3枚引き1回分です。",
        price_stars=100,
        kind="ticket",
    ),
    Product(
        sku="TICKET_7",
        title="ヘキサグラム(7枚)",
        description="深掘りをしたいときの7枚スプレッド1回分です。",
        price_stars=300,
        kind="ticket",
    ),
    Product(
        sku="TICKET_10",
        title="ケルト十字(10枚)",
        description="じっくり見たい方の10枚スプレッド1回分です。",
        price_stars=500,
        kind="ticket",
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
