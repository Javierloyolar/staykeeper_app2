from django.contrib import admin
from django.utils.html import format_html
from .models import OwnerFinancialTransaction, OwnerPayout


# ─── FINANCIAL TRANSACTION ───

@admin.register(OwnerFinancialTransaction)
class OwnerFinancialTransactionAdmin(admin.ModelAdmin):

    list_display    = ('id', 'listing', 'booking', 'get_type_badge', 'category', 'formatted_amount', 'get_owner_share', 'transaction_date')
    list_filter     = ('transaction_type', 'category', 'owner_impact', 'transaction_date', 'listing')
    search_fields   = ('description', 'booking__reservation_code', 'listing__name')
    readonly_fields = ('created_at', 'owner_share', 'admin_share')

    def get_type_badge(self, obj):
        if obj.transaction_type == 'income':
            return format_html('<span style="background:#d1fae5;color:#065f46;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">▲ Ingreso</span>')
        return format_html('<span style="background:#fee2e2;color:#991b1b;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:bold">▼ Egreso</span>')
    get_type_badge.short_description = 'Tipo'

    def formatted_amount(self, obj):
        return f"${obj.amount:,}"
    formatted_amount.short_description = 'Monto'

    def get_owner_share(self, obj):
        signo = "+" if obj.owner_share >= 0 else ""
        return f"{signo}${obj.owner_share:,}"
    get_owner_share.short_description = 'Parte Owner'

    def has_change_permission(self, request, obj=None):
        return False


# ─── INLINE para property_charges ───

class PropertyChargesInline(admin.TabularInline):
    model   = OwnerPayout.property_charges.through
    extra   = 0
    verbose_name = "Gasto de propiedad"
    verbose_name_plural = "Gastos de propiedad incluidos"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'ownerfinancialtransaction':
            kwargs['queryset'] = OwnerFinancialTransaction.objects.filter(
                booking__isnull=True
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# ─── OWNER PAYOUT ───

@admin.register(OwnerPayout)
class OwnerPayoutAdmin(admin.ModelAdmin):

    list_display    = ('id', 'get_reservation_code', 'base_amount', 'get_total_extras', 'get_net_amount', 'get_status_badge', 'scheduled_date', 'paid_date')
    list_filter     = ('status', 'scheduled_date', 'booking__listing')
    search_fields   = ('booking__reservation_code', 'notes')
    readonly_fields = ('base_amount', 'get_net_amount', 'get_total_extras', 'get_property_charges_total')
    inlines         = [PropertyChargesInline]

    fieldsets = (
        ('Reserva', {
            'fields': ('booking',)
        }),
        ('Montos', {
            'fields': ('base_amount', 'get_total_extras', 'get_property_charges_total', 'get_net_amount'),
            'description': 'net = base + extras de reserva − gastos de propiedad'
        }),
        ('Pago', {
            'fields': ('status', 'scheduled_date', 'paid_date', 'payment_method', 'notes')
        }),
    )

    def get_reservation_code(self, obj):
        return obj.booking.reservation_code if obj.booking else "Sin Reserva"
    get_reservation_code.short_description = 'Reserva'

    def get_total_extras(self, obj):
        monto = obj.booking_transactions_total
        signo = "+" if monto >= 0 else ""
        return f"{signo}${monto:,}"
    get_total_extras.short_description = 'Extras Reserva'

    def get_property_charges_total(self, obj):
        monto = obj.property_charges_total
        signo = "+" if monto >= 0 else ""
        return f"{signo}${monto:,}"
    get_property_charges_total.short_description = 'Gastos Propiedad'

    def get_net_amount(self, obj):
        return format_html('<strong style="color:#065f46">${}</strong>', f"{obj.net_amount:,}")
    get_net_amount.short_description = 'Neto a Pagar'

    def get_status_badge(self, obj):
        if obj.status == 'paid':
            return format_html('<span style="background:#d1fae5;color:#065f46;padding:2px 10px;border-radius:4px;font-size:11px;font-weight:bold">✓ Pagado</span>')
        return format_html('<span style="background:#fef3c7;color:#92400e;padding:2px 10px;border-radius:4px;font-size:11px;font-weight:bold">⏳ Pendiente</span>')
    get_status_badge.short_description = 'Estado'

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status == 'paid':
            return [f.name for f in obj._meta.fields] + ['get_net_amount', 'get_total_extras', 'get_property_charges_total']
        return self.readonly_fields

    actions = ['marcar_como_pagado']

    @admin.action(description='Marcar seleccionados como Pagados')
    def marcar_como_pagado(self, request, queryset):
        pendientes = queryset.filter(status='pending')
        for payout in pendientes:
            payout.mark_as_paid()
        self.message_user(request, f"{pendientes.count()} pago(s) marcados como pagados.")