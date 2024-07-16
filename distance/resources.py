from import_export import resources
from distance.models import distance


class DistanceResource(resources.ModelResource):
    class Meta:
        model = distance
