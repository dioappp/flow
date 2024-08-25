from django.contrib import admin
from django.urls import path, include
from debug_toolbar.toolbar import debug_toolbar_urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("stb/loader/hourly/", include("stb_loader.urls")),
    path("stb/loader/shiftly/", include("stb_loader_shiftly.urls")),
    path("stb/hauler/hourly/", include("stb_hauler.urls")),
    path("stb/hauler/shiftly/", include("stb_hauler_shiftly.urls")),
    path("", include("ritase.urls")),
    path("distance/", include("distance.urls")),
    path("exporter/", include("exporter.urls")),
    path("hm/", include("hma2b.urls")),
] + debug_toolbar_urls()
