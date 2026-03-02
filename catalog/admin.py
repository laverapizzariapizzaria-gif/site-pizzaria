from django.contrib import admin
from .models import Category, Product, ProductSize, AddOn, AddOnCategory, ProductAddOnRule


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "counts_as_flavor")
    list_editable = ("counts_as_flavor",)
    list_filter = ("counts_as_flavor",)
    search_fields = ("name",)
    fields = ("name", "counts_as_flavor")


class ProductAddOnRuleInline(admin.TabularInline):
    model = ProductAddOnRule
    extra = 0


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "promo_price", "no_price_increase", "second_flavor_extra", "is_active")
    list_filter = ("category", "no_price_increase", "is_active")
    search_fields = ("name",)
    filter_horizontal = ("addons",)
    inlines = [ProductAddOnRuleInline]


@admin.register(ProductSize)
class ProductSizeAdmin(admin.ModelAdmin):
    list_display = ("product", "size", "price", "promo_price", "price_two_flavors", "max_flavors")
    list_editable = ("price", "promo_price", "price_two_flavors", "max_flavors")
    list_filter = ("size",)
    search_fields = ("product__name",)


@admin.register(AddOnCategory)
class AddOnCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "sort_order")
    list_editable = ("sort_order",)
    search_fields = ("name",)


@admin.register(AddOn)
class AddOnAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "is_free", "is_active")
    list_filter = ("is_active", "category", "is_free")
    search_fields = ("name",)
