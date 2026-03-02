from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0005_ifood_addons"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="promo_price",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name="Preço promocional"),
        ),
        migrations.AlterField(
            model_name="product",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="products/"),
        ),
    ]
