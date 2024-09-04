from django.urls import path

from hpr import views

app_name = "hpr"
urlpatterns = [path("", views.index, name="index")]
