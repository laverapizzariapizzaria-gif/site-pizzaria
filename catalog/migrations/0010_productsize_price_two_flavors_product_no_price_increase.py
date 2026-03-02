from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0009_productsize_max_flavors"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="no_price_increase",
            field=models.BooleanField(
                default=False,
                help_text="Se marcado, quando este produto for escolhido como sabor em pizzas meio-a-meio, ele não aumenta o preço.",
                verbose_name="Sabor não aumenta preço",
            ),
        ),
        migrations.AddField(
            model_name="productsize",
            name="price_two_flavors",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Opcional: se preenchido, ao escolher 2 sabores neste tamanho o sistema usará este valor (em vez de calcular pelo maior preço).",
                max_digits=10,
                null=True,
                verbose_name="Preço para 2 sabores",
            ),
        ),
    ]
