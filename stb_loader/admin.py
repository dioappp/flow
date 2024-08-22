from django.contrib import admin
from .models import loaderID


# Register your models here.
class LoaderAdmin(admin.ModelAdmin):
    list_display = ["unit", "ellipse"]
    search_fields = ["unit", "ellipse"]


admin.site.register(loaderID, LoaderAdmin)
