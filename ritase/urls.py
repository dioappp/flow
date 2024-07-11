from django.urls import path
from ritase import views

app_name = "ritase"
urlpatterns = [
    path("", views.index, name="home"),
    path("load_ritase", views.load_ritase, name="cek_ritase"),
    path("update", views.update, name="update"),
    path("load_operator", views.operator, name="cek_operator"),
    path("ritase_db", views.load_ritase_to_db, name="to_db"),
    path("addrow", views.addrow, name="addrow"),
    path("update_operator", views.update_operator, name="update_operator"),
    path("delete_row", views.delete_row, name="delete_row"),
]
