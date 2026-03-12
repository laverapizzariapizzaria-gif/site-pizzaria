from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from decimal import Decimal

DELIVERY_FEE_DEFAULT = Decimal("5.00")  # taxa padrão de entrega

from catalog.cart import cart_items_and_total, clear_cart
from .models import Order, OrderItem, OrderItemAddOn, SiteSettings
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from .services.mercadopago_pix import criar_pagamento_pix, consultar_pagamento
from .services.whatsapp import normalize_phone_to_wa, render_message, wa_link
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


def _get_site_settings() -> SiteSettings:
    # Singleton: pega o primeiro ou cria com defaults
    obj = SiteSettings.objects.first()
    if obj is None:
        obj = SiteSettings.objects.create()
    return obj

@never_cache
@ensure_csrf_cookie
def checkout_view(request):
    items, subtotal = cart_items_and_total(request)
    if not items:
        return redirect("cart")

    settings_obj = _get_site_settings()
    if not getattr(settings_obj, 'store_is_open', True):
        return redirect('menu')

    # Mantém valores preenchidos em caso de erro
    form = {
        "name": "",
        "email": "",
        "cpf": "",
        "phone": "",
        "delivery_type": "ENTREGA",
        "address": "",
        "reference_point": "",
        "notes": "",
        "payment_method": "PIX",
        "cash_change_for": "",
    }
    errors = {}

    # Taxa automática (aplica somente para ENTREGA)
    def calc_fee(delivery_type: str) -> Decimal:
        if delivery_type != "ENTREGA":
            return Decimal("0.00")
        settings_obj = _get_site_settings()
        # Campo configurável no Admin
        return getattr(settings_obj, "delivery_fee_default", DELIVERY_FEE_DEFAULT)

    if request.method == "POST":
        form["name"] = (request.POST.get("name") or "").strip()
        form["email"] = (request.POST.get("email") or "").strip().lower()
        form["cpf"] = (request.POST.get("cpf") or "").strip()
        form["phone"] = (request.POST.get("phone") or "").strip()
        form["delivery_type"] = (request.POST.get("delivery_type") or "ENTREGA").strip().upper()
        form["address"] = (request.POST.get("address") or "").strip()
        form["reference_point"] = (request.POST.get("reference_point") or "").strip()
        form["notes"] = (request.POST.get("notes") or "").strip()
        form["payment_method"] = (request.POST.get("payment_method") or "PIX").strip().upper()
        form["cash_change_for"] = (request.POST.get("cash_change_for") or "").strip()

        # Validações
        if not form["name"]:
            errors["name"] = "Informe seu nome."
        if not form["email"]:
            errors["email"] = "Informe seu email para salvar seus pedidos."
        else:
            try:
                validate_email(form["email"])
            except ValidationError:
                errors["email"] = "Informe um email válido."
        # CPF é usado no payer.identification do Mercado Pago
        cpf_digits = (form["cpf"] or "").replace(".", "").replace("-", "").replace(" ", "")
        if not cpf_digits:
            errors["cpf"] = "Informe seu CPF."
        elif (not cpf_digits.isdigit()) or (len(cpf_digits) != 11):
            errors["cpf"] = "CPF inválido. Digite 11 números (ex: 123.456.789-00)."
        if not form["phone"]:
            errors["phone"] = "Informe um telefone/WhatsApp."

        if form["delivery_type"] not in {"ENTREGA", "RETIRADA"}:
            errors["delivery_type"] = "Selecione ENTREGA ou RETIRADA."

        # Se for ENTREGA, endereço passa a ser obrigatório
        if form["delivery_type"] == "ENTREGA" and not form["address"]:
            errors["address"] = "Para entrega, informe o endereço."

        if form["payment_method"] not in {"PIX", "CARTAO", "DINHEIRO"}:
            errors["payment_method"] = "Selecione a forma de pagamento."

        # Troco só faz sentido para dinheiro
        if form["payment_method"] == "DINHEIRO" and form["cash_change_for"]:
            try:
                cash_val = Decimal(form["cash_change_for"].replace(",", "."))
                if cash_val <= 0:
                    raise ValueError()
            except Exception:
                errors["cash_change_for"] = "Informe um valor válido para troco (ex: 100,00)."

        delivery_fee = calc_fee(form["delivery_type"])
        total = (subtotal or Decimal("0.00")) + delivery_fee

        if errors:
            return render(
                request,
                "orders/checkout.html",
                {
                    "items": items,
                    "subtotal": subtotal,
                    "delivery_fee": delivery_fee,
                    "total": total,
                    "errors": errors,
                    "form": form,
                },
            )

        # Vincula (ou cria) conta do cliente automaticamente pelo email.
        User = get_user_model()
        user_obj = None
        if request.user.is_authenticated:
            user_obj = request.user
            # Se o usuário não tiver email cadastrado, atualiza.
            if form["email"] and not getattr(user_obj, "email", ""):
                user_obj.email = form["email"]
                user_obj.save(update_fields=["email"])
        else:
            email = form["email"]
            user_obj = User.objects.filter(email__iexact=email).first()
            if user_obj is None:
                # Cria usuário sem senha (vai definir senha pelo link "Ativar conta").
                user_obj = User(username=email, email=email)
                user_obj.set_unusable_password()
                user_obj.save()

        order = Order.objects.create(
            customer_name=form["name"],
            customer_email=form["email"],
            customer_cpf=form["cpf"],
            phone=form["phone"],
            delivery_type=form["delivery_type"],
            address=form["address"] if form["delivery_type"] == "ENTREGA" else "",
            reference_point=form["reference_point"] if form["delivery_type"] == "ENTREGA" else "",
            notes=form["notes"],
            payment_method=form["payment_method"],
            cash_change_for=(Decimal(form["cash_change_for"].replace(",", ".")) if (form["payment_method"]=="DINHEIRO" and form["cash_change_for"]) else None),
            delivery_fee=delivery_fee,
            total=total,
            user=user_obj,
        )

        for i in items:
            order_item = OrderItem.objects.create(
                order=order,
                product_name=i["name"],
                unit_price=i["price"],
                quantity=i["qty"],
                size_code=i.get("size_code", "") or "",
                size_label=i.get("size_label", "") or "",
            )

            # Salva opcionais do item (snapshot)
            for a in i.get("addons", []) or []:
                try:
                    OrderItemAddOn.objects.create(
                        item=order_item,
                        name=a.get("name", ""),
                        price=a.get("price", 0) or 0,
                        qty=int(a.get("qty", 1) or 1),
                    )
                except Exception:
                    # não quebra o pedido caso algum opcional esteja inválido
                    pass

        clear_cart(request)

        # Se for PIX, gera cobrança e exibe QR Code
        if order.payment_method == "PIX":
            try:
                payload = criar_pagamento_pix(order)
                order.mp_payment_id = payload.payment_id
                order.mp_status = payload.status or "pending"
                order.mp_qr_code_base64 = payload.qr_code_base64
                order.mp_qr_code = payload.qr_code
                order.save(update_fields=["mp_payment_id","mp_status","mp_qr_code_base64","mp_qr_code"])
                return redirect("pix_payment", order_id=order.id)
            except Exception as e:
                # Se Mercado Pago falhar, cai para fluxo normal (pedido criado) e mostra mensagem na página
                request.session["pix_error"] = str(e)
                return redirect("order_success", order_id=order.id)

        return redirect("order_success", order_id=order.id)

    # GET: mostra valores padrão
    delivery_fee = calc_fee(form["delivery_type"])
    total = (subtotal or Decimal("0.00")) + delivery_fee

    return render(
        request,
        "orders/checkout.html",
        {
            "items": items,
            "subtotal": subtotal,
            "delivery_fee": delivery_fee,
            "total": total,
            "form": form,
            "errors": errors,
        },
    )


def order_success(request, order_id):
    order = get_object_or_404(Order.objects.select_related("user"), id=order_id)
    pix_error = request.session.pop("pix_error", None)
    s = _get_site_settings()

    # Link para o cliente definir senha (quando a conta foi criada automaticamente no checkout)
    claim_link = ""
    try:
        if order.user and not order.user.has_usable_password():
            from users.views import build_claim_link  # import local para evitar ciclos

            claim_link = build_claim_link(request, order.user)
    except Exception:
        claim_link = ""

    whatsapp_enabled = bool(s.enable_whatsapp)
    store_number = normalize_phone_to_wa(s.whatsapp_store_number)
    customer_number = normalize_phone_to_wa(order.phone)

    # Link para o cliente enviar mensagem para a pizzaria
    store_msg = render_message(s.whatsapp_store_message, order)
    whatsapp_store_link = wa_link(store_number, store_msg) if whatsapp_enabled else ""

    # Link para a pizzaria enviar mensagem pronta para o cliente
    cust_msg = render_message(s.whatsapp_customer_message, order)
    whatsapp_customer_link = wa_link(customer_number, cust_msg) if whatsapp_enabled else ""

    return render(
        request,
        "orders/success.html",
        {
            "order": order,
            "pix_error": pix_error,
            "claim_link": claim_link,
            "whatsapp_enabled": whatsapp_enabled,
            "whatsapp_store_link": whatsapp_store_link,
            "whatsapp_customer_link": whatsapp_customer_link,
            "whatsapp_store_configured": bool(store_number),
        },
    )

from django.contrib.admin.views.decorators import staff_member_required
import urllib.parse
from django.views.decorators.http import require_POST


@staff_member_required
def kitchen_panel_view(request):
    """Painel de cozinha em tempo real (atualiza automaticamente)."""
    settings_obj = _get_site_settings()
    return render(request, "orders/kitchen_panel.html", {"store_open": settings_obj.store_is_open})


@staff_member_required
def kitchen_orders_api(request):
    """Retorna pedidos em aberto para atualização do painel (JSON)."""
    orders = (
        Order.objects.prefetch_related("items", "items__addons")
        .exclude(status__in=["FINALIZADO", "CANCELADO"])
        .order_by("-created_at")[:80]
    )

    data = []
    max_id = 0
    for o in orders:
        max_id = max(max_id, o.id)
        data.append(
            {
                "id": o.id,
                "status": o.status,
                "created_at": o.created_at.isoformat(),
                "delivery_type": o.delivery_type,
                "customer_name": o.customer_name,
                "phone": o.phone,
                "address": o.address,
                "reference_point": o.reference_point,
                "notes": o.notes,
                "payment_method": o.payment_method,
                "payment_method_label": o.get_payment_method_display(),
                "cash_change_for": (str(o.cash_change_for) if o.cash_change_for else ""),
                "pix_status": o.mp_status,
                "paid": bool(o.paid_at),
                "total": str(o.total),
                "items": [
                    {
                        "product_name": it.product_name,
                        "quantity": it.quantity,
                        "size_label": it.size_label,
                        "addons": [
                            {"name": a.name, "qty": a.qty, "price": str(a.price)}
                            for a in it.addons.all()
                        ],
                    }
                    for it in o.items.all()
                ],
            }
        )

    return JsonResponse({"orders": data, "max_id": max_id})


@staff_member_required
def dashboard_view(request):
    orders = (Order.objects.prefetch_related("items", "items__addons")
              .exclude(status="FINALIZADO")
              .order_by("-created_at")[:50])
    s = _get_site_settings()
    whatsapp_enabled = bool(s.enable_whatsapp)
    store_number = normalize_phone_to_wa(s.whatsapp_store_number)

    if whatsapp_enabled:
        for o in orders:
            customer_number = normalize_phone_to_wa(o.phone)
            o.wa_customer_link = wa_link(customer_number, render_message(s.whatsapp_customer_message, o))
            o.wa_store_link = wa_link(store_number, render_message(s.whatsapp_store_message, o)) if store_number else ""
    else:
        for o in orders:
            o.wa_customer_link = ""
            o.wa_store_link = ""

    auto_wa_link = request.GET.get("wa_client") or ""

    return render(
        request,
        "orders/dashboard.html",
        {
            "orders": orders,
            "whatsapp_enabled": whatsapp_enabled,
            "whatsapp_store_configured": bool(store_number),
            "auto_wa_link": auto_wa_link,
        },
    )

@require_POST
@staff_member_required
def set_status_view(request, order_id):
    order = Order.objects.get(id=order_id)
    new_status = request.POST.get("status")

    allowed = {"NOVO", "PREPARANDO", "SAIU", "FINALIZADO", "CANCELADO"}

    wa_client_link = ""

    if new_status in allowed:
        order.status = new_status
        order.save()

        # Se virou "SAIU" (saiu para entrega), prepara WhatsApp automático pro cliente
        if new_status == "SAIU":
            try:
                from .models import SiteSettings
                from .services.whatsapp import normalize_phone_to_wa, render_message, wa_link

                settings_obj = SiteSettings.objects.first()
                if settings_obj and settings_obj.enable_whatsapp and settings_obj.whatsapp_auto_open_on_delivery:
                    phone_wa = normalize_phone_to_wa(getattr(order, "phone", ""))
                    msg_tpl = settings_obj.whatsapp_out_for_delivery_message
                    msg = render_message(msg_tpl, order)
                    wa_client_link = wa_link(phone_wa, msg)
            except Exception:
                wa_client_link = ""

    if wa_client_link:
        return redirect(f"/painel/?wa_client={urllib.parse.quote(wa_client_link, safe='')}")

    return redirect("orders_dashboard")

from django.utils import timezone
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate

@staff_member_required
def daily_report_view(request):
    """
    Relatório do dia (por padrão hoje). Pode filtrar com ?date=YYYY-MM-DD
    """
    date_str = request.GET.get("date")
    if date_str:
        try:
            selected_date = timezone.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            selected_date = timezone.localdate()
    else:
        selected_date = timezone.localdate()

    # Considera o dia inteiro (00:00 até 23:59)
    start = timezone.make_aware(timezone.datetime.combine(selected_date, timezone.datetime.min.time()))
    end = timezone.make_aware(timezone.datetime.combine(selected_date, timezone.datetime.max.time()))

    qs = Order.objects.filter(created_at__range=(start, end))

    total_orders = qs.count()
    total_value = qs.aggregate(v=Sum("total"))["v"] or 0

    # Se quiser excluir cancelados do faturamento:
    paid_like_value = qs.exclude(status="CANCELADO").aggregate(v=Sum("total"))["v"] or 0
    canceled_count = qs.filter(status="CANCELADO").count()

    by_status = list(
        qs.values("status")
          .annotate(qtd=Count("id"), total=Sum("total"))
          .order_by("status")
    )

    # Top itens (mais vendidos no dia)
    top_items = list(
        OrderItem.objects.filter(order__created_at__range=(start, end))
        .values("product_name")
        .annotate(qtd=Sum("quantity"))
        .order_by("-qtd")[:10]
    )

    return render(
        request,
        "orders/daily_report.html",
        {
            "selected_date": selected_date,
            "total_orders": total_orders,
            "total_value": total_value,
            "paid_like_value": paid_like_value,
            "canceled_count": canceled_count,
            "by_status": by_status,
            "top_items": top_items,
        },
    )

from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
import calendar
import csv

# Excel
from openpyxl import Workbook


def _month_range(selected_date):
    """Retorna (start_datetime, end_datetime) do mês da data informada."""
    year = selected_date.year
    month = selected_date.month
    last_day = calendar.monthrange(year, month)[1]

    start = timezone.make_aware(timezone.datetime(year, month, 1, 0, 0, 0))
    end = timezone.make_aware(timezone.datetime(year, month, last_day, 23, 59, 59))
    return start, end


@staff_member_required
def monthly_report_view(request):
    # Pega mês via ?month=YYYY-MM (se não vier, usa mês atual)
    month_str = request.GET.get("month")
    if month_str:
        try:
            year, month = month_str.split("-")
            selected_date = timezone.datetime(int(year), int(month), 1).date()
        except Exception:
            selected_date = timezone.localdate().replace(day=1)
    else:
        selected_date = timezone.localdate().replace(day=1)

    start, end = _month_range(selected_date)

    qs = Order.objects.filter(created_at__range=(start, end))

    total_orders = qs.count()
    total_value = qs.aggregate(v=Sum("total"))["v"] or 0
    total_no_canceled = qs.exclude(status="CANCELADO").aggregate(v=Sum("total"))["v"] or 0

    # Agrupar por dia
    by_day = list(
        qs.annotate(day=TruncDate("created_at"))
          .values("day")
          .annotate(qtd=Count("id"), total=Sum("total"))
          .order_by("day")
    )

    # Top itens do mês
    top_items = list(
        OrderItem.objects.filter(order__created_at__range=(start, end))
        .values("product_name")
        .annotate(qtd=Sum("quantity"))
        .order_by("-qtd")[:15]
    )

    context = {
        "selected_month": selected_date.strftime("%Y-%m"),
        "total_orders": total_orders,
        "total_value": total_value,
        "total_no_canceled": total_no_canceled,
        "by_day": by_day,
        "top_items": top_items,
    }
    return render(request, "orders/monthly_report.html", context)


@staff_member_required
def export_monthly_csv(request):
    month_str = request.GET.get("month") or timezone.localdate().strftime("%Y-%m")
    try:
        year, month = month_str.split("-")
        selected_date = timezone.datetime(int(year), int(month), 1).date()
    except Exception:
        selected_date = timezone.localdate().replace(day=1)

    start, end = _month_range(selected_date)

    qs = (
        Order.objects.filter(created_at__range=(start, end))
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(qtd=Count("id"), total=Sum("total"))
        .order_by("day")
    )

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="relatorio_mensal_{selected_date.strftime("%Y_%m")}.csv"'

    writer = csv.writer(response)
    writer.writerow(["Dia", "Pedidos", "Total (R$)"])
    for row in qs:
        writer.writerow([row["day"], row["qtd"], row["total"]])

    return response


@staff_member_required
def export_monthly_xlsx(request):
    month_str = request.GET.get("month") or timezone.localdate().strftime("%Y-%m")
    try:
        year, month = month_str.split("-")
        selected_date = timezone.datetime(int(year), int(month), 1).date()
    except Exception:
        selected_date = timezone.localdate().replace(day=1)

    start, end = _month_range(selected_date)

    qs = (
        Order.objects.filter(created_at__range=(start, end))
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(qtd=Count("id"), total=Sum("total"))
        .order_by("day")
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Relatorio Mensal"

    ws.append(["Dia", "Pedidos", "Total (R$)"])
    for row in qs:
        ws.append([str(row["day"]), int(row["qtd"]), float(row["total"] or 0)])

    # (Opcional) segunda aba: top itens
    ws2 = wb.create_sheet("Top Itens")
    ws2.append(["Item", "Quantidade"])
    top = (
        OrderItem.objects.filter(order__created_at__range=(start, end))
        .values("product_name")
        .annotate(qtd=Sum("quantity"))
        .order_by("-qtd")[:50]
    )
    for t in top:
        ws2.append([t["product_name"], int(t["qtd"])])

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="relatorio_mensal_{selected_date.strftime("%Y_%m")}.xlsx"'
    wb.save(response)
    return response
def track_order_view(request, token):
    # Carrega itens e opcionais (addons) para exibir no acompanhamento do cliente
    order = (
        Order.objects.prefetch_related("items__addons")
        .filter(public_token=token)
        .first()
    )
    if order is None:
        order = get_object_or_404(Order, public_token=token)

    return render(request, "orders/track.html", {"order": order})



# --- PIX / Mercado Pago ---

def pix_payment_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    if order.payment_method != "PIX":
        return redirect("order_success", order_id=order.id)

    return render(request, "orders/pix_payment.html", {"order": order})


def pix_status_api(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return JsonResponse({
        "order_id": order.id,
        "mp_status": order.mp_status,
        "paid": bool(order.paid_at),
    })


@csrf_exempt
def mercadopago_webhook(request):
    # valida segredo simples via querystring
    secret = request.GET.get("secret") or ""
    if secret != getattr(settings, "MERCADOPAGO_WEBHOOK_SECRET", ""):
        return JsonResponse({"ok": False, "error": "invalid secret"}, status=403)

    try:
        import json
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        payload = {}

    payment_id = None

    # Formatos comuns do webhook
    if isinstance(payload, dict):
        data = payload.get("data") or {}
        if isinstance(data, dict) and data.get("id"):
            payment_id = str(data.get("id"))

    # fallback: query params (às vezes vem topic/id)
    if not payment_id:
        pid = request.GET.get("id") or request.GET.get("data.id")
        if pid:
            payment_id = str(pid)

    if not payment_id:
        return JsonResponse({"ok": True, "ignored": True})

    # consulta o pagamento na API (fonte da verdade)
    try:
        p = consultar_pagamento(payment_id)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)

    status = str(p.get("status") or "")
    ext_ref = str(p.get("external_reference") or "")
    metadata = p.get("metadata") or {}
    order_id = metadata.get("order_id")

    order = None
    if order_id:
        try:
            order = Order.objects.get(id=int(order_id))
        except Exception:
            order = None

    if order is None and ext_ref:
        try:
            order = Order.objects.get(public_token=ext_ref)
        except Exception:
            order = None

    if order is None:
        return JsonResponse({"ok": True, "ignored": True})

    order.mp_payment_id = str(p.get("id") or order.mp_payment_id)
    order.mp_status = status

    # marca como pago quando aprovado
    if status == "approved" and not order.paid_at:
        order.paid_at = timezone.now()
        # opcional: você pode mudar status do pedido automaticamente aqui
        # order.status = "NOVO"
        order.save(update_fields=["mp_payment_id", "mp_status", "paid_at"])
    else:
        order.save(update_fields=["mp_payment_id", "mp_status"])

    return JsonResponse({"ok": True})


@require_POST
def toggle_store_open(request):
    settings_obj = _get_site_settings()
    settings_obj.store_is_open = not settings_obj.store_is_open
    settings_obj.save(update_fields=['store_is_open'])
    return redirect(request.META.get('HTTP_REFERER') or 'kitchen_panel')
