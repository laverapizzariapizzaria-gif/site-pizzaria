from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0016_remove_category_kind_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="counts_as_flavor",
            field=models.BooleanField(
                default=True,
                help_text=(
                    "Se marcado, produtos desta categoria contam no limite de sabores da pizza (meio-a-meio). "
                    "Se desmarcado (ex.: Bebidas), continuam com checkbox no cardápio, mas NÃO contam como sabor."
                ),
                verbose_name="Conta como sabor",
            ),
        ),
    ]
