from django.shortcuts import render
from django.http import HttpResponse
from tablib import Dataset
from distance.resources import DistanceResource
from distance.forms import UploadFileForm


# Create your views here.
def index(request):
    form = UploadFileForm()
    return render(request, "distance/index.html", {"form": form})


def import_data(request):
    return
