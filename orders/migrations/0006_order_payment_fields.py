from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0005_printerprofile_and_item_size"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="payment_method",
            field=models.CharField(choices=[("PIX", "Pix"), ("CARTAO", "Cartão (débito/crédito)"), ("DINHEIRO", "Dinheiro")], default="PIX", max_length=20),
        ),
        migrations.AddField(
            model_name="order",
            name="cash_change_for",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
