from decimal import Decimal

from django.test import RequestFactory, TestCase

from catalog.cart import add_to_cart, cart_items_and_total
from catalog.models import AddOn, AddOnCategory, Category, Product, ProductSize


class CartCalculationTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        cat = Category.objects.create(name="Pizzas")
        self.product = Product.objects.create(category=cat, name="Calabresa", price=Decimal("30.00"))
        ProductSize.objects.create(product=self.product, size="G", price=Decimal("42.00"))

        addon_cat = AddOnCategory.objects.create(name="Borda")
        self.addon = AddOn.objects.create(name="Catupiry", category=addon_cat, price=Decimal("5.00"))

    def _request_with_session(self):
        request = self.factory.get("/")
        session = self.client.session
        session.save()
        request.session = session
        return request

    def test_cart_total_uses_selected_size_and_addons(self):
        request = self._request_with_session()
        add_to_cart(request, self.product.id, qty=2, size_code="G", addons={str(self.addon.id): 1})

        items, total = cart_items_and_total(request)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["size_label"], "Grande")
        self.assertEqual(items[0]["price"], Decimal("42.00"))
        self.assertEqual(items[0]["addons_unit_total"], Decimal("5.00"))
        self.assertEqual(items[0]["subtotal"], Decimal("94.00"))
        self.assertEqual(total, Decimal("94.00"))
