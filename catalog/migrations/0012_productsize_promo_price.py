from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0011_product_second_flavor_extra"),
    ]

    operations = [
        migrations.AddField(
            model_name="productsize",
            name="promo_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Opcional: preço promocional específico para este tamanho. Se preenchido, substitui o preço normal e também tem prioridade sobre a promoção geral do produto.",
                max_digits=10,
                null=True,
                verbose_name="Preço promocional (tamanho)",
            ),
        ),
    ]
