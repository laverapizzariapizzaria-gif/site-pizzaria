from __future__ import annotations

from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm, UserCreationForm
from django.core import signing
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from orders.models import Order


User = get_user_model()
signer = signing.TimestampSigner(salt="pizzaria-account-claim")


def register_view(request: HttpRequest) -> HttpResponse:
    """Cadastro manual (email + senha).

    Mesmo com o cadastro automático no checkout, vale manter essa tela no menu.
    """

    class RegisterForm(UserCreationForm):
        class Meta(UserCreationForm.Meta):
            model = User
            fields = ("username",)

    if request.method == "POST":
        form = RegisterForm(request.POST)
        email = (request.POST.get("email") or "").strip().lower()
        username = (request.POST.get("username") or email).strip().lower()

        # Validar email
        if not email:
            form.add_error(None, "Informe um email.")
        else:
            # Evita duplicar email
            if User.objects.filter(email__iexact=email).exists():
                form.add_error(None, "Esse email já está em uso. Faça login.")

        if form.is_valid() and not form.errors:
            user = form.save(commit=False)
            user.username = username or email
            user.email = email
            user.save()
            login(request, user)
            return redirect("my_orders")
    else:
        form = RegisterForm()

    return render(request, "users/register.html", {"form": form})


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("my_orders")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect("my_orders")
    else:
        form = AuthenticationForm(request)

    return render(request, "registration/login.html", {"form": form})


@login_required
def my_orders_view(request: HttpRequest) -> HttpResponse:
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "users/my_orders.html", {"orders": orders})


def logout_view(request: HttpRequest) -> HttpResponse:
    """Sair da conta."""
    logout(request)
    return redirect("menu")


def claim_account_set_password_view(request: HttpRequest, token: str) -> HttpResponse:
    """Tela para definir senha da conta criada automaticamente no checkout.

    O token é assinado e expira (por padrão em 7 dias).
    """

    try:
        user_id = signer.unsign(token, max_age=7 * 24 * 60 * 60)
        user = User.objects.get(pk=int(user_id))
    except Exception:
        return render(
            request,
            "users/claim_invalid.html",
            {
                "login_url": reverse("login"),
            },
            status=400,
        )

    if request.user.is_authenticated and request.user.pk != user.pk:
        # Evita que um usuário logado troque senha de outro.
        return redirect("my_orders")

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            login(request, user)
            return redirect("my_orders")
    else:
        form = SetPasswordForm(user)

    return render(
        request,
        "users/claim_set_password.html",
        {
            "form": form,
            "email": user.email,
        },
    )


def build_claim_link(request: HttpRequest, user) -> str:
    token = signer.sign(str(user.pk))
    return request.build_absolute_uri(reverse("claim_set_password", args=[token]))
