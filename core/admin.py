from django.contrib import admin
from .models import Session, Microphone, AudioSegment


class MicrophoneInline(admin.TabularInline):
    model = Microphone
    extra = 0


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


@admin.register(AudioSegment)
class AudioSegmentAdmin(admin.ModelAdmin):
    list_display = ("id", "microphone", "segment_index", "duration_ms", "created_at")
    list_filter = ("microphone",)
    search_fields = ("microphone__device_name", "segment_index")
