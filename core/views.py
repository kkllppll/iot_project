from django.utils import timezone
from webbrowser import get
from django.shortcuts import render, redirect, get_object_or_404
from .forms import CreateSessionForm
from .models import Microphone, Session

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
                # code згенерується автоматично через default=generate_code
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
    return render(request, 'join_connected.html', {'session': session})


def mic_detail(request, pk):
    mic = get_object_or_404(Microphone, pk=pk)
    return render(request, "mic_detail.html", {"mic": mic})


def mic_ready(request, pk):
    mic = get_object_or_404(Microphone, pk=pk)

    if request.method == "POST":
        mic.is_ready = True
        mic.save()
        return redirect("mic_detail", pk=pk)
    
    return redirect("mic_detail", pk=pk)


def start_recording(request, code):
    session = get_object_or_404(Session, code=code, is_active=True)

    if request.method == "POST":
        mics_qs = session.microphone_data.all()

        if not mics_qs.exists():
            return redirect("session_detail", code=code)

        not_ready_exists = mics_qs.filter(is_ready=False).exists()
        if not_ready_exists:
           
            return redirect("session_detail", code=code)

        session.start_time = timezone.now()
        session.end_time = None
        session.save()

        return redirect("session_detail", code=code)

 
    return redirect("session_detail", code=code)