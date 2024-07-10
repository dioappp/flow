from django.urls import path
from report import views

urlpatterns = [
    path('',views.index,name='report.index'),
    path('show',views.showreport,name='report.show'),
]