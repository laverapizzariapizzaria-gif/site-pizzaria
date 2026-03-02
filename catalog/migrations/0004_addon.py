from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_productsize"),
    ]

    operations = [
        migrations.CreateModel(
            name="AddOn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=80)),
                ("price", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("is_active", models.BooleanField(default=True)),
                (
                    "categories",
                    models.ManyToManyField(blank=True, related_name="addons", to="catalog.category"),
                ),
            ],
            options={
                "verbose_name": "Opcional",
                "verbose_name_plural": "Opcionais",
                "ordering": ["name"],
            },
        ),
    ]
