import re
import urllib.parse
from decimal import Decimal


def _only_digits(s: str) -> str:
    return re.sub(r"\D+", "", s or "")


def normalize_phone_to_wa(phone: str) -> str:
    """Retorna o telefone no formato wa.me (somente dígitos, com DDI).

    Regras:
    - Remove tudo que não for dígito
    - Se começar com '55' já considera BR ok
    - Se tiver 10 ou 11 dígitos, assume Brasil e prefixa 55
    """

    digits = _only_digits(phone)
    if not digits:
        return ""

    # já tem DDI Brasil
    if digits.startswith("55") and len(digits) >= 12:
        return digits

    # assume BR se veio só DDD+numero
    if len(digits) in (10, 11):
        return "55" + digits

    # fallback
    return digits


def format_money(value) -> str:
    try:
        v = Decimal(value)
        return f"{v:.2f}".replace(".", ",")
    except Exception:
        return str(value)


def build_items_text(order) -> str:
    linhas = []
    for it in order.items.all():
        tamanho = f" ({it.size_label})" if getattr(it, "size_label", "") else ""
        addons = list(getattr(it, "addons", []).all()) if hasattr(it, "addons") else []
        if addons:
            addons_txt = ", ".join([f"{getattr(a, 'qty', 1)}x {a.name} (+R$ {a.price})" for a in addons])
            linhas.append(f"- {it.quantity}x {it.product_name}{tamanho} | Opcionais: {addons_txt}")
        else:
            linhas.append(f"- {it.quantity}x {it.product_name}{tamanho}")
    return "\n".join(linhas) if linhas else "(sem itens)"


def render_message(template: str, order) -> str:
    data = {
        "nome": getattr(order, "customer_name", "") or "Cliente",
        "telefone": getattr(order, "phone", "") or "",
        "pedido": str(getattr(order, "id", "")),
        "total": format_money(getattr(order, "total", "0")),
        "tipo_entrega": getattr(order, "get_delivery_type_display", lambda: "")(),
        "pagamento": getattr(order, "get_payment_method_display", lambda: "")(),
        "endereco": getattr(order, "address", "") or "",
        "referencia": getattr(order, "reference_point", "") or "",
        "itens": build_items_text(order),
    }

    msg = template or ""
    for k, v in data.items():
        msg = msg.replace("{" + k + "}", str(v))
    return msg


def _encode_wa_text(message: str) -> str:
    """Codifica texto para WhatsApp preservando quebras de linha.

    - Normaliza CRLF/CR para LF
    - URL-encode (LF vira %0A)
    """
    # Normaliza quebras e garante que elas virem %0A (WhatsApp entende isso em wa.me e api.whatsapp.com)
    msg = (message or "")
    msg = msg.replace("\r\n", "\n").replace("\r", "\n")

    # Alguns handlers do WhatsApp/navegadores são inconsistentes com \n mesmo URL-encoded.
    # Então convertemos explicitamente para o token %0A e preservamos o '%'.
    msg = msg.replace("\n", "%0A")

    # Encode geral mantendo o token %0A intacto
    return urllib.parse.quote(msg, safe="%")


def wa_link(phone_wa: str, message: str, mode: str = "api") -> str:
    """Gera link do WhatsApp.

    mode:
      - "api"  -> https://api.whatsapp.com/send?phone=...&text=...
      - "wa"   -> https://wa.me/... ?text=...
    """
    if not phone_wa:
        return ""

    text = _encode_wa_text(message)
    mode = (mode or "").lower().strip()

    if mode in ("wa", "wame", "wa.me"):
        return f"https://wa.me/{phone_wa}?text={text}"

    # padrão: api.whatsapp.com (mais compatível em desktop/mobile)
    return f"https://api.whatsapp.com/send?phone={phone_wa}&text={text}"
