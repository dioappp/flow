from django.urls import path

from distance import views

app_name = "distance"
urlpatterns = [path("", views.index, name="index")]
