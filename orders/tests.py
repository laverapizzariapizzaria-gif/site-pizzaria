from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Product, ProductSize
from orders.models import Order


class OrderViewsTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name="Pizzas")
        product = Product.objects.create(category=cat, name="Mussarela", price=Decimal("30.00"), is_active=True)
        ProductSize.objects.create(product=product, size="G", price=Decimal("40.00"))

        session = self.client.session
        session["cart"] = {
            f"{product.id}:G:": {
                "product_id": product.id,
                "qty": 1,
                "size_code": "G",
                "addons": {},
                "flavors": [],
            }
        }
        session.save()

    def test_checkout_rejects_invalid_email(self):
        response = self.client.post(reverse("checkout"), data={
            "name": "Julian",
            "email": "email-invalido",
            "cpf": "12345678901",
            "phone": "47999999999",
            "delivery_type": "RETIRADA",
            "payment_method": "PIX",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Informe um email válido.")
        self.assertEqual(Order.objects.count(), 0)

    def test_order_success_returns_404_for_missing_order(self):
        response = self.client.get(reverse("order_success", args=[999999]))
        self.assertEqual(response.status_code, 404)

    def test_kitchen_api_returns_reference_point(self):
        user = get_user_model().objects.create_user(username="staff", password="123", is_staff=True)
        order = Order.objects.create(
            customer_name="Cliente",
            customer_email="cliente@example.com",
            customer_cpf="12345678901",
            phone="47999999999",
            delivery_type="ENTREGA",
            address="Rua A, 123",
            reference_point="Perto da praça",
            payment_method="PIX",
            total=Decimal("45.00"),
        )

        self.client.force_login(user)
        response = self.client.get(reverse("kitchen_orders_api"))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["orders"][0]["id"], order.id)
        self.assertEqual(payload["orders"][0]["reference_point"], "Perto da praça")

    @patch("orders.views.criar_pagamento_pix")
    def test_checkout_creates_order_without_delivery_fee_for_pickup(self, mocked_pix):
        mocked_pix.side_effect = RuntimeError("PIX temporariamente indisponível")

        response = self.client.post(reverse("checkout"), data={
            "name": "Julian",
            "email": "cliente@example.com",
            "cpf": "12345678901",
            "phone": "47999999999",
            "delivery_type": "RETIRADA",
            "payment_method": "PIX",
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        order = Order.objects.latest("id")
        self.assertEqual(order.delivery_fee, Decimal("0.00"))
        self.assertEqual(order.address, "")
