from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, ReadOnlyPasswordHashWidget
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import CustomUser


class SimplePasswordWidget(ReadOnlyPasswordHashWidget):
    def render(self, name, value, attrs=None, renderer=None):
        return format_html(
            '<strong>********</strong>'
            '<p><a role="button" class="button" href="../password/">{}</a></p>',
            _("Restablecer contraseña")
        )


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = CustomUser

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password'].widget = SimplePasswordWidget()


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    form = CustomUserChangeForm

    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Información personal', {'fields': ('first_name', 'last_name', 'role')}),
        ('Permisos', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions'
            )
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'first_name',
                'last_name',
                'role',
                'password1',
                'password2',
                'is_staff',
                'is_superuser',
            ),
        }),
    )

    search_fields = ('email',)