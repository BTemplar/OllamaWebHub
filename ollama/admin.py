from django.contrib import admin

from .models import ChatBranch, ChatMessage


class ChatMessageInline(admin.TabularInline):
    model = ChatMessage
    extra = 0
    readonly_fields = ("timestamp",)
    fields = ("sender", "message", "think", "image", "timestamp")


@admin.register(ChatBranch)
class ChatBranchAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "user",
        "selected_model",
        "request_type",
        "response_type",
        "multimodal",
        "temperature",
    )
    list_filter = ("request_type", "response_type", "multimodal", "think")
    search_fields = ("name", "user__username", "selected_model")
    inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("chat_branch", "sender", "short_message", "timestamp")
    list_filter = ("sender",)
    search_fields = ("message", "chat_branch__name")
    readonly_fields = ("timestamp",)

    @admin.display(description="Message")
    def short_message(self, obj):
        return obj.message[:80]
