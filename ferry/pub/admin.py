from django import forms
from django.contrib import admin
from emoji_picker.widgets import EmojiPickerTextInputAdmin

from ferry.pub.models import Pub, PubEvent, PubTable


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


class PubEventAdmin(admin.ModelAdmin):
    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("id", "timestamp", "pub", "table", "attendees", "created_by", "created_at", "updated_at")
    list_display = ("timestamp", "pub")
    filter_horizontal = ("attendees",)


admin.site.register(Pub, PubAdmin)
admin.site.register(PubTable, PubTableAdmin)
admin.site.register(PubEvent, PubEventAdmin)
