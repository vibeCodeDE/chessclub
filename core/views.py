from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render


def health(request):
    return JsonResponse({"status": "ok"})


def home(request):
    return render(request, "core/home.html")


@login_required
def profil(request):
    return render(request, "core/profil.html")
