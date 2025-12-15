from django.db import migrations, models
import django.db.models.deletion
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AudioSegment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("audio_file", models.FileField(upload_to=core.models.audio_segment_upload_to)),
                ("segment_index", models.PositiveIntegerField(default=0)),
                ("started_at", models.DateTimeField()),
                ("duration_ms", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("microphone", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audio_segments", to="core.microphone")),
            ],
            options={
                "ordering": ["microphone", "segment_index"],
                "unique_together": {("microphone", "segment_index")},
            },
        ),
    ]
