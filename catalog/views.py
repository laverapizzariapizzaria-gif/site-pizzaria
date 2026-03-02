from decimal import Decimal, ROUND_HALF_UP

from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Prefetch

from .models import Category, Product, ProductAddOnRule, ProductSize
from .cart import add_to_cart
from django.db.models import Q
from orders.models import SiteSettings

def _get_site_settings():
    obj = SiteSettings.objects.first()
    if obj is None:
        obj = SiteSettings.objects.create()
    return obj







@never_cache
def menu_confirm_flavors(request, product_id: int):
    """Recebe seleção de sabores (checkbox) feita diretamente no cardápio e redireciona para opcionais."""
    product = get_object_or_404(Product.objects.select_related("category").prefetch_related("sizes"), pk=product_id)

    # Itens selecionados que NÃO contam como sabor (ex.: Bebidas). Eles devem ir direto para o carrinho.
    # Além disso, guardamos o valor total desses itens para exibir como acréscimo na tela de opcionais.
    non_flavor_ids = [int(x) for x in request.POST.getlist("items") if str(x).isdigit()]
    non_flavor_ids = sorted(set(non_flavor_ids))
    if non_flavor_ids:
        selected_size = (request.session.get('size') or request.session.get('selected_size') or '').strip().upper()

        def _unit_price(prod: Product, size_code: str) -> Decimal:
            """Mesmo cálculo do carrinho para um produto e tamanho (unitário)."""
            if not size_code:
                base = prod.promo_price if getattr(prod, "promo_price", None) and prod.promo_price < prod.price else prod.price
                return Decimal(str(base))

            ps = ProductSize.objects.filter(product=prod, size=size_code).first()
            if ps:
                # promo por tamanho
                if getattr(ps, "promo_price", None) and ps.promo_price < ps.price:
                    return Decimal(str(ps.promo_price))
                # promo global proporcional
                if getattr(prod, "promo_price", None) and prod.promo_price < prod.price and prod.price:
                    try:
                        multiplier = Decimal(str(prod.promo_price)) / Decimal(str(prod.price))
                        return (Decimal(str(ps.price)) * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    except Exception:
                        return Decimal(str(ps.price))
                return Decimal(str(ps.price))

            base = prod.promo_price if getattr(prod, "promo_price", None) and prod.promo_price < prod.price else prod.price
            return Decimal(str(base))

        non_flavor_total = Decimal("0.00")
        non_flavor_items = []
        for pid in Product.objects.filter(id__in=non_flavor_ids, is_active=True).values_list("id", flat=True):
            p = Product.objects.filter(id=pid).prefetch_related("sizes").first()
            size_code = selected_size if (p and p.sizes.exists() and selected_size) else ""
            add_to_cart(request, pid, qty=1, size_code=size_code)

            if p:
                try:
                    price = _unit_price(p, size_code)
                    non_flavor_total += price
                    non_flavor_items.append({"id": p.id, "name": p.name, "price": str(price)})
                except Exception:
                    pass

        # Guardamos para a tela de opcionais somar como acréscimo (não divide por 2).
        request.session[f"pending_nonflavor_total_{product.id}"] = str(non_flavor_total)
        request.session[f"pending_nonflavor_items_{product.id}"] = non_flavor_items

    selected_size = (request.session.get('size') or request.session.get('selected_size') or '').strip().upper()
    if not selected_size:
        return redirect('size_home')

    # Limite de sabores vem do ProductSize (campo "Máx. de sabores" no admin)
    size_obj = ProductSize.objects.filter(product=product, size=selected_size).first()
    max_flavors = int(getattr(size_obj, "max_flavors", 1) or 1)
    if max_flavors < 1:
        max_flavors = 1

    max_extra = max(0, max_flavors - 1)

    # Sabores extras enviados pelo form (checkbox no cardápio)
    extras = [int(x) for x in request.POST.getlist("flavors") if str(x).isdigit()]
    extras = [x for x in extras if x != product.id]
    # remove duplicados mantendo ordem
    seen=set()
    extras=[x for x in extras if not (x in seen or seen.add(x))]

    if len(extras) > max_extra:
        request.session["addon_error"] = f"Você pode escolher no máximo {max_flavors} sabor(es) para este tamanho."
        return redirect("menu")

    # Regra de mistura de categorias (configurável por tamanho)
    # OBS: neste projeto, o checkbox no admin significa "NÃO permitir misturar".
    block_mix = bool(getattr(size_obj, "allow_mix_categories", False))

    if block_mix and extras:
        # Se bloquear mistura, todos os sabores devem ser da mesma categoria do sabor base
        extra_cats = set(
            Product.objects.filter(id__in=extras, is_active=True).values_list("category_id", flat=True)
        )
        if any(cat_id != product.category_id for cat_id in extra_cats):
            messages.error(request, "Para este tamanho, não é permitido misturar categorias de sabores.")
            return redirect("menu")

    # Mantém apenas sabores válidos/ativos
    extras = list(
        Product.objects.filter(id__in=extras, is_active=True).values_list("id", flat=True)
    )

    flavors = [product.id] + extras

    # salva na sessão para a tela de opcionais usar e enviar para o carrinho
    request.session[f"pending_flavors_{product.id}"] = flavors

    return redirect(f"/opcionais/{product.id}/?size={selected_size}&lock=1&from_menu=1")


@never_cache
@ensure_csrf_cookie
def menu_add_selected(request):
    """Adiciona ao carrinho os itens selecionados no cardápio que NÃO contam como sabor.

    Usado quando o usuário seleciona apenas itens de categorias como Bebidas (com checkbox),
    sem escolher uma pizza base.
    """
    if request.method != "POST":
        return redirect("menu")

    item_ids = [int(x) for x in request.POST.getlist("items") if str(x).isdigit()]
    item_ids = sorted(set(item_ids))
    if not item_ids:
        return redirect("menu")

    selected_size = (request.session.get('size') or request.session.get('selected_size') or '').strip().upper()
    for pid in Product.objects.filter(id__in=item_ids, is_active=True).values_list("id", flat=True):
        p = Product.objects.filter(id=pid).prefetch_related("sizes").first()
        size_code = selected_size if (p and p.sizes.exists() and selected_size) else ""
        add_to_cart(request, pid, qty=1, size_code=size_code)

    return redirect("cart")


@never_cache
@ensure_csrf_cookie
def size_home_view(request):
    """Primeira tela do site: usuário escolhe o tamanho padrão (P/M/G).
    O tamanho escolhido fica salvo na sessão e é usado no cardápio e na seleção de sabores.
    """
    if request.method == "POST":
        size = (request.POST.get("size") or "").strip().upper()
        if size in ("P", "M", "G", "BIG"):
            request.session["size"] = size
            return redirect("menu")
    selected_size = request.session.get("size") or request.session.get("selected_size") or ""
    return render(request, "catalog/size_home.html", {"selected_size": selected_size})

@never_cache
@ensure_csrf_cookie
def menu_view(request):
    selected_size = (request.session.get('size') or request.session.get('selected_size') or '').strip().upper()
    if not selected_size:
        return redirect('size_home')

    # Prefetch produtos + tamanhos para montar o cardápio.
    # IMPORTANTE: além das pizzas com tamanho selecionado, também precisamos exibir produtos
    # sem tamanho (ex.: Bebidas) para que possam ser selecionados no cardápio.
    products_qs = (
        Product.objects
        .filter(is_active=True)
        .filter(Q(sizes__size=selected_size) | Q(sizes__isnull=True))
        .distinct()
        .prefetch_related("sizes")
    )

    categories = (
        Category.objects
        .prefetch_related(Prefetch("products", queryset=products_qs, to_attr="filtered_products"))
        .all()
    )

    # Calcula desconto do produto (promoção no Product) e aplica visualmente nos tamanhos
    for category in categories:
        for product in getattr(category, 'filtered_products', []):
            product.has_promo = bool(product.promo_price and product.promo_price < product.price)
            product.promo_percent = None
            promo_multiplier = None

            if product.has_promo and product.price:
                promo_multiplier = (product.promo_price / product.price)
                # % OFF arredondado
                product.promo_percent = int(((Decimal("1") - promo_multiplier) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

            # Anexa preço promocional por tamanho apenas para exibição
            for size in product.sizes.all():
                # Prioridade de promoção:
                # 1) Promoção por tamanho (ProductSize.promo_price)
                # 2) Promoção geral do produto (Product.promo_price), aplicada proporcionalmente ao tamanho
                # 3) Sem promoção
                size.has_promo = False
                size.promo_percent = None
                size.final_price = size.price
                size.original_price = size.price

                if getattr(size, "promo_price", None) and size.promo_price < size.price:
                    size.has_promo = True
                    size.final_price = size.promo_price
                    # % OFF do próprio tamanho
                    if size.price:
                        pct = (Decimal("1") - (Decimal(str(size.promo_price)) / Decimal(str(size.price)))) * Decimal("100")
                        size.promo_percent = int(pct.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
                elif promo_multiplier is not None:
                    size.has_promo = True
                    size.final_price = (size.price * promo_multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    size.promo_percent = product.promo_percent




    # Anexa o tamanho escolhido (P/M/G) a cada produto para o template renderizar apenas aquele tamanho.
    for category in categories:
        for product in getattr(category, 'filtered_products', []):
            # IMPORTANTE:
            # Não use product.sizes.filter(...).first() aqui, porque isso faz uma nova query
            # e retorna um objeto ProductSize "limpo" (sem os atributos calculados acima,
            # como final_price/has_promo/original_price).
            # Precisamos reaproveitar o objeto já pré-carregado em product.sizes.all().
            sel = None
            if selected_size:
                for s in product.sizes.all():
                    if (getattr(s, "size", "") or "").strip().upper() == selected_size:
                        sel = s
                        break
            product.selected_size_obj = sel
            product.selected_size_code = selected_size

            if sel is not None:
                # Usa o preço final calculado (já com promo por tamanho ou por produto) se existir.
                product.selected_price = getattr(sel, "final_price", sel.price)
                product.selected_has_promo = bool(getattr(sel, "has_promo", False))
                product.selected_original_price = getattr(sel, "original_price", sel.price)
                product.selected_promo_percent = getattr(sel, "promo_percent", None)
            else:
                product.selected_price = None


    # Monta opções de sabores (checkbox no cardápio) baseado no tamanho escolhido.
    # Regra: o sabor base é o próprio produto; o cliente escolhe apenas os sabores EXTRA (até max_flavors-1).
    for category in categories:
        for product in getattr(category, 'filtered_products', []):
            # Pega do ProductSize selecionado (campo "Máx. de sabores" no admin)
            sel = getattr(product, "selected_size_obj", None)
            max_flavors = int(getattr(sel, "max_flavors", 1) or 1)
            if max_flavors < 1:
                max_flavors = 1

            product.max_flavors = max_flavors
            product.max_extra_flavors = max(0, max_flavors - 1)

            flavor_options = []
            if product.max_extra_flavors > 0:
                # Por padrão, não mistura doce/salgada (mesma categoria do produto base),
                # mas isso pode ser liberado por tamanho via ProductSize.allow_mix_categories.
                allow_mix = bool(getattr(sel, "allow_mix_categories", False))
                qs = Product.objects.filter(is_active=True).exclude(id=product.id).order_by("name")
                if not allow_mix:
                    qs = qs.filter(category=product.category)
                for fp in qs:
                    extra = getattr(fp, "second_flavor_extra", None)
                    try:
                        extra_val = Decimal(str(extra)) if extra is not None else Decimal("0.00")
                    except Exception:
                        extra_val = Decimal("0.00")

                    flavor_options.append(
                        {
                            "id": fp.id,
                            "name": fp.name,
                            "no_price_increase": bool(getattr(fp, "no_price_increase", False)),
                            "second_flavor_extra": extra_val,
                        }
                    )
            product.flavor_options = flavor_options

    # Remove categorias vazias após filtrar pelo tamanho selecionado
    categories = [c for c in categories if getattr(c, 'filtered_products', [])]

    settings_obj = _get_site_settings()
    return render(
        request,
        "catalog/menu.html",
        {
            "categories": categories,
            "store_open": settings_obj.store_is_open,
            "store_closed_message": settings_obj.store_closed_message,
        },
    )

@never_cache
@ensure_csrf_cookie
def size_select_view(request, product_id: int):
    """Tela para escolher o tamanho (P/M/G) antes de ir para sabores/opcionais."""

    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related("sizes"),
        pk=product_id,
    )

    sizes = list(product.sizes.all()) if product.sizes.exists() else []

    # Se não houver tamanhos, cai direto na tela de opcionais/sabores.
    if not sizes:
        return redirect("addons_select", product_id=product_id)

    store_open = bool(_get_site_settings().is_store_open)

    if request.method == "POST":
        size_code = (request.POST.get("size") or "").strip().upper()
        if not size_code:
            size_code = sizes[0].size
        return redirect(f"/opcionais/{product_id}/?size={size_code}&lock=1")

    return render(
        request,
        "catalog/size_select.html",
        {
            "product": product,
            "sizes": sizes,
            "store_open": store_open,
        },
    )

def addons_view(request, product_id: int):
    """Tela dedicada para escolher opcionais (modo iFood)."""

    product = get_object_or_404(
        Product.objects.select_related("category").prefetch_related("sizes", "addons__category"),
        pk=product_id,
    )

    # Mensagem de erro vinda de validação no POST
    error_msg = request.session.pop("addon_error", "")

    # Tamanhos (P/M/G etc.): permitir escolher nesta própria tela.
    size_code = ((request.GET.get('size') or '').strip().upper() or (request.session.get('size') or request.session.get('selected_size') or '').strip().upper())
    lock_size = ((request.GET.get('lock') or '').strip() == '1') or bool(request.session.get('size') or request.session.get('selected_size'))
    selected_size = None
    sizes = list(product.sizes.all()) if product.sizes.exists() else []

    # Sabores escolhidos no cardápio (persistidos em sessão)
    pending_key = f"pending_flavors_{product.id}"
    pending_flavors = request.session.get(pending_key)
    selected_flavor_ids = []
    if isinstance(pending_flavors, list) and pending_flavors:
        try:
            ids = [int(x) for x in pending_flavors if str(x).isdigit()]
        except Exception:
            ids = []
        ids = sorted(set(ids), key=ids.index) if ids else []
        if product.id not in ids:
            ids = [product.id] + ids
        selected_flavor_ids = ids

    def _unit_price_for_product(prod: Product, size_code_local: str) -> Decimal:
        """Mesmo cálculo do carrinho para um produto e tamanho."""
        if not size_code_local:
            base = prod.promo_price if getattr(prod, "promo_price", None) and prod.promo_price < prod.price else prod.price
            return Decimal(str(base))

        ps_local = ProductSize.objects.filter(product=prod, size=size_code_local).first()
        if ps_local:
            if getattr(ps_local, "promo_price", None) and ps_local.promo_price < ps_local.price:
                return Decimal(str(ps_local.promo_price))
            if getattr(prod, "promo_price", None) and prod.promo_price < prod.price and prod.price:
                try:
                    multiplier = Decimal(str(prod.promo_price)) / Decimal(str(prod.price))
                    return (Decimal(str(ps_local.price)) * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                except Exception:
                    return Decimal(str(ps_local.price))
            return Decimal(str(ps_local.price))

        base = prod.promo_price if getattr(prod, "promo_price", None) and prod.promo_price < prod.price else prod.price
        return Decimal(str(base))

    def _calculated_pizza_price(size_code_local: str) -> Decimal:
        """Preço final exibido (sabores somados e divididos por 2, quando houver)."""
        if selected_flavor_ids:
            flavor_products = list(Product.objects.filter(id__in=selected_flavor_ids, is_active=True))
            # mantém a ordem (base primeiro)
            fp_map = {p.id: p for p in flavor_products}
            ordered = [fp_map[i] for i in selected_flavor_ids if i in fp_map]
            if ordered:
                prices = [_unit_price_for_product(fp, size_code_local) for fp in ordered]
                total_prices = sum(prices, Decimal("0.00"))
                return (total_prices / Decimal("2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return _unit_price_for_product(product, size_code_local)

    base_price = Decimal(str(product.price))
    computed_prices_by_size = {}

    if sizes:
        if size_code:
            selected_size = product.sizes.filter(size=size_code).first()
        if not selected_size:
            selected_size = sizes[0]
        size_code = selected_size.size

        # Preço exibido na tela de opcionais deve ser o MESMO do carrinho.
        base_price = _calculated_pizza_price(size_code)
        # Também calculamos o preço exibido para cada tamanho quando a tela permite trocar o tamanho aqui.
        for s in sizes:
            computed_prices_by_size[s.size] = _calculated_pizza_price(s.size)
    else:
        # Sem tamanho, segue cálculo do carrinho
        base_price = _calculated_pizza_price("")

    # Itens marcados no cardápio que NÃO contam como sabor (ex.: Bebidas)
    # Esses itens já foram adicionados ao carrinho, mas mostramos o valor como acréscimo na tela.
    non_flavor_total = Decimal("0.00")
    non_flavor_items = []
    try:
        nf_raw = request.session.get(f"pending_nonflavor_total_{product.id}")
        if nf_raw is not None:
            non_flavor_total = Decimal(str(nf_raw))
    except Exception:
        non_flavor_total = Decimal("0.00")
    try:
        nf_items = request.session.get(f"pending_nonflavor_items_{product.id}")
        if isinstance(nf_items, list):
            non_flavor_items = nf_items
    except Exception:
        non_flavor_items = []

    # Sabores (meio-a-meio): limite configurável por tamanho (admin)
    max_flavors = 1
    try:
        if selected_size and getattr(selected_size, "max_flavors", None):
            max_flavors = int(selected_size.max_flavors)
    except Exception:
        max_flavors = 1
    if max_flavors < 1:
        max_flavors = 1

    # Opções de sabores para meio-a-meio.
    # IMPORTANTE: aqui mostramos o *acréscimo do 2º sabor* (e não o preço cheio da pizza).
    flavor_options = []
    if max_flavors > 1:
        qs = Product.objects.filter(category=product.category, is_active=True).order_by("name")
        for fp in qs:
            extra = getattr(fp, "second_flavor_extra", None)
            try:
                extra_val = float(extra) if extra is not None else 0.0
            except Exception:
                extra_val = 0.0

            flavor_options.append(
                {
                    "id": fp.id,
                    "name": fp.name,
                    "no_price_increase": bool(getattr(fp, "no_price_increase", False)),
                    "second_flavor_extra": extra_val,
                }
            )


    # Se os sabores foram escolhidos no cardápio, escondemos a seção de sabores aqui
    # e enviamos os IDs selecionados como campos hidden no formulário.
    if selected_flavor_ids:
        flavor_options = []
        # Não mostramos aviso de "limite" aqui, pois a seleção já aconteceu no cardápio.
        max_flavors = 0

    addons_qs = product.addons.filter(is_active=True).select_related("category").order_by(
        "category__sort_order", "category__name", "name"
    )

    rules_qs = ProductAddOnRule.objects.filter(product=product, enabled=True).select_related("category")
    rules = {r.category_id: r for r in rules_qs}

    grouped = []
    current_cat = None
    current_list = []
    for a in addons_qs:
        if current_cat is None or a.category_id != current_cat.id:
            if current_cat is not None:
                grouped.append({"category": current_cat, "addons": current_list})
            current_cat = a.category
            current_list = []
        current_list.append(a)
    if current_cat is not None:
        grouped.append({"category": current_cat, "addons": current_list})

    return render(
        request,
        "catalog/addons.html",
        {
            "product": product,
            "grouped_addons": grouped,
            "rules": rules,
            "selected_size": selected_size,
            "max_flavors": max_flavors,
            "flavor_options": flavor_options,
            "selected_flavor_ids": selected_flavor_ids,
            "size_code": size_code,
            "base_price": base_price,
            "computed_prices_by_size": computed_prices_by_size,
            "lock_size": lock_size,
            "error": error_msg,
            "sizes": sizes,
            "non_flavor_total": non_flavor_total,
            "non_flavor_items": non_flavor_items,
        },
    )