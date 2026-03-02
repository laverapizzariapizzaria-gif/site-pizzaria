"""Rotinas de impressão de pedidos.

Windows + impressora 58mm:
- Usa a fila do Windows (spooler) com o nome da impressora configurado no Admin.
"""

from .models import PrinterProfile
from .windows_receipt import print_order_receipt_windows


def get_default_printer() -> PrinterProfile | None:
    return PrinterProfile.objects.filter(is_default=True).first()


def print_order(order) -> None:
    printer = get_default_printer()
    if not printer:
        return
    if not printer.auto_print:
        return

    if not printer.windows_printer_name:
        # Sem nome configurado ainda.
        return

    print_order_receipt_windows(order, printer.windows_printer_name)
