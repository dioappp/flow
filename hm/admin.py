from django.contrib import admin
from hm.models import Operator


# Register your models here.
class OperatorAdmin(admin.ModelAdmin):
    list_display = ["NRP", "operator"]
    search_fields = ["NRP", "operator"]


admin.site.register(Operator, OperatorAdmin)
