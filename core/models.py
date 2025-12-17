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



class RecordingRound(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name="rounds")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Round {self.id} for session {self.session.code} (active={self.is_active})"


class AudioSegment(models.Model):
    microphone = models.ForeignKey(Microphone, on_delete=models.CASCADE, related_name="audio_segments")

    round = models.ForeignKey(
        RecordingRound,
        on_delete=models.CASCADE,
        related_name="segments",
        null=True,      
        blank=True     
    )

    audio_file = models.FileField(upload_to=audio_segment_upload_to)
    segment_index = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField()
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    cloud_url = models.CharField(max_length=500, blank=True, null=True)




class LocalizationResult(models.Model):
    round = models.OneToOneField("RecordingRound", on_delete=models.CASCADE, related_name="result")
    method = models.CharField(max_length=50, default="grid_tdoa")
    estimated_x = models.FloatField(null=True, blank=True)
    estimated_y = models.FloatField(null=True, blank=True)
    error = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # корисно для дебага
    num_mics = models.PositiveIntegerField(default=0)
