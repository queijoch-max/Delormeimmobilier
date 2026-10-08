from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class AgentAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "email", "phone", "is_active", "is_superuser")
    fieldsets = UserAdmin.fieldsets + (("Coordonnées", {"fields": ("phone",)}),)
