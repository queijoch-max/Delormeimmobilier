from django.contrib import admin

from .models import ChatMessage


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("created_at", "question", "property", "status")
    list_filter = ("status", "created_at")
    search_fields = ("question", "answer")
    readonly_fields = ("session_key", "property", "question", "answer", "status", "created_at")
