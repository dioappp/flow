from django.urls import path

from distance import views

app_name = "distance"
urlpatterns = [
    path("", views.index, name="index"),
    path("import/", views.import_data, name="import"),
    path("to_db/", views.to_db, name="to_db"),
]
