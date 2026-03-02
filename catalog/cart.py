from decimal import Decimal
from typing import Dict, Tuple

from .models import AddOn, Product, ProductSize

CART_SESSION_ID = "cart"

# Mapa para exibir tamanho mesmo sem bater no banco (fallback)
SIZE_LABELS = {"P": "Pequena", "M": "Média", "G": "Grande"}


def _normalize_addons(addons) -> Dict[str, int]:
    """Aceita lista [id,id] (compatível) ou dict {id: qty}."""
    if not addons:
        return {}
    if isinstance(addons, dict):
        out = {}
        for k, v in addons.items():
            k = str(k).strip()
            try:
                q = int(v)
            except Exception:
                q = 0
            if k and q > 0:
                out[k] = q
        return out
    # lista/iterável
    out = {}
    for a in addons:
        k = str(a).strip()
        if not k:
            continue
        out[k] = out.get(k, 0) + 1
    return out


def _encode_addons(addons_qty: Dict[str, int]) -> str:
    """Converte {'3':2,'7':1} -> '3x2,7x1'"""
    if not addons_qty:
        return ""
    parts = []
    for aid, qty in sorted(addons_qty.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0]):
        parts.append(f"{aid}x{int(qty)}")
    return ",".join(parts)


def _decode_addons(part: str) -> Dict[str, int]:
    """Compatível com formato antigo: '3,7' -> {'3':1,'7':1}."""
    part = (part or "").strip()
    if not part:
        return {}
    out: Dict[str, int] = {}
    for token in part.split(","):
        token = token.strip()
        if not token:
            continue
        if "x" in token:
            aid, q = token.split("x", 1)
            aid = aid.strip()
            try:
                qty = int(q.strip())
            except Exception:
                qty = 0
            if aid and qty > 0:
                out[aid] = qty
        else:
            aid = token
            if aid:
                out[aid] = out.get(aid, 0) + 1
    return out


def _make_key(product_id: int, size_code: str = "", addons=None, flavors=None) -> str:
    """Cria chave única do item do carrinho.

    Formato: product_id:size_code:addons
      - size_code pode ser vazio
      - addons é dict {id:qty} ou lista [id,id]
    """
    size_code = (size_code or "").strip().upper()
    addons_qty = _normalize_addons(addons)
    addons_part = _encode_addons(addons_qty)
    flavors_part = ""
    if flavors:
        try:
            ids = sorted({int(x) for x in flavors if str(x).strip().isdigit()})
        except Exception:
            ids = []
        flavors_part = ",".join(str(i) for i in ids)
    return f"{product_id}:{size_code}:{addons_part}:{flavors_part}"


def _split_key(item_key: str) -> Tuple[int, str, Dict[str, int], list]:
    """Retorna (product_id, size_code, addons_qty, flavors). Compatível com chaves antigas."""
    parts = (item_key or "").split(":")
    pid_str = parts[0] if len(parts) > 0 else "0"
    size_code = parts[1] if len(parts) > 1 else ""
    addons_part = parts[2] if len(parts) > 2 else ""
    flavors_part = parts[3] if len(parts) > 3 else ""
    try:
        pid = int(pid_str or 0)
    except Exception:
        pid = 0
    flavors = [int(x) for x in (flavors_part or "").split(",") if x.strip().isdigit()]
    return pid, (size_code or "").strip().upper(), _decode_addons(addons_part), flavors


def get_cart(request):
    cart = request.session.get(CART_SESSION_ID)
    if not cart:
        cart = request.session[CART_SESSION_ID] = {}
    return cart


def add_to_cart(request, product_id: int, qty: int = 1, size_code: str = "", addons=None, flavors=None):
    cart = get_cart(request)
    key = _make_key(product_id, size_code, addons=addons, flavors=flavors)
    if key not in cart:
        cart[key] = {
            "qty": 0,
            "size": (size_code or "").strip().upper(),
            "addons": _normalize_addons(addons),
            "flavors": sorted({int(x) for x in (flavors or []) if str(x).strip().isdigit()}) if flavors else [],
        }
    cart[key]["qty"] += int(qty)
    if cart[key]["qty"] <= 0:
        cart.pop(key, None)
    request.session.modified = True


def set_qty(request, item_key: str, qty: int):
    cart = get_cart(request)
    qty = int(qty)
    if qty <= 0:
        cart.pop(item_key, None)
    else:
        pid, size_code, addons_qty, flavors = _split_key(item_key)
        cart[item_key] = {"qty": qty, "size": size_code, "addons": addons_qty, "flavors": flavors}
    request.session.modified = True


def remove_from_cart(request, item_key: str):
    cart = get_cart(request)
    cart.pop(item_key, None)
    request.session.modified = True


def clear_cart(request):
    request.session[CART_SESSION_ID] = {}
    request.session.modified = True


def cart_items_and_total(request):
    cart = get_cart(request)

    # Pré-carrega produtos, tamanhos e adicionais para evitar N+1
    pids = []
    addon_ids_all = []
    for k in cart.keys():
        pid, _, addons_qty, flavors = _split_key(k)
        if pid:
            pids.append(pid)
        for fid in (flavors or []):
            if fid:
                pids.append(fid)
        addon_ids_all.extend(list((addons_qty or {}).keys()))

    products = Product.objects.filter(id__in=pids, is_active=True).select_related("category")
    products_map = {p.id: p for p in products}

    size_pairs = []
    for k in cart.keys():
        pid, size_code, _, flavors = _split_key(k)
        if size_code:
            size_pairs.append((pid, size_code))
            for fid in (flavors or []):
                size_pairs.append((fid, size_code))

    sizes_map = {}
    if size_pairs:
        qs = ProductSize.objects.filter(
            product_id__in=[pid for pid, _ in size_pairs],
            size__in=list({sc for _, sc in size_pairs}),
        )
        for ps in qs:
            sizes_map[(ps.product_id, ps.size)] = ps

    addons_map = {}
    if addon_ids_all:
        ids_int = [int(a) for a in addon_ids_all if str(a).isdigit()]
        qs = AddOn.objects.filter(id__in=list(set(ids_int)), is_active=True).select_related("category")
        addons_map = {str(a.id): a for a in qs}

    items = []
    total = Decimal("0.00")

    def _unit_price_for_product(prod: Product, size_code_local: str) -> Decimal:
        """Calcula o preço unitário do produto para o tamanho selecionado.

        Regras:
        - Se houver ProductSize e promo_price do tamanho, usa promo_price.
        - Senão, usa price do tamanho. Se o produto tiver promo (promo_price < price),
          aplica a promo proporcionalmente ao tamanho.
        - Sem tamanho, usa promo do produto (quando existir), senão price.
        """
        if not size_code_local:
            base = prod.promo_price if getattr(prod, "promo_price", None) and prod.promo_price < prod.price else prod.price
            return Decimal(str(base))

        ps_local = sizes_map.get((prod.id, size_code_local))
        if ps_local:
            if getattr(ps_local, "promo_price", None) and ps_local.promo_price < ps_local.price:
                return Decimal(str(ps_local.promo_price))
            if getattr(prod, "promo_price", None) and prod.promo_price < prod.price and prod.price:
                multiplier = Decimal(str(prod.promo_price)) / Decimal(str(prod.price))
                return (Decimal(str(ps_local.price)) * multiplier).quantize(Decimal("0.01"))
            return Decimal(str(ps_local.price))

        base = prod.promo_price if getattr(prod, "promo_price", None) and prod.promo_price < prod.price else prod.price
        return Decimal(str(base))

    for item_key, data in cart.items():
        pid, size_code, addons_qty, flavors = _split_key(item_key)
        p = products_map.get(pid)
        if not p:
            continue

        try:
            qty = int(data.get("qty", 1))
        except Exception:
            qty = 1
        if qty <= 0:
            qty = 1

        # Preço inicial (produto base)
        unit_price = _unit_price_for_product(p, size_code)

        # Tamanho (quando existir)
        size_label = ""
        if size_code:
            ps = sizes_map.get((pid, size_code))
            if ps:
                size_label = ps.get_size_display()
            else:
                size_label = SIZE_LABELS.get(size_code, size_code)

        # Sabores (meio-a-meio / multi-sabores):
        # - exibe nome composto (Sabor 1 + Sabor 2 ...)
        # - preço final = (soma dos preços dos sabores) / 2
        #   (regra do projeto: divide SEMPRE por 2, independente da quantidade de sabores)
        p_name_override = p.name
        flavor_ids = []
        try:
            flavor_ids = sorted({int(x) for x in (flavors or []) if int(x) > 0})
        except Exception:
            flavor_ids = []
        if flavor_ids:
            if pid not in flavor_ids:
                flavor_ids = [pid] + flavor_ids
            else:
                # garante que o sabor base fique primeiro (para cálculo de acréscimos)
                flavor_ids = [pid] + [x for x in flavor_ids if x != pid]

            flavor_products = [products_map.get(fid) for fid in flavor_ids if products_map.get(fid)]
            if flavor_products:
                composed_name = " + ".join([fp.name for fp in flavor_products])
                p_name_override = composed_name

                try:
                    prices = [_unit_price_for_product(fp, size_code) for fp in flavor_products]
                    if prices:
                        total_prices = sum(prices, Decimal("0.00"))
                        unit_price = (total_prices / Decimal("2")).quantize(Decimal("0.01"))
                except Exception:
                    pass

        # Addons
        addons = []
        addons_unit_total = Decimal("0.00")
        for aid, aqty in (addons_qty or {}).items():
            a = addons_map.get(str(aid))
            if not a:
                continue
            try:
                aqty_int = int(aqty)
            except Exception:
                aqty_int = 0
            if aqty_int <= 0:
                continue

            price = Decimal(str(a.get_price()))
            addons.append(
                {
                    "id": a.id,
                    "name": a.name,
                    "category": str(a.category),
                    "qty": aqty_int,
                    "price": price,
                    "total": price * aqty_int,
                }
            )
            addons_unit_total += (price * aqty_int)

        base_subtotal = unit_price * qty
        addons_subtotal = addons_unit_total * qty
        subtotal = base_subtotal + addons_subtotal
        total += subtotal

        # Nome exibido no carrinho deve refletir os sabores escolhidos
        display_name = p_name_override + (f" ({size_label})" if size_label else "")

        items.append(
            {
                "key": item_key,
                "id": p.id,
                "name": p_name_override,
                "display_name": display_name,
                "size_code": size_code,
                "size_label": size_label,
                "price": unit_price,
                "qty": qty,
                "addons": addons,
                "addons_unit_total": addons_unit_total,
                "addons_subtotal": addons_subtotal,
                "subtotal": subtotal,
            }
        )

    items.sort(key=lambda x: x["display_name"].lower())
    return items, total
