from django.db import models
import random, string


def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))


class Session(models.Model):
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    code = models.CharField(default=generate_code, max_length=10, unique=True)
    owner_name = models.CharField(max_length=100)
    width = models.FloatField()
    height = models.FloatField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Session {self.id} from {self.start_time} to {self.end_time or 'ongoing'}"


class Microphone(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='microphone_data')
    device_name = models.CharField(max_length=100)
    x_coordinate = models.FloatField()
    y_coordinate = models.FloatField()
    is_ready = models.BooleanField(default=False)
    connected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Microphone for Session {self.session.id} at ({self.x_coordinate}, {self.y_coordinate})"


def audio_segment_upload_to(instance, filename):
    session_code = instance.microphone.session.code
    mic_id = instance.microphone.id
    idx = instance.segment_index if instance.segment_index is not None else 0
    ext = filename.split(".")[-1] if "." in filename else "webm"
    return f"audio_sessions/{session_code}/mic_{mic_id}/segment_{idx:06d}.{ext}"


class AudioSegment(models.Model):
    """
    Один завершений файл запису (наприклад 10 секунд).
    Це НЕ чанки кожну секунду — кожен segment є валідним контейнером (webm/ogg).
    """
    microphone = models.ForeignKey(Microphone, on_delete=models.CASCADE, related_name="audio_segments")
    audio_file = models.FileField(upload_to=audio_segment_upload_to)

    segment_index = models.PositiveIntegerField(default=0)  # 0,1,2...
    started_at = models.DateTimeField()                     # час старту цього сегмента на клієнті
    duration_ms = models.PositiveIntegerField(default=0)    # тривалість сегмента

    created_at = models.DateTimeField(auto_now_add=True)


    cloud_url = models.CharField(max_length=500, blank=True, null=True)


    class Meta:
        unique_together = ("microphone", "segment_index")
        ordering = ["microphone", "segment_index"]

    def __str__(self):
        return f"Mic {self.microphone_id} segment {self.segment_index}"
