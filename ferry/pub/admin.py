from typing import Any

from django import forms
from django.contrib import admin
from django.http import HttpRequest
from emoji_picker.widgets import EmojiPickerTextInputAdmin

from ferry.pub.models import Pub, PubEvent, PubEventRSVP, PubTable


class PubAdminForm(forms.ModelForm):
    class Meta:
        model = Pub
        fields = ("name", "emoji", "map_url", "menu_url")
        widgets = {
            "emoji": EmojiPickerTextInputAdmin(),
        }


class PubAdmin(admin.ModelAdmin):
    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("id", "name", "emoji", "map_url", "menu_url", "created_at", "updated_at")
    list_display = ("name", "emoji")
    form = PubAdminForm


class PubTableAdmin(admin.ModelAdmin):
    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("id", "pub", "number", "created_at", "updated_at")
    list_display = ("__str__", "pub", "number")


class PubEventRSVPAdmin(admin.StackedInline):
    model = PubEventRSVP
    extra = 0

    readonly_fields = ("person", "id", "created_at", "updated_at")
    fields = ("person", "is_attending", "method", "id", "created_at", "updated_at")

    def has_add_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


class PubEventAdmin(admin.ModelAdmin):
    readonly_fields = ("id", "discord_id", "created_at", "updated_at")
    fields = ("id", "timestamp", "discord_id", "pub", "table", "created_by", "created_at", "updated_at")
    list_display = ("timestamp", "pub")
    inlines = (PubEventRSVPAdmin,)


admin.site.register(Pub, PubAdmin)
admin.site.register(PubTable, PubTableAdmin)
admin.site.register(PubEvent, PubEventAdmin)
