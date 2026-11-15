from django.contrib import admin
from django.utils.html import format_html

from .models import Category, Product, ProductBatch
from .signals import stock_changed


class ProductBatchInline(admin.TabularInline):
    model = ProductBatch
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock_badge", "nearest_expiry", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("name", "sku")
    inlines = [ProductBatchInline]

    def get_readonly_fields(self, request, obj=None):
        # Stock follows the batches; products without batches can have their stock typed in.
        return ("stock_qty",) if obj and obj.batches.exists() else ()

    @admin.display(description="Stock")
    def stock_badge(self, obj):
        colour = "#c0392b" if obj.is_low_stock else "#3DA535"
        return format_html('<b style="color:{}">{}</b>', colour, obj.stock_qty)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.recalc_stock()
        stock_changed.send(sender=Product, product=form.instance, batch=None)


@admin.register(ProductBatch)
class ProductBatchAdmin(admin.ModelAdmin):
    list_display = ("product", "batch_no", "qty", "expiry_date", "days_left")
    list_filter = ("expiry_date",)
    search_fields = ("product__name", "batch_no")
    ordering = ("expiry_date",)

    @admin.display(description="Days left")
    def days_left(self, obj):
        return obj.days_to_expiry
