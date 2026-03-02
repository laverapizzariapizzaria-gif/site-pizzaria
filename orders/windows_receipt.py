"""Impressão de cupom 58mm via fila do Windows (spooler).

Este método é o mais estável no Windows: o sistema só precisa saber o nome
da impressora (como aparece em "Impressoras e scanners").
"""

import os
import tempfile
from decimal import Decimal


MM_TO_PT = 72 / 25.4
PAPER_WIDTH_MM = 58
PAGE_WIDTH = PAPER_WIDTH_MM * MM_TO_PT  # ~164.4 pt


def _money(v):
    try:
        v = Decimal(v)
    except Exception:
        v = Decimal("0")
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


def _send_pdf_to_printer_windows(pdf_path: str, printer_name: str):
    import win32api
    import win32print

    current = win32print.GetDefaultPrinter()
    try:
        win32print.SetDefaultPrinter(printer_name)
        # Envia para a fila do Windows. O driver decide o layout final.
        win32api.ShellExecute(0, "print", pdf_path, None, ".", 0)
    finally:
        win32print.SetDefaultPrinter(current)


def make_receipt_pdf_58mm(order, path: str):
    # Import local para não exigir reportlab em contextos que não usam impressão
    from reportlab.pdfgen import canvas

    line_h = 10
    # altura estimada (base + linhas dos itens + margem)
    items_count = getattr(order, "items", None).all().count() if getattr(order, "items", None) else 0
    height = (22 + (items_count * 3)) * line_h + 90

    c = canvas.Canvas(path, pagesize=(PAGE_WIDTH, height))
    y = height - 14

    def txt(s, bold=False, size=9):
        nonlocal y
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        # margem esquerda 6pt
        # limita largura (evita estourar)
        c.drawString(6, y, (s or "")[:64])
        y -= line_h

    txt("PIZZARIA", bold=True, size=12)
    txt(f"Pedido #{getattr(order, 'id', '')}", bold=True)
    txt("-" * 32)

    txt("CLIENTE:", bold=True)
    txt(getattr(order, "customer_name", "-") or "-")
    phone = getattr(order, "phone", "") or ""
    if phone:
        txt(f"Tel: {phone}")

    delivery_type = getattr(order, "delivery_type", "RETIRADA")
    if str(delivery_type).upper().startswith("ENTREGA"):
        txt("ENTREGA", bold=True)
        addr = (getattr(order, "address", "") or "").strip()
        while addr:
            txt(addr[:32])
            addr = addr[32:]
    else:
        txt("RETIRADA NO BALCAO", bold=True)

    notes = (getattr(order, "notes", "") or "").strip()
    if notes:
        txt("OBS:", bold=True)
        while notes:
            txt(notes[:32])
            notes = notes[32:]

    txt("-" * 32)
    txt("ITENS:", bold=True)

    subtotal = Decimal("0")
    items = getattr(order, "items", None)
    if items is not None:
        for item in items.all():
            qty = getattr(item, "quantity", 0) or 0
            name = getattr(item, "product_name", "") or ""
            size = getattr(item, "size_label", "") or ""
            size_txt = f" ({size})" if size else ""
            txt(f"{qty}x {name}{size_txt}")

            unit = getattr(item, "unit_price", 0) or 0
            total_line = (Decimal(unit) * Decimal(qty))
            subtotal += total_line
            txt(_money(total_line))

    txt("-" * 32)

    delivery_fee = getattr(order, "delivery_fee", 0) or 0
    total = getattr(order, "total", None)
    if total is None or Decimal(total) == Decimal("0"):
        total = subtotal + Decimal(delivery_fee)

    if Decimal(delivery_fee) > 0:
        txt(f"Entrega: {_money(delivery_fee)}")
    txt(f"TOTAL: {_money(total)}", bold=True)

    # espaço extra para destacar
    txt(" ")
    txt(" ")
    txt(" ")

    c.showPage()
    c.save()


def print_order_receipt_windows(order, printer_name: str):
    if not printer_name:
        raise RuntimeError("Nome da impressora do Windows não configurado.")

    tmp = tempfile.gettempdir()
    pdf_path = os.path.join(tmp, f"pedido_{getattr(order, 'id', 'x')}_58mm.pdf")
    make_receipt_pdf_58mm(order, pdf_path)
    _send_pdf_to_printer_windows(pdf_path, printer_name)


def print_test_receipt_windows(printer_name: str):
    """Imprime um cupom de teste (sem depender de um pedido)."""
    from reportlab.pdfgen import canvas

    if not printer_name:
        raise RuntimeError("Nome da impressora do Windows não configurado.")

    tmp = tempfile.gettempdir()
    pdf_path = os.path.join(tmp, "cupom_teste_58mm.pdf")
    height = 220
    c = canvas.Canvas(pdf_path, pagesize=(PAGE_WIDTH, height))
    y = height - 14
    c.setFont("Helvetica-Bold", 12)
    c.drawString(6, y, "TESTE - PIZZARIA")
    y -= 18
    c.setFont("Helvetica", 9)
    c.drawString(6, y, "Se saiu este cupom, está OK.")
    y -= 12
    c.drawString(6, y, "58mm - Windows spooler")
    y -= 12
    c.drawString(6, y, "-")
    c.showPage()
    c.save()

    _send_pdf_to_printer_windows(pdf_path, printer_name)
