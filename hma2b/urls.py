from django.urls import path

from hma2b import views


app_name = "hma2b"
urlpatterns = [path("", views.index, name="index")]
