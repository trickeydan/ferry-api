from typing import Any

from django import forms
from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from emoji_picker.widgets import EmojiPickerTextInputAdmin

from ferry.pub.models import (
    Pub,
    PubEvent,
    PubEventAttendanceTombstone,
    PubEventBooking,
    PubEventExtraInfo,
    PubEventRSVP,
    PubTable,
)


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


class PubEventBookingAdmin(admin.StackedInline):
    model = PubEventBooking

    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("table_size", "id", "created_by", "created_at", "updated_at")


class PubEventExtraInfoAdmin(admin.StackedInline):
    model = PubEventExtraInfo
    extra = 1

    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("info", "id", "created_by", "created_at", "updated_at")


class PubEventAttendanceTombstoneInlineAdmin(admin.StackedInline):
    model = PubEventAttendanceTombstone
    extra = 0

    # The inline is read-only because it is linked to the pub event when it is created.
    readonly_fields = ("person", "id", "created_at", "updated_at")
    fields = ("person", "id", "created_at", "updated_at")

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


class PubEventAdmin(admin.ModelAdmin):
    readonly_fields = ("id", "discord_id", "created_at", "updated_at")
    fields = ("id", "timestamp", "discord_id", "pub", "table", "created_by", "created_at", "updated_at")
    list_display = ("timestamp", "pub")
    inlines = (
        PubEventBookingAdmin,
        PubEventRSVPAdmin,
        PubEventExtraInfoAdmin,
        PubEventAttendanceTombstoneInlineAdmin,
    )


class PubEventAttendanceTombstoneAdmin(admin.ModelAdmin):
    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("id", "person", "pub_event", "created_at", "updated_at")
    list_display = ("person", "pub_event")

    def get_queryset(self, request: HttpRequest) -> QuerySet[PubEventAttendanceTombstone]:
        return PubEventAttendanceTombstone.objects.select_related("person", "pub_event").filter(pub_event__isnull=True)


admin.site.register(Pub, PubAdmin)
admin.site.register(PubTable, PubTableAdmin)
admin.site.register(PubEvent, PubEventAdmin)
admin.site.register(PubEventAttendanceTombstone, PubEventAttendanceTombstoneAdmin)
