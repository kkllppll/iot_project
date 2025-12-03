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
    

