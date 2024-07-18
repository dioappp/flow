from django.shortcuts import render


# Create your views here.
def index(request):
    return render(request, "exporter/index.html")


def standby(request):
    pass


def production(request):
    pass
