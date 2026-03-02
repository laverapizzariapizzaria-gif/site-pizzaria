from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter(name="discount_percent")
def discount_percent(product) -> int:
    """Return discount percentage for a product with promo_price.

    Example: price=30, promo=20 -> 33
    """
    try:
        price = getattr(product, "price", None)
        promo = getattr(product, "promo_price", None)
        if price in (None, "") or promo in (None, ""):
            return 0

        price_d = Decimal(str(price))
        promo_d = Decimal(str(promo))

        if price_d <= 0 or promo_d <= 0 or promo_d >= price_d:
            return 0

        pct = (Decimal("1") - (promo_d / price_d)) * Decimal("100")
        # Round to nearest integer, typical for discounts
        return int(pct.quantize(Decimal("1")))
    except (InvalidOperation, TypeError, ValueError):
        return 0
