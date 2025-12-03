from django.contrib import admin
from .models import Session, Microphone


class MicrophoneInline(admin.TabularInline):
    model = Microphone
    extra = 0  # не показувати порожні рядки


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('code', 'owner_name', 'start_time', 'end_time', 'is_active')
    search_fields = ('code', 'owner_name')
    list_filter = ('is_active',)
    inlines = [MicrophoneInline]

@admin.register(Microphone)
class MicrophoneAdmin(admin.ModelAdmin):
    list_display = ('device_name', 'session', 'x_coordinate', 'y_coordinate', 'is_ready')
    list_filter = ('is_ready', 'session')
