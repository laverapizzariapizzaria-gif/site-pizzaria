from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Order
from .printing import print_order


@receiver(post_save, sender=Order)
def auto_print_on_new_order(sender, instance: Order, created: bool, **kwargs):
    # Imprime ao criar o pedido.
    # Se preferir imprimir somente quando status virar "PREPARANDO" ou "NOVO",
    # dá para mudar a regra aqui.
    if created:
        try:
            print_order(instance)
        except Exception as e:
            # Nunca pode quebrar a criação do pedido por causa da impressora.
            print(f"[PRINT ERROR] {e}")
