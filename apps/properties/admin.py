from django.contrib import admin

from .models import Photo, Property


class PhotoInline(admin.TabularInline):
    model = Photo
    extra = 1


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("title", "kind", "transaction", "neighborhood", "price", "agent", "is_published", "updated_at")
    list_filter = ("is_published", "kind", "transaction", "agent")
    search_fields = ("title", "neighborhood", "highlights")
    inlines = [PhotoInline]
