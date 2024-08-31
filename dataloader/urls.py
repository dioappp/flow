from django.urls import path

from dataloader import views

urlpatterns = [path("/", views.index, name="data_loader")]
