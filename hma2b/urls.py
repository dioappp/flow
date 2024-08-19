from django.urls import path

from hma2b import views


app_name = "hma2b"
urlpatterns = [
    path("", views.index, name="index"),
    path("cek_operator/", views.operator, name="cek_operator"),
]
