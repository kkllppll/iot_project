from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.dateparse import parse_datetime

from .forms import CreateSessionForm
from .models import Microphone, Session, AudioSegment, RecordingRound, AudioSegment, LocalizationResult

from .models import AudioSegment  
from django.conf import settings
from pathlib import Path
from .cloud_storage import make_public_url, upload_to_gcs

import tempfile
from itertools import combinations
from .processing.audio import to_wav, read_wav_mono
from .processing.tdoa import gcc_phat
from .processing.localize import localize_grid, crop_around_peak

from .cloud_storage import make_signed_url


import os

from django.shortcuts import get_object_or_404


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

    active_round = (
        RecordingRound.objects
        .filter(session=session, is_active=True)
        .order_by("-created_at")
        .first()
    )

    last_round = (
        RecordingRound.objects
        .filter(session=session)
        .order_by("-created_at")
        .first()
    )

    last_result = None
    if last_round:
        last_result = getattr(last_round, "result", None)

    mics = session.microphone_data.all().order_by("id")

        # --- SVG adaptive sizes (працює для будь-яких розмірів кімнати) ---
    W = float(session.width)
    H = float(session.height)
    min_dim = max(1.0, min(W, H))  # щоб не ділило на 0

    # Розмір маркерів як % від меншої сторони кімнати
    mic_r = min_dim * 0.03        # 3% від min(W,H)
    sound_r = min_dim * 0.04      # 4%

    # Обмеження, щоб не було ні мікро, ні гігантів
    mic_r = max(0.12, min(mic_r, 2.0))
    sound_r = max(0.16, min(sound_r, 2.5))

    # Текст
    fs = min_dim * 0.06           # 6% від min(W,H)
    fs = max(0.25, min(fs, 2.2))

    dx = mic_r * 0.6
    dy = -mic_r * 0.6

    # Висота SVG в px: залежить від співвідношення сторін
    aspect = W / H if H else 1.0
    svg_height = 520
    if aspect > 3:
        svg_height = 360
    elif aspect < 1:
        svg_height = 600


    return render(request, "session_detail.html", {
        "session": session,
        "mics": mics,

        "active_round": active_round,
        "last_round": last_round,
        "last_result": last_result,

        "mic_r": mic_r,
        "sound_r": sound_r,
        "fs": fs,
        "dx": dx,
        "dy": dy,
        "svg_height": svg_height,
})




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

    active_round = (
        RecordingRound.objects
        .filter(session=mic.session, is_active=True)
        .order_by("-created_at")
        .first()
    )

    last_segment = (
        AudioSegment.objects
        .filter(microphone=mic)
        .order_by("-created_at")
        .first()
    )

    last_segment_url = None
    if last_segment and last_segment.cloud_url:
        last_segment_url = make_public_url(last_segment.cloud_url)


    return render(request, "mic_detail.html", {
        "microphone": mic,
        "last_segment": last_segment,
        "last_segment_url": last_segment_url,
        "active_round": active_round,
    })




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

        #акриваємо попередній активний раунд
        RecordingRound.objects.filter(session=session, is_active=True).update(is_active=False)

        #створюємо новий активний раунд
        RecordingRound.objects.create(session=session, is_active=True)

        session.start_time = timezone.now()
        session.end_time = None
        session.save()

    return redirect("session_detail", code=code)


@require_POST
def upload_audio(request, mic_id):
    microphone = get_object_or_404(Microphone, pk=mic_id)

    active_round = (
        RecordingRound.objects
        .filter(session=microphone.session, is_active=True)
        .order_by("-created_at")
        .first()
    )

    if not active_round:
        return JsonResponse(
            {"status": "error", "message": "No active round. Host must start recording first."},
            status=400
        )

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

    # один запис на мікрофон+round (перезаписуємо)
    seg, created = AudioSegment.objects.get_or_create(
        microphone=microphone,
        round=active_round,
        defaults={
            "audio_file": audio_file,
            "segment_index": segment_index,
            "started_at": started_at,
            "duration_ms": duration_ms,
        },
    )

    if not created:
        # прибираємо попередній файл (щоб не залишати сміття в storage)
        if seg.audio_file:
            seg.audio_file.delete(save=False)

        seg.audio_file = audio_file
        seg.segment_index = segment_index
        seg.started_at = started_at
        seg.duration_ms = duration_ms
        seg.save()

    # розширення
    ext = Path(audio_file.name).suffix or ".webm"
    object_name = f"audio_sessions/{microphone.session.code}/mic_{microphone.id}/current{ext}"

    # IMPORTANT: GoogleCloudStorage не має .path -> пишемо у /tmp і віддаємо шлях
    tmp_path = None
    try:
        seg.audio_file.open("rb")
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir="/tmp") as tmp:
            for chunk in seg.audio_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name
        seg.audio_file.close()

        cloud_uri = upload_to_gcs(
            local_path=tmp_path,
            bucket_name=settings.GCS_BUCKET_NAME,
            object_name=object_name,
            content_type=None,
        )

        seg.cloud_url = cloud_uri
        seg.save(update_fields=["cloud_url"])

    finally:
        # чистимо tmp
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    if seg.audio_file:
        seg.audio_file.delete(save=False)

    return JsonResponse({
        "status": "ok",
        "segment_id": seg.id,
        "segment_index": seg.segment_index,
        "duration_ms": seg.duration_ms,
        "cloud_url": seg.cloud_url,
    })

@require_POST
def process_round(request, round_id):
    rnd = get_object_or_404(RecordingRound, pk=round_id)
    session = rnd.session

    segments = list(
        AudioSegment.objects
        .filter(round=rnd, cloud_url__isnull=False)
        .select_related("microphone")
    )

    if len(segments) < 2:
        return JsonResponse({"status": "error", "message": "Need at least 2 microphones"}, status=400)

 
    mic_pos = {s.microphone_id: (s.microphone.x_coordinate, s.microphone.y_coordinate) for s in segments}

   
    from .cloud_storage import download_from_gcs  

    wav_data = {}
    with tempfile.TemporaryDirectory() as td:
        for s in segments:
            local_src = str(Path(td) / f"seg_{s.id}.webm")
            download_from_gcs(s.cloud_url, local_src)

            wav_path = to_wav(local_src, td)
            x, sr = read_wav_mono(wav_path)
            x = crop_around_peak(x, sr, window_sec=0.5)
            wav_data[s.microphone_id] = (x, sr)



    # TDOA між парами
    mic_ids = list(wav_data.keys())
    tdoa_pairs = []

    for a, b in combinations(mic_ids, 2):
        xa, sra = wav_data[a]
        xb, srb = wav_data[b]
        if sra != srb:
            return JsonResponse({"status": "error", "message": "Sample rates mismatch"}, status=400)

        # max_tau приблизно: діагональ кімнати / 343
        max_dist = (session.width**2 + session.height**2) ** 0.5
        max_tau = max_dist / 343.0

        tau = gcc_phat(xa, xb, fs=sra, max_tau=max_tau)
        tdoa_pairs.append((a, b, tau))

    #  grid все одно дасть “найкращу”
    best_xy, err = localize_grid(session.width, session.height, mic_pos, tdoa_pairs, step=0.1)

    res, _ = LocalizationResult.objects.update_or_create(
        round=rnd,
        defaults={
            "estimated_x": best_xy[0] if best_xy else None,
            "estimated_y": best_xy[1] if best_xy else None,
            "error": err,
            "num_mics": len(mic_ids),
            "method": "grid_tdoa",
        }
    )


    num_mics = len(mic_ids)

    if num_mics == 2:
        note = (
            "Використано 2 мікрофони: положення джерела звуку є неоднозначним "
            "(визначено найкращу наближену точку)."
        )
    else:
        note = (
            "Використано 3 або більше мікрофонів: визначено координати "
            "джерела звуку (x, y)."
    )


    return redirect("session_detail", code=rnd.session.code)