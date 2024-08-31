from django.urls import path

from dataloader import views

app_name = "dataloader"
urlpatterns = [
    path("", views.index, name="data_loader"),
    path("ritase/", views.ritase, name="ritase"),
    path("hm/", views.hm, name="hm"),
]
