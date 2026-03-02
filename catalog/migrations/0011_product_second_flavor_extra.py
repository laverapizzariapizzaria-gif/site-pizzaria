from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0010_productsize_price_two_flavors_product_no_price_increase"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="second_flavor_extra",
            field=models.DecimalField(
                default=0,
                decimal_places=2,
                max_digits=10,
                verbose_name="Acréscimo como 2º sabor",
                help_text="Valor que será somado ao preço do tamanho quando este sabor for escolhido como 2º (ou 3º, 4º...) sabor em pizzas meio-a-meio. Ex.: Frango +R$ 12,00",
            ),
        ),
    ]
