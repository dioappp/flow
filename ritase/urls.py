from django.urls import path
from ritase import views

app_name = "ritase"
urlpatterns = [
    path("", views.index, name="index"),
    path("loader/", views.index_loader, name="index_loader"),
    path("load_ritase/", views.load_ritase, name="cek_ritase"),
    path("load_ritase_loader/", views.load_ritase_loader, name="cek_ritase_loader"),
    path("update/", views.update, name="update"),
    path("load_operator/", views.operator, name="cek_operator"),
    path("addrow/", views.addrow, name="addrow"),
    path("create_operator/", views.create_operator, name="create_operator"),
    path("update_operator/", views.update_operator, name="update_operator"),
    path("delete_row/", views.delete_row, name="delete_row"),
]
