from django.contrib import admin
from .models import loaderID, Standby, Reason


# Register your models here.
class LoaderAdmin(admin.ModelAdmin):
    list_display = ["unit", "ellipse"]
    search_fields = ["unit", "ellipse"]


class ReasonInline(admin.StackedInline):
    model = Reason


class StandbyAdmin(admin.ModelAdmin):
    inlines = [
        ReasonInline,
    ]
    list_display = ["code", "rank"]


admin.site.register(loaderID, LoaderAdmin)

admin.site.register(Standby, StandbyAdmin)
