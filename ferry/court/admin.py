from django.contrib import admin

from .models import Accusation, Consequence, Person, Ratification


class PersonAdmin(admin.ModelAdmin):
    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("id", "display_name", "discord_id", "created_at", "updated_at")
    list_display = ("display_name", "discord_id")


class ConsequenceAdmin(admin.ModelAdmin):
    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("id", "content", "is_enabled", "created_by", "created_at", "updated_at")

    list_filter = ("is_enabled",)
    list_display = ("content", "is_enabled", "created_by")


class RatificationInline(admin.StackedInline):
    model = Ratification
    extra = 0

    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("id", "consequence", "created_by", "created_at", "updated_at")


class AccusationAdmin(admin.ModelAdmin):
    readonly_fields = ("id", "created_at", "updated_at")
    fields = ("id", "quote", "suspect", "created_by", "created_at", "updated_at")
    inlines = (RatificationInline,)

    list_filter = ("suspect", "created_by")
    list_display = ("created_at", "suspect", "created_by")


admin.site.register(Person, PersonAdmin)
admin.site.register(Consequence, ConsequenceAdmin)
admin.site.register(Accusation, AccusationAdmin)
