from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from ferry.accounts.models import APIToken, Person, User


class PersonAdmin(admin.ModelAdmin):
    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("id", "display_name", "discord_id", "autopub", "created_at", "updated_at")
    list_display = ("display_name", "discord_id", "autopub")


class InlineAPITokenAdmin(admin.TabularInline):
    model = APIToken
    readonly_fields = ("token", "created_at", "updated_at")
    extra = 0


class FerryUserAdmin(UserAdmin):
    inlines = [InlineAPITokenAdmin]
    readonly_fields = ["last_login", "date_joined"]

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "email")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
        (
            _("Ferry Service"),
            {
                "fields": ("person",),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )


admin.site.register(User, FerryUserAdmin)
admin.site.unregister(Group)
admin.site.register(Person, PersonAdmin)
