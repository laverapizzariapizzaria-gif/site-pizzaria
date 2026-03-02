from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.conf import settings

try:
    import mercadopago
except Exception as e:
    mercadopago = None


@dataclass
class PixPayload:
    payment_id: str
    status: str
    qr_code_base64: str
    qr_code: str


def _sdk():
    if mercadopago is None:
        raise RuntimeError("Biblioteca 'mercadopago' não instalada. Rode: pip install mercadopago")
    if not settings.MERCADOPAGO_ACCESS_TOKEN:
        raise RuntimeError("MERCADOPAGO_ACCESS_TOKEN não configurado (settings ou variável de ambiente).")
    return mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)


def criar_pagamento_pix(order) -> PixPayload:
    """Cria um pagamento PIX no Mercado Pago e devolve QR base64 + copia/cola."""
    sdk = _sdk()

    # Mercado Pago exige um e-mail válido no payer.
    payer_email = (getattr(order, "customer_email", "") or "").strip().lower() or f"cliente{order.id}@pizzaria.com"

    # CPF no formato somente números (11 dígitos)
    cpf_raw = (getattr(order, "customer_cpf", "") or "").strip()
    cpf_digits = cpf_raw.replace(".", "").replace("-", "").replace(" ", "")

    notification_url = f"{settings.SITE_BASE_URL}/webhooks/mercadopago/?secret={settings.MERCADOPAGO_WEBHOOK_SECRET}"

    payer = {
        "email": payer_email,
        "first_name": (getattr(order, "customer_name", "") or "Cliente").strip()[:60],
    }
    # Envia CPF quando disponível (recomendado para reduzir reprovações/validações)
    if cpf_digits and cpf_digits.isdigit() and len(cpf_digits) == 11:
        payer["identification"] = {"type": "CPF", "number": cpf_digits}

    payment_data = {
        "transaction_amount": float(order.total),
        "description": f"Pedido #{order.id} - Pizzaria",
        "payment_method_id": "pix",
        "payer": payer,
        # vincula o pagamento ao pedido
        "external_reference": str(order.public_token),
        "metadata": {"order_id": order.id},
        "notification_url": notification_url,
    }

    result = sdk.payment().create(payment_data)
    payment = result.get("response") or {}

    poi = (payment.get("point_of_interaction") or {}).get("transaction_data") or {}
    qr_base64 = poi.get("qr_code_base64") or ""
    qr_code = poi.get("qr_code") or ""

    return PixPayload(
        payment_id=str(payment.get("id") or ""),
        status=str(payment.get("status") or ""),
        qr_code_base64=qr_base64,
        qr_code=qr_code,
    )


def consultar_pagamento(payment_id: str) -> dict:
    sdk = _sdk()
    result = sdk.payment().get(payment_id)
    return result.get("response") or {}
