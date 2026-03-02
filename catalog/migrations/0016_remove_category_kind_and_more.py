from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0015_category_kind"),
    ]

    operations = [
        # Em versões anteriores existia o campo `kind` na Category.
        # Foi removido para simplificar e evitar filtros incorretos no cardápio.
        migrations.RemoveField(
            model_name="category",
            name="kind",
        ),
        # Garante que o campo exista com a definição atual (alguns deploys tinham opções diferentes).
        migrations.AlterField(
            model_name="productsize",
            name="allow_mix_categories",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Se marcado, só permite escolher sabores da mesma categoria do sabor base. "
                    "Se desmarcado, permite misturar categorias (ex.: doce + salgada)."
                ),
                verbose_name="Não permitir misturar doce/salgada",
            ),
        ),
    ]
