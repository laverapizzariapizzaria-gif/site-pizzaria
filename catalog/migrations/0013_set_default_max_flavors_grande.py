from django.db import migrations


def set_default_max_flavors_grande(apps, schema_editor):
    """Define 2 sabores como padrão para tamanho G em registros já existentes.

    Muitos bancos já têm os tamanhos cadastrados com max_flavors=1 (padrão).
    Isso faz o cardápio esconder as caixinhas de sabores.

    Ajusta apenas os tamanhos 'G' que ainda estão com 1 sabor.
    """

    ProductSize = apps.get_model("catalog", "ProductSize")

    # Ajusta somente quando ainda está no padrão (1)
    ProductSize.objects.filter(size="G", max_flavors=1).update(max_flavors=2)


def noop_reverse(apps, schema_editor):
    # não reverte automaticamente (evita desfazer configurações manuais do admin)
    return


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0012_productsize_promo_price"),
    ]

    operations = [
        migrations.RunPython(set_default_max_flavors_grande, reverse_code=noop_reverse),
    ]
