from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0004_order_delivery_fee"),
    ]

    operations = [
        migrations.AddField(
            model_name="orderitem",
            name="size_code",
            field=models.CharField(blank=True, default="", max_length=10),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="size_label",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.CreateModel(
            name="PrinterProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(default="Impressora do balcão", max_length=80)),
                ("windows_printer_name", models.CharField(blank=True, max_length=200, null=True)),
                ("is_default", models.BooleanField(default=False)),
                ("auto_print", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
