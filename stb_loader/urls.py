from django.urls import path
from stb_loader import views

app_name = "stb_loader"
urlpatterns = [
    path("", views.index, name="index"),
    path("reportstb", views.reportDataSTB, name="report"),
    path("timeline", views.timeline, name="timeline"),
    path("update", views.update, name="update"),
    path("delete", views.delete, name="delete"),
    path("split", views.split, name="split"),
    path("add", views.add, name="add"),
    path("load_data", views.load_data, name="load_data"),
    path("undo/", views.undo, name="undo"),
    # path("redo/", views.redo, name="your_redo_view"),
    path("addbatch/", views.addBatch, name="addbatch"),
    path("load_child/", views.data_child, name="load_child"),
    path("timeline_batch/", views.timeline_batch, name="timeline_batch"),
]
