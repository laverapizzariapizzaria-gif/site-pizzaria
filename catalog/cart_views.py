from decimal import Decimal

from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from .cart import add_to_cart, cart_items_and_total, clear_cart, remove_from_cart, set_qty
from .models import Product, ProductAddOnRule


@never_cache
@ensure_csrf_cookie
def cart_view(request):
    items, total = cart_items_and_total(request)
    return render(request, "catalog/cart.html", {"items": items, "total": total})


def _parse_addons_qty_from_post(post):
    """Lê inputs do tipo addon_<id>=<qty> e retorna dict {id:qty}."""
    out = {}
    for k, v in post.items():
        if not k.startswith("addon_"):
            continue
        aid = k.replace("addon_", "").strip()
        if not aid.isdigit():
            continue
        try:
            qty = int(v)
        except Exception:
            qty = 0
        if qty > 0:
            out[aid] = qty
    return out


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product.objects.prefetch_related("addons__category", "sizes"), pk=product_id)

    qty = request.POST.get("qty", "1")
    # Tamanho pode vir do POST (radio/hidden) ou da sessão (selecionado na 1ª tela)
    size = ((request.POST.get("size") or "").strip().upper() or (request.session.get("size") or request.session.get("selected_size") or "").strip().upper())

    # Addons (modo iFood): dict {id:qty}
    addons_qty = _parse_addons_qty_from_post(request.POST)

    # Valida tamanho se o produto tem tamanhos (pizzas)
    if product.sizes.exists() and not size:
        request.session["addon_error"] = "Escolha um tamanho antes de adicionar ao carrinho."
        return redirect(f"/opcionais/{product.id}/")

    # Sabores (meio-a-meio etc.)
    flavors = [int(x) for x in request.POST.getlist("flavors") if str(x).isdigit()]
    flavors = sorted(set(flavors))
    if product.id not in flavors:
        # garante ao menos o sabor base
        flavors = [product.id] + flavors

    # valida limite por tamanho (configurável em ProductSize.max_flavors)
    # Limite de sabores vem do ProductSize (campo "Máx. de sabores" no admin)
    size_obj_limit = product.sizes.filter(size=size).first() if size else None
    max_flavors = int(getattr(size_obj_limit, "max_flavors", 1) or 1)
    if max_flavors < 1:
        max_flavors = 1

    if flavors and len(flavors) > max_flavors:
        request.session["addon_error"] = f"Você pode escolher no máximo {max_flavors} sabor(es) para este tamanho."
        return redirect(f"/opcionais/{product.id}/?size={size}")

    # Valida regra de mistura de categorias (configurável por tamanho)
    size_obj = None
    if size:
        size_obj = product.sizes.filter(size=size).first()
    block_mix = bool(getattr(size_obj, "allow_mix_categories", False))  # checkbox = NÃO permitir misturar

    if flavors:
        if block_mix:
            # não pode misturar categorias
            cats = set(Product.objects.filter(id__in=flavors, is_active=True).values_list("category_id", flat=True))
            if any(c != product.category_id for c in cats):
                request.session["addon_error"] = "Para este tamanho, não é permitido misturar categorias de sabores."
                return redirect(f"/opcionais/{product.id}/?size={size}")
            allowed_qs = Product.objects.filter(id__in=flavors, category=product.category, is_active=True)
        else:
            allowed_qs = Product.objects.filter(id__in=flavors, is_active=True)

        allowed_flavors = set(allowed_qs.values_list("id", flat=True))
        flavors = [fid for fid in flavors if fid in allowed_flavors]
        if product.id not in flavors:
            flavors = [product.id] + flavors

    # Mantém só addons permitidos no produto
    allowed_ids = {str(a.id): a for a in product.addons.filter(is_active=True)}
    addons_qty = {aid: q for aid, q in addons_qty.items() if aid in allowed_ids}

    # Valida regras por categoria (min/max por categoria) contando seleção (checkbox), não quantidade
    rules = list(ProductAddOnRule.objects.filter(product=product, enabled=True).select_related("category"))
    count_by_cat = {}
    for aid in addons_qty.keys():
        a = allowed_ids.get(aid)
        if not a:
            continue
        cat_id = a.category_id
        count_by_cat[cat_id] = count_by_cat.get(cat_id, 0) + 1

    for r in rules:
        cnt = count_by_cat.get(r.category_id, 0)
        if r.min_select and cnt < r.min_select:
            request.session["addon_error"] = f"Em '{r.category.name}', selecione pelo menos {r.min_select} opção(ões)."
            return redirect(f"/opcionais/{product.id}/?size={size}")
        if r.max_select and r.max_select > 0 and cnt > r.max_select:
            request.session["addon_error"] = f"Em '{r.category.name}', selecione no máximo {r.max_select} opção(ões)."
            return redirect(f"/opcionais/{product.id}/?size={size}")

    add_to_cart(request, product_id, qty, size_code=size, addons=addons_qty, flavors=flavors)

    # Limpa acréscimos de itens que não contam como sabor (ex.: Bebidas) usados na tela de opcionais
    request.session.pop(f"pending_nonflavor_total_{product_id}", None)
    request.session.pop(f"pending_nonflavor_items_{product_id}", None)
    return redirect("cart")

@require_POST
def cart_set_qty(request, item_key):
    qty = request.POST.get("qty", "1")
    set_qty(request, item_key, qty)
    return redirect("cart")


@require_POST
def cart_remove(request, item_key):
    remove_from_cart(request, item_key)
    return redirect("cart")


@require_POST
def cart_clear(request):
    clear_cart(request)
    return redirect("cart")