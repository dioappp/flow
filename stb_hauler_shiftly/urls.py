from django.urls import path
from stb_hauler_shiftly import views

app_name = "stb_hauler_shiftly"
urlpatterns = [
    path("", views.index, name="index"),
    path("reportstb", views.reportDataSTB, name="report"),
    path("timeline", views.timeline, name="timeline"),
]
