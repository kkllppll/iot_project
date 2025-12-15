from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_datetime

from .forms import CreateSessionForm
from .models import Microphone, Session, AudioSegment

from .models import AudioSegment  
from django.conf import settings
from pathlib import Path
from .cloud_storage import upload_to_gcs



def home(request):
    return render(request, 'home.html')


def create_session(request):
    if request.method == 'POST':
        form = CreateSessionForm(request.POST)
        if form.is_valid():
            s = Session.objects.create(
                owner_name=form.cleaned_data['owner_name'],
                width=form.cleaned_data['width'],
                height=form.cleaned_data['height'],
            )
            return redirect('session_detail', code=s.code)
    else:
        form = CreateSessionForm()
    return render(request, 'create.html', {'form': form})


def session_detail(request, code):
    session = get_object_or_404(Session, code=code)
    return render(request, 'session_detail.html', {'session': session})


def join_session(request):
    error = None
    if request.method == 'POST':
        code = (request.POST.get('code') or '').strip()
        if code and Session.objects.filter(code=code).exists():
            return redirect('join_session_device', code=code)
        error = 'Session with this code does not exist.'
    return render(request, 'join.html', {'error': error})


def join_session_device(request, code):
    session = get_object_or_404(Session, code=code, is_active=True)

    if request.method == "POST":
        device_name = request.POST.get("device_name")
        x = request.POST.get("x")
        y = request.POST.get("y")

        if device_name and x and y:
            mic = Microphone.objects.create(
                session=session,
                device_name=device_name,
                x_coordinate=float(x),
                y_coordinate=float(y),
            )
            return redirect("mic_detail", pk=mic.id)

    return render(request, "join_device.html", {"code": code})


def join_connected(request, code):
    session = get_object_or_404(Session, code=code)
    return render(request, 'join_connected.html', {'session': session, "code": code})


def mic_detail(request, pk):
    mic = get_object_or_404(Microphone, pk=pk)
 
    last_segment = (
        AudioSegment.objects
        .filter(microphone=mic)
        .order_by("-created_at")
        .first()
    )
    return render(request, "mic_detail.html", {"microphone": mic, "last_segment": last_segment})



def mic_ready(request, pk):
    mic = get_object_or_404(Microphone, pk=pk)
    if request.method == "POST":
        mic.is_ready = True
        mic.save()
    return redirect("mic_detail", pk=pk)


def start_recording(request, code):
    session = get_object_or_404(Session, code=code, is_active=True)

    if request.method == "POST":
        mics_qs = session.microphone_data.all()
        if not mics_qs.exists():
            return redirect("session_detail", code=code)

        if mics_qs.filter(is_ready=False).exists():
            return redirect("session_detail", code=code)

        session.start_time = timezone.now()
        session.end_time = None
        session.save()

    return redirect("session_detail", code=code)


@require_POST
def upload_audio(request, mic_id):
    """
    Приймає ОДИН завершений аудіо-сегмент (наприклад 10 секунд) і зберігає його як AudioSegment.

    Очікує:
      - FILES["audio"]             — blob-файл (webm/ogg)
      - POST["segment_index"]      — (обов'язково) 0,1,2...
      - POST["started_at"]         — ISO-строка старту сегмента (опційно)
      - POST["duration_ms"]        — тривалість сегмента в мс (опційно)
    """
    microphone = get_object_or_404(Microphone, pk=mic_id)

    audio_file = request.FILES.get("audio")
    if not audio_file:
        return JsonResponse(
            {"status": "error", "message": "No audio file provided."},
            status=400
        )

    
    if audio_file.size < 2000:
        return JsonResponse(
            {"status": "skip", "message": "Audio segment too small (likely empty)."},
            status=200
        )


    idx_raw = request.POST.get("segment_index")
    try:
        segment_index = int(idx_raw)
        if segment_index < 0:
            raise ValueError()
    except (TypeError, ValueError):
        return JsonResponse({"status": "error", "message": "Invalid or missing 'segment_index'."}, status=400)

    duration_raw = request.POST.get("duration_ms")
    try:
        duration_ms = int(duration_raw) if duration_raw is not None else 0
        if duration_ms < 0:
            duration_ms = 0
    except (TypeError, ValueError):
        duration_ms = 0

    started_at_str = request.POST.get("started_at")
    if started_at_str:
        dt = parse_datetime(started_at_str)
        if dt is None:
            started_at = timezone.now()
        else:
            if timezone.is_naive(dt):
                dt = timezone.make_aware(dt, timezone.get_current_timezone())
            started_at = dt
    else:
        started_at = timezone.now()

    seg, created = AudioSegment.objects.get_or_create(
        microphone=microphone,
        segment_index=segment_index,
        defaults={
            "audio_file": audio_file,
            "started_at": started_at,
            "duration_ms": duration_ms,
        },
    )

    # MVP: якщо індекс повторився — перезапишемо
    if not created:

        if seg.audio_file:
            seg.audio_file.delete(save=False)

        seg.audio_file = audio_file
        seg.started_at = started_at
        seg.duration_ms = duration_ms
        seg.save()


    ext = Path(seg.audio_file.name).suffix or ".webm"
    object_name = f"audio_sessions/{microphone.session.code}/mic_{microphone.id}/current{ext}"

    cloud_uri = upload_to_gcs(
        local_path=seg.audio_file.path,
        bucket_name=settings.GCS_BUCKET_NAME,
        object_name=object_name,
        content_type=None,
    )

    seg.cloud_url = cloud_uri
    seg.save(update_fields=["cloud_url"])


    return JsonResponse({
        "status": "ok",
        "segment_id": seg.id,
        "segment_index": seg.segment_index,
        "duration_ms": seg.duration_ms,
    })


