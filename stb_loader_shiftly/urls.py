from django.urls import path
from stb_loader_shiftly import views

app_name = 'stb_loader_shiftly'
urlpatterns = [
    path('', views.index, name='index'),
    path('reportstb', views.reportDataSTB, name='report'),
    path('timeline', views.timeline, name='timeline'),
    path('update', views.update, name='update'),
    path('delete', views.delete, name='delete'),
    path('split', views.split, name='split'),
    path('add', views.add, name='add'),
    path('export_excel', views.export_excel, name='export_excel'),
]
