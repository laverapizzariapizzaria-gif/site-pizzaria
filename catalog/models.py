from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=60, unique=True)

    counts_as_flavor = models.BooleanField(
        default=True,
        verbose_name="Conta como sabor",
        help_text=(
            "Se marcado, produtos desta categoria contam no limite de sabores da pizza (meio-a-meio). "
            "Se desmarcado (ex.: Bebidas), continuam com checkbox no cardápio, mas NÃO contam como sabor."
        ),
    )

    def __str__(self):
        return self.name


class AddOnCategory(models.Model):
    """Categoria de opcionais (ex.: Borda, Extras, Remover ingredientes)."""

    name = models.CharField(max_length=60, unique=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Categoria de opcionais"
        verbose_name_plural = "Categorias de opcionais"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class AddOn(models.Model):
    """Opcional/adicional (ex: borda recheada, extra queijo, sem cebola).

    No modo "iFood":
    - O opcional pertence a uma *categoria* (borda/extras/etc.)
    - O produto (pizza) escolhe quais opcionais aparecem.
    """

    name = models.CharField(max_length=80)
    category = models.ForeignKey(AddOnCategory, on_delete=models.PROTECT, related_name="addons")
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    is_free = models.BooleanField(
        default=False,
        help_text="Se marcado, este opcional será tratado como gratuito (R$ 0,00) mesmo que o preço esteja preenchido.",
        verbose_name="Gratuito",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Opcional"
        verbose_name_plural = "Opcionais"
        ordering = ["category__sort_order", "category__name", "name"]

    def get_price(self):
        return 0 if self.is_free else self.price

    def __str__(self):
        price = self.get_price()
        return f"{self.name} ({self.category}) (+R$ {price})"


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='Imagem')
    promo_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, verbose_name='Preço promocional')

    no_price_increase = models.BooleanField(default=False, verbose_name="Sabor não aumenta preço", help_text="Se marcado, quando este produto for escolhido como sabor em pizzas meio-a-meio, ele não aumenta o preço.")

    second_flavor_extra = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Acréscimo como 2º sabor", help_text="Valor que será somado ao preço do tamanho quando este sabor for escolhido como 2º (ou 3º, 4º...) sabor em pizzas meio-a-meio. Ex.: Frango +R$ 12,00")

    is_active = models.BooleanField(default=True)

    # Opcionais permitidos para este produto (modo iFood)
    addons = models.ManyToManyField(AddOn, related_name="products", blank=True, verbose_name="Opcionais disponíveis")

    def __str__(self):
        return f"{self.name} ({self.category.name})"


class ProductSize(models.Model):
    """Preço por tamanho (útil para pizzas com valores diferentes).

    Mantém compatibilidade: produtos que não têm tamanhos continuam usando
    `Product.price`.
    """

    SIZE_CHOICES = (
        ("P", "Pequena"),
        ("M", "Média"),
        ("G", "Grande"),
        ("BIG", "Big"),
    )

    product = models.ForeignKey(Product, related_name="sizes", on_delete=models.CASCADE)
    # Precisa comportar "BIG" (3 caracteres)
    size = models.CharField(max_length=3, choices=SIZE_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    promo_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Preço promocional (tamanho)", help_text="Opcional: preço promocional específico para este tamanho. Se preenchido, substitui o preço normal e também tem prioridade sobre a promoção geral do produto.")
    price_two_flavors = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Preço para 2 sabores", help_text="Opcional: se preenchido, ao escolher 2 sabores neste tamanho o sistema usará este valor (em vez de calcular pelo maior preço).")
    max_flavors = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Máx. de sabores",
        help_text="Quantos sabores diferentes podem ser escolhidos neste tamanho (ex.: 2 para meio-a-meio).",
    )

    allow_mix_categories = models.BooleanField(
        default=False,
        verbose_name="Não permitir misturar doce/salgada",
        help_text=(
            "Se marcado, só permite escolher sabores da mesma categoria do sabor base. "
            "Se desmarcado, permite misturar categorias (ex.: doce + salgada)."
        ),
    )

    class Meta:
        unique_together = ("product", "size")
        ordering = ["product_id", "size"]

    def __str__(self):
        return f"{self.product.name} - {self.get_size_display()} (R$ {self.price})"


class ProductAddOnRule(models.Model):
    """Regras de opcionais por PRODUTO x CATEGORIA (min/max/obrigatório)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="addon_rules")
    category = models.ForeignKey(AddOnCategory, on_delete=models.CASCADE, related_name="product_rules")

    enabled = models.BooleanField(default=True, verbose_name="Ativo")
    min_select = models.PositiveIntegerField(default=0, verbose_name="Mínimo (obrigatório)")
    max_select = models.PositiveIntegerField(default=0, verbose_name="Máximo (0 = sem limite)")

    class Meta:
        unique_together = ("product", "category")
        verbose_name = "Regra de opcionais"
        verbose_name_plural = "Regras de opcionais"
        ordering = ["category__sort_order", "category__name"]

    def __str__(self):
        return f"{self.product} - {self.category} (min={self.min_select}, max={self.max_select or '∞'})"
