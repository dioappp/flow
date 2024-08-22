from django.contrib import admin

from .models import truckID, material


# Register your models here.
class TruckAdmin(admin.ModelAdmin):
    list_display = ("jigsaw", "code", "ellipse")
    search_fields = ["jigsaw", "code"]


admin.site.register(truckID, TruckAdmin)


class MaterialAdmin(admin.ModelAdmin):
    list_display = ("code", "material", "remark")


admin.site.register(material, MaterialAdmin)
