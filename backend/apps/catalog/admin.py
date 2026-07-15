from django.contrib import admin

from .models import Deck


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ["name", "creator", "is_official", "created_at"]
    list_editable = ["is_official"]
    readonly_fields = ["creator"]
