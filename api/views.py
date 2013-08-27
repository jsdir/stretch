from rest_framework import viewsets


from api import models
from api import serializers


class EnvironmentViewSet(viewsets.ModelViewSet):
    queryset = models.Environment.objects.all()
    serializer_class = serializers.EnvironmentSerializer
