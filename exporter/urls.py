from django.urls import path
from exporter import views

app_name = "exporter"
urlpatterns = [
    path("", views.index, name="index"),
]
